# file: screening/engine.py
"""Orchestrates live stock screening: universe resolution -> data fetch ->
metric computation -> filtering -> percentile ranking -> weighting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from screening import data_fetch, universe_data
from screening.metric_registry import METRIC_REGISTRY, MetricSpec
from screening.schemas import ScreenResult, ScreenedStock, SkippedMetric, FailedTicker

MAX_SCREEN_TICKERS = 200
NEAR_UNSUPPORTED_MISSING_RATIO = 0.8
FLOAT_TOLERANCE = 1e-6
DEFAULT_TOP_N = 20

_TECH_CATEGORIES = {"price_volume", "technical", "momentum_volatility"}


def _get_metric_value(bundle, metric_name: str, spec: MetricSpec) -> Optional[float]:
    cache = bundle._cache
    if metric_name in cache:
        return cache[metric_name]
    try:
        value = spec.compute_fn(bundle)
    except Exception:
        value = None
    cache[metric_name] = value
    return value


def _required_metric_names(filters: list[dict], ranking_metrics: list[str],
                            weight_metric: Optional[str]) -> list[str]:
    names: set[str] = set()
    for f in filters:
        if f.get("metric"):
            names.add(f["metric"])
        if f.get("compare_type") == "metric" and f.get("compare_metric"):
            names.add(f["compare_metric"])
    names.update(ranking_metrics or [])
    if weight_metric:
        names.add(weight_metric)
    return sorted(names)


def _classify_metrics(names: list[str]) -> tuple[dict[str, MetricSpec], list[SkippedMetric]]:
    supported: dict[str, MetricSpec] = {}
    skipped: list[SkippedMetric] = []
    for name in names:
        spec = METRIC_REGISTRY.get(name)
        if spec is None or not spec.supported:
            reason = spec.unsupported_reason if spec else "unknown metric"
            skipped.append(SkippedMetric(metric=name, reason=reason, scope="global"))
            continue
        supported[name] = spec
    return supported, skipped


def _compare(value: float, operator: str, target: float) -> bool:
    if operator == "<":
        return value < target
    if operator == ">":
        return value > target
    if operator == "<=":
        return value <= target
    if operator == ">=":
        return value >= target
    if operator == "==":
        return abs(value - target) < FLOAT_TOLERANCE
    return False


def _percentile_series(values: dict[str, Optional[float]]) -> dict[str, Optional[float]]:
    s = pd.Series(values, dtype="float64")
    pct = s.rank(pct=True, na_option="keep")
    return {k: (float(v) if pd.notna(v) else None) for k, v in pct.items()}


def run_screening(
    universe: str,
    filters: list[dict],
    ranking_metrics: list[str],
    weight_type: str,
    weight_metric: Optional[str],
    weight_metric_inverse: bool,
    top_n: int,
) -> ScreenResult:
    fetched_at = datetime.now(timezone.utc).isoformat()
    top_n = top_n or DEFAULT_TOP_N

    universe_entries = universe_data.resolve_universe(universe)
    universe_total = len(universe_entries)
    truncated = universe_total > MAX_SCREEN_TICKERS
    screened_entries = universe_entries[:MAX_SCREEN_TICKERS]

    if not screened_entries:
        return ScreenResult(
            success=False,
            message=f"No constituent data available for universe '{universe}'.",
            universe=universe, universe_total_tickers=universe_total,
            universe_screened_tickers=0, universe_truncated=truncated,
            eligible_count=0, selected_count=0, requested_top_n=top_n,
            weight_type=weight_type, weight_metric=weight_metric,
            fetched_at=fetched_at,
        )

    required_names = _required_metric_names(filters, ranking_metrics, weight_metric)
    supported_specs, skipped_metrics = _classify_metrics(required_names)

    need_fundamentals = any(spec.category not in _TECH_CATEGORIES for spec in supported_specs.values())

    bundles, failed_ticker_info = data_fetch.build_bundles(screened_entries, need_fundamentals)
    failed_tickers = [FailedTicker(**f) for f in failed_ticker_info]

    if not bundles:
        return ScreenResult(
            success=False,
            message="Live data fetch failed for every ticker in this universe (Yahoo Finance may be "
                    "rate-limiting this server). Try again shortly.",
            universe=universe, universe_total_tickers=universe_total,
            universe_screened_tickers=len(screened_entries), universe_truncated=truncated,
            eligible_count=0, selected_count=0, requested_top_n=top_n,
            weight_type=weight_type, weight_metric=weight_metric,
            skipped_metrics=skipped_metrics, failed_tickers=failed_tickers,
            fetched_at=fetched_at,
        )

    # Compute every required supported metric once per ticker.
    computed: dict[str, dict[str, Optional[float]]] = {}  # ticker -> metric -> value
    missing_counts: dict[str, int] = {name: 0 for name in supported_specs}
    for ticker, bundle in bundles.items():
        row = {}
        for name, spec in supported_specs.items():
            val = _get_metric_value(bundle, name, spec)
            row[name] = val
            if val is None:
                missing_counts[name] += 1
        computed[ticker] = row

    n_tickers = len(bundles)
    for name, missing in missing_counts.items():
        if n_tickers > 0 and missing / n_tickers >= NEAR_UNSUPPORTED_MISSING_RATIO:
            skipped_metrics.append(SkippedMetric(
                metric=name, scope="near_unsupported",
                reason=f"Data missing for {missing}/{n_tickers} tickers in this universe "
                       f"(common for small/microcap coverage gaps on Yahoo Finance)",
            ))

    # Apply filters.
    eligible: list[str] = []
    for ticker in bundles:
        row = computed[ticker]
        passes = True
        for f in filters:
            metric = f.get("metric")
            if metric not in supported_specs:
                continue  # globally-unsupported filter: skip (not enforced), already reported
            value = row.get(metric)
            if value is None:
                passes = False
                break
            operator = f["operator"]
            if f.get("compare_type") == "metric":
                compare_metric = f.get("compare_metric")
                if compare_metric not in supported_specs:
                    continue
                target = row.get(compare_metric)
                if target is None:
                    passes = False
                    break
            else:
                target = f.get("value")
                if target is None:
                    continue
            if not _compare(value, operator, float(target)):
                passes = False
                break
        if passes:
            eligible.append(ticker)

    eligible_count = len(eligible)

    # Rank eligible tickers by percentile across ranking metrics.
    composite_scores: dict[str, float] = {}
    per_metric_percentiles: dict[str, dict[str, Optional[float]]] = {}
    valid_ranking_metrics = [m for m in ranking_metrics if m in supported_specs]

    for metric in valid_ranking_metrics:
        values = {t: computed[t].get(metric) for t in eligible}
        pct = _percentile_series(values)
        if supported_specs[metric].lower_is_better:
            pct = {t: (1 - p if p is not None else None) for t, p in pct.items()}
        per_metric_percentiles[metric] = pct

    ranked_tickers: list[str] = []
    for t in eligible:
        scores = [per_metric_percentiles[m][t] for m in valid_ranking_metrics if per_metric_percentiles[m].get(t) is not None]
        if not scores:
            continue
        composite_scores[t] = sum(scores) / len(scores)
        ranked_tickers.append(t)

    ranked_tickers.sort(key=lambda t: composite_scores[t], reverse=True)
    selected = ranked_tickers[:top_n]
    selected_count = len(selected)

    # Weighting -- computed among the *selected* subset so weights sum to 100%.
    weight_fallback_reason = None
    effective_weight_type = weight_type
    weight_values: dict[str, Optional[float]] = {}
    if weight_type == "metric" and weight_metric and weight_metric in supported_specs:
        raw_values = {t: computed[t].get(weight_metric) for t in selected}
        pct = _percentile_series(raw_values)
        if weight_metric_inverse:
            pct = {t: (1 - p if p is not None else None) for t, p in pct.items()}
        available = {t: p for t, p in pct.items() if p is not None}
        if available:
            # Tickers missing the weight metric get the average of the available
            # percentiles (a neutral fallback) rather than being zeroed out or
            # dropped, so every selected stock still receives a nonzero weight.
            fallback_pct = sum(available.values()) / len(available)
            filled = {t: pct.get(t) if pct.get(t) is not None else fallback_pct for t in selected}
            total = sum(filled.values())
            weight_values = {t: (v / total * 100 if total > 0 else 100 / len(filled)) for t, v in filled.items()}
        else:
            effective_weight_type = "equal"
            weight_fallback_reason = f"'{weight_metric}' had no data for any selected stock; fell back to equal weighting"
    elif weight_type == "metric":
        effective_weight_type = "equal"
        weight_fallback_reason = f"Weight metric '{weight_metric}' is not computable from live data; fell back to equal weighting"

    if effective_weight_type == "equal":
        weight_values = {t: (100 / selected_count if selected_count else 0) for t in selected}

    results: list[ScreenedStock] = []
    for rank, t in enumerate(selected, start=1):
        entry = bundles[t]
        row = computed[t]
        filter_metric_names = {f["metric"] for f in filters if f.get("metric") in supported_specs}
        filter_metric_names.update(
            f["compare_metric"] for f in filters
            if f.get("compare_type") == "metric" and f.get("compare_metric") in supported_specs
        )
        filter_values = {m: row.get(m) for m in filter_metric_names}
        ranking_values = {m: row.get(m) for m in valid_ranking_metrics}
        missing = [m for m, v in row.items() if v is None]
        results.append(ScreenedStock(
            ticker=t, symbol=entry.symbol, company_name=entry.company_name,
            rank=rank, composite_score=round(composite_scores.get(t, 0.0), 4),
            weight_pct=round(weight_values.get(t, 0.0), 2),
            filter_values=filter_values, ranking_values=ranking_values,
            weight_metric_value=row.get(weight_metric) if weight_metric else None,
            missing_metrics=missing,
        ))

    data_quality_warning = None
    warnings = []
    if truncated:
        warnings.append(f"Universe '{universe}' has {universe_total} constituents; only the first "
                         f"{MAX_SCREEN_TICKERS} were screened for response-time reasons.")
    if failed_tickers:
        warnings.append(f"{len(failed_tickers)} of {len(screened_entries)} tickers could not be fetched.")
    if weight_fallback_reason:
        warnings.append(weight_fallback_reason)
    if warnings:
        data_quality_warning = " ".join(warnings)

    return ScreenResult(
        success=True,
        universe=universe,
        universe_total_tickers=universe_total,
        universe_screened_tickers=len(screened_entries),
        universe_truncated=truncated,
        eligible_count=eligible_count,
        selected_count=selected_count,
        requested_top_n=top_n,
        weight_type=effective_weight_type,
        weight_metric=weight_metric,
        results=results,
        skipped_metrics=skipped_metrics,
        failed_tickers=failed_tickers,
        data_quality_warning=data_quality_warning,
        fetched_at=fetched_at,
    )
