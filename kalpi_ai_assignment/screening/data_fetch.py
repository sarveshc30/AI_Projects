# file: screening/data_fetch.py
"""Threaded, best-effort live data fetching from yfinance.

Yahoo rate-limits/soft-blocks datacenter IPs and individual tickers routinely
fail (delisted symbols, missing statements, transient errors). Every fetch
here is isolated per-ticker so one failure never aborts the batch; failures
are collected and reported to the caller instead of raised.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import yfinance as yf

OHLCV_BATCH_SIZE = 50
OHLCV_PERIOD = "2y"
FUNDAMENTALS_MAX_WORKERS = 16
OHLCV_MAX_WORKERS = 4
CACHE_TTL_SECONDS = 15 * 60

BENCHMARK_TICKER = "^NSEI"  # Nifty 50 index, used for Beta / idiosyncratic return


@dataclass
class TickerBundle:
    ticker: str
    symbol: str
    company_name: str
    ohlcv: Optional[pd.DataFrame] = None          # columns: Open, High, Low, Close, Volume
    info: Optional[dict] = None
    financials: Optional[pd.DataFrame] = None            # annual income statement
    quarterly_financials: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None          # annual
    quarterly_balance_sheet: Optional[pd.DataFrame] = None
    cashflow: Optional[pd.DataFrame] = None               # annual
    quarterly_cashflow: Optional[pd.DataFrame] = None
    index_ohlcv: Optional[pd.DataFrame] = None            # shared benchmark series
    _cache: dict = field(default_factory=dict)  # per-bundle memoization for compute_fn results


class _TTLCache:
    """Best-effort in-process cache. Not durable across cold serverless starts."""

    def __init__(self):
        self._store: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value):
        with self._lock:
            self._store[key] = (time.time() + CACHE_TTL_SECONDS, value)


_ohlcv_cache = _TTLCache()
_fundamentals_cache = _TTLCache()


def _chunk(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _fetch_ohlcv_batch(tickers: list[str]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    try:
        raw = yf.download(
            tickers=tickers,
            period=OHLCV_PERIOD,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception:
        return out

    if raw is None or raw.empty:
        return out

    if len(tickers) == 1:
        # yfinance sometimes returns a flat (non-multiindex) frame for a single ticker.
        t = tickers[0]
        df = raw if not isinstance(raw.columns, pd.MultiIndex) else raw.get(t)
        if df is not None and not df.empty:
            out[t] = df.dropna(how="all")
        return out

    for t in tickers:
        try:
            df = raw[t]
        except Exception:
            continue
        if df is not None and not df.empty:
            df = df.dropna(how="all")
            if len(df) > 0:
                out[t] = df
    return out


def fetch_ohlcv(tickers: list[str]) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Batch + threaded OHLCV fetch. Returns (ticker -> df, list of tickers with no usable data)."""
    results: dict[str, pd.DataFrame] = {}
    to_fetch = []
    for t in tickers:
        cached = _ohlcv_cache.get(t)
        if cached is not None:
            results[t] = cached
        else:
            to_fetch.append(t)

    batches = _chunk(to_fetch, OHLCV_BATCH_SIZE)
    if batches:
        with ThreadPoolExecutor(max_workers=OHLCV_MAX_WORKERS) as pool:
            futures = [pool.submit(_fetch_ohlcv_batch, batch) for batch in batches]
            for fut in as_completed(futures):
                batch_result = fut.result()
                for t, df in batch_result.items():
                    _ohlcv_cache.set(t, df)
                    results[t] = df

    failed = [t for t in tickers if t not in results or len(results[t]) < 30]
    return results, failed


def fetch_benchmark_ohlcv() -> Optional[pd.DataFrame]:
    cached = _ohlcv_cache.get(BENCHMARK_TICKER)
    if cached is not None:
        return cached
    data, _ = fetch_ohlcv([BENCHMARK_TICKER])
    return data.get(BENCHMARK_TICKER)


def _fetch_one_fundamentals(ticker: str) -> Optional[dict]:
    cached = _fundamentals_cache.get(ticker)
    if cached is not None:
        return cached
    try:
        tk = yf.Ticker(ticker)
        bundle = {
            "info": _safe(lambda: tk.info) or {},
            "financials": _safe(lambda: tk.financials),
            "quarterly_financials": _safe(lambda: tk.quarterly_financials),
            "balance_sheet": _safe(lambda: tk.balance_sheet),
            "quarterly_balance_sheet": _safe(lambda: tk.quarterly_balance_sheet),
            "cashflow": _safe(lambda: tk.cashflow),
            "quarterly_cashflow": _safe(lambda: tk.quarterly_cashflow),
        }
        _fundamentals_cache.set(ticker, bundle)
        return bundle
    except Exception:
        return None


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


def fetch_fundamentals(tickers: list[str]) -> tuple[dict[str, dict], list[str]]:
    """Threaded per-ticker fundamentals fetch. Returns (ticker -> data dict, failed tickers)."""
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=FUNDAMENTALS_MAX_WORKERS) as pool:
        future_to_ticker = {pool.submit(_fetch_one_fundamentals, t): t for t in tickers}
        for fut in as_completed(future_to_ticker):
            t = future_to_ticker[fut]
            try:
                data = fut.result(timeout=30)
            except Exception:
                data = None
            if data is not None:
                results[t] = data

    failed = [t for t in tickers if t not in results]
    return results, failed


def build_bundles(
    tickers: list[dict],
    need_fundamentals: bool,
) -> tuple[dict[str, TickerBundle], list[dict]]:
    """tickers: list of {symbol, yf_ticker, company_name}. Returns (yf_ticker -> TickerBundle, failed_ticker_info)."""
    yf_tickers = [t["yf_ticker"] for t in tickers]
    ohlcv_data, ohlcv_failed = fetch_ohlcv(yf_tickers)

    fundamentals_data: dict[str, dict] = {}
    fundamentals_failed: set[str] = set()
    if need_fundamentals:
        fund_targets = [t for t in yf_tickers if t not in ohlcv_failed]
        fundamentals_data, ff = fetch_fundamentals(fund_targets)
        fundamentals_failed = set(ff)

    index_ohlcv = fetch_benchmark_ohlcv()

    bundles: dict[str, TickerBundle] = {}
    failed_info: list[dict] = []
    ohlcv_failed_set = set(ohlcv_failed)

    for t in tickers:
        yft = t["yf_ticker"]
        if yft in ohlcv_failed_set:
            failed_info.append({"ticker": yft, "reason": "No usable price history returned by Yahoo Finance"})
            continue
        if need_fundamentals and yft in fundamentals_failed:
            failed_info.append({"ticker": yft, "reason": "Price data available but fundamentals fetch failed"})
            continue

        fdata = fundamentals_data.get(yft, {}) if need_fundamentals else {}
        bundles[yft] = TickerBundle(
            ticker=yft,
            symbol=t["symbol"],
            company_name=t.get("company_name", t["symbol"]),
            ohlcv=ohlcv_data.get(yft),
            info=fdata.get("info"),
            financials=fdata.get("financials"),
            quarterly_financials=fdata.get("quarterly_financials"),
            balance_sheet=fdata.get("balance_sheet"),
            quarterly_balance_sheet=fdata.get("quarterly_balance_sheet"),
            cashflow=fdata.get("cashflow"),
            quarterly_cashflow=fdata.get("quarterly_cashflow"),
            index_ohlcv=index_ohlcv,
        )

    return bundles, failed_info
