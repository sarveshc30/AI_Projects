#!/usr/bin/env python3
"""
reports.py — turn a list of benchmark run dicts into reports.

Outputs:
  - CSV        : one flat row per variant (load time + speed + memory + quality
                 + efficiency score)
  - Markdown   : comparison tables + chart links
  - HTML       : self-contained page (best-variant callout, tables, and
                 base64-embedded bar / radar / efficiency charts) — this is what
                 the Gradio frontend renders inline.

Reuses the dataframe builders and bar-plot functions from
visualize_benchmarks.py, and adds:
  - efficiency_score(run) = (Quality x Speed) / Memory
  - plot_radar(...)       : Quality / Speed / Memory / Model Size spider chart
  - plot_efficiency(...)  : variants ranked by efficiency score

A "run" is a dict as produced by pipeline.run_variant (superset of the
benchmark_llm JSON schema, with an extra "quantization" section).
"""

from __future__ import annotations

import base64
import io
import math
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # headless: render to buffers, never open a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import visualize_benchmarks as viz


# --------------------------------------------------------------------------- #
# Metric extraction
# --------------------------------------------------------------------------- #

def _quality(run: dict) -> Optional[float]:
    """Mean of the variant's primary benchmark scores (0-1). None if no
    quality data. Uses acc_norm / acc-style metrics, skips sample_len."""
    sm = run.get("smartness") or {}
    scores = []
    for _task, metrics in sm.items():
        if not isinstance(metrics, dict):
            continue
        for name, value in metrics.items():
            if name == "sample_len" or not isinstance(value, (int, float)):
                continue
            scores.append(float(value))
    return float(np.mean(scores)) if scores else None


def _speed(run: dict) -> Optional[float]:
    s = run.get("speed") or {}
    v = s.get("avg_tokens_per_sec")
    return float(v) if isinstance(v, (int, float)) else None


def _memory_gb(run: dict) -> Optional[float]:
    m = run.get("memory") or {}
    for key in ("gpu_peak_allocated_gb", "gpu_allocated_gb", "in_memory_param_size_gb"):
        v = m.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _model_size_gb(run: dict) -> Optional[float]:
    m = run.get("memory") or {}
    for key in ("on_disk_size_gb", "in_memory_param_size_gb"):
        v = m.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _load_time(run: dict) -> Optional[float]:
    q = run.get("quantization") or {}
    v = q.get("load_time_sec")
    return float(v) if isinstance(v, (int, float)) else None


def efficiency_score(run: dict) -> Optional[float]:
    """
    Composite efficiency = (Quality x Speed) / Memory.

    Quality = mean benchmark score, Speed = avg tokens/sec, Memory = peak VRAM
    in GB (falls back to in-memory param size). Higher is better. Returns None
    if any component is missing so it can be shown as "n/a".
    """
    q = _quality(run)
    s = _speed(run)
    mem = _memory_gb(run)
    if q is None or s is None or not mem:
        return None
    return round((q * s) / mem, 3)


# --------------------------------------------------------------------------- #
# Tabular data
# --------------------------------------------------------------------------- #

def summary_dataframe(runs: List[dict]) -> pd.DataFrame:
    """One flat row per variant with the headline metrics + efficiency."""
    rows = []
    for r in runs:
        rows.append({
            "model": r.get("tag", r.get("model", "?")),
            "method": (r.get("quantization") or {}).get("method", r.get("method", "")),
            "Load time (s)": _load_time(r),
            "Tokens/sec": _speed(r),
            "Avg latency (s)": (r.get("speed") or {}).get("avg_latency_sec"),
            "Avg TTFT (s)": (r.get("speed") or {}).get("avg_ttft_sec"),
            "Peak VRAM (GB)": (r.get("memory") or {}).get("gpu_peak_allocated_gb"),
            "Param size (GB)": (r.get("memory") or {}).get("in_memory_param_size_gb"),
            "Model size (GB)": _model_size_gb(r),
            "Quality (avg)": (round(_quality(r), 4) if _quality(r) is not None else None),
            "Efficiency": efficiency_score(r),
        })
    df = pd.DataFrame(rows)
    if not df.empty and df["Efficiency"].notna().any():
        df = df.sort_values("Efficiency", ascending=False, na_position="last")
    return df.reset_index(drop=True)


def best_variant(runs: List[dict]) -> Optional[dict]:
    """The run with the highest efficiency score, or None."""
    scored = [(efficiency_score(r), r) for r in runs]
    scored = [(s, r) for s, r in scored if s is not None]
    if not scored:
        return None
    return max(scored, key=lambda t: t[0])[1]


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #

def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _minmax(values, invert=False):
    """Normalize a list to [0,1]. invert=True => smaller raw value -> larger
    normalized (used for Memory / Model Size where less is better)."""
    vals = np.array([v if v is not None else np.nan for v in values], dtype=float)
    finite = vals[np.isfinite(vals)]
    if finite.size == 0:
        return np.zeros_like(vals)
    lo, hi = np.nanmin(vals), np.nanmax(vals)
    if math.isclose(lo, hi):
        norm = np.ones_like(vals) * 0.5
    else:
        norm = (vals - lo) / (hi - lo)
    if invert:
        norm = 1.0 - norm
    return np.nan_to_num(norm, nan=0.0)


def plot_radar(runs: List[dict]):
    """Spider chart: Quality / Speed / Memory / Model Size, one polygon per
    variant, oriented so outward = better."""
    labels = [r.get("tag", "?") for r in runs]
    axes_names = ["Quality", "Speed", "Memory", "Model Size"]

    quality = _minmax([_quality(r) for r in runs])
    speed = _minmax([_speed(r) for r in runs])
    memory = _minmax([_memory_gb(r) for r in runs], invert=True)      # less = better
    size = _minmax([_model_size_gb(r) for r in runs], invert=True)    # less = better
    data = np.vstack([quality, speed, memory, size]).T  # rows=variants, cols=axes

    n = len(axes_names)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # close the loop

    fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw=dict(polar=True))
    cmap = plt.get_cmap("viridis")
    for i, (label, row) in enumerate(zip(labels, data)):
        vals = row.tolist() + row[:1].tolist()
        color = cmap(i / max(len(labels) - 1, 1))
        ax.plot(angles, vals, linewidth=2, label=label, color=color)
        ax.fill(angles, vals, alpha=0.12, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(axes_names)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["", "", "", ""])
    ax.set_ylim(0, 1)
    ax.set_title("Trade-off radar (outward = better)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=9)
    return fig


def plot_efficiency(runs: List[dict]):
    """Bar chart of the composite efficiency score, ranked high -> low."""
    pairs = [(r.get("tag", "?"), efficiency_score(r)) for r in runs]
    pairs = [(t, s) for t, s in pairs if s is not None]
    if not pairs:
        return None
    pairs.sort(key=lambda p: p[1], reverse=True)
    tags = [p[0] for p in pairs]
    scores = [p[1] for p in pairs]

    fig, ax = plt.subplots(figsize=(8, 5))
    cmap = plt.get_cmap("viridis")
    colors = [cmap(i / max(len(tags) - 1, 1)) for i in range(len(tags))]
    bars = ax.bar(tags, scores, color=colors)
    ax.bar_label(bars, fmt="%.3f", padding=3)
    ax.set_title("Overall efficiency = (Quality x Speed) / Memory")
    ax.set_ylabel("Efficiency score")
    ax.set_ylim(top=max(scores) * 1.2)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    return fig


def _load_time_chart(runs: List[dict]):
    pairs = [(r.get("tag", "?"), _load_time(r)) for r in runs]
    pairs = [(t, s) for t, s in pairs if s is not None]
    if not pairs:
        return None
    tags = [p[0] for p in pairs]
    times = [p[1] for p in pairs]
    fig, ax = plt.subplots(figsize=(8, 5))
    cmap = plt.get_cmap("viridis")
    colors = [cmap(i / max(len(tags) - 1, 1)) for i in range(len(tags))]
    bars = ax.bar(tags, times, color=colors)
    ax.bar_label(bars, fmt="%.2f", padding=3)
    ax.set_title("Quantization / load time")
    ax.set_ylabel("seconds")
    ax.set_ylim(top=max(times) * 1.2)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    return fig


def build_charts(runs: List[dict]) -> Dict[str, str]:
    """Render every chart to a base64 PNG. Missing sections are skipped."""
    charts: Dict[str, str] = {}

    speed_df = viz.speed_dataframe(runs)
    mem_df = viz.memory_dataframe(runs)
    smart_df = viz.smartness_dataframe(runs)

    if not speed_df.empty:
        fig, axes = plt.subplots(1, 4, figsize=(20, 5))
        viz.plot_speed(axes, speed_df)
        fig.suptitle("Speed", fontsize=15, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.92])
        charts["speed"] = _fig_to_base64(fig)

    if not mem_df.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        viz.plot_memory(ax, mem_df)
        fig.tight_layout()
        charts["memory"] = _fig_to_base64(fig)

    if not smart_df.empty:
        fig, ax = plt.subplots(figsize=(9, 5))
        viz.plot_smartness(ax, smart_df)
        fig.tight_layout()
        charts["quality"] = _fig_to_base64(fig)

    lt = _load_time_chart(runs)
    if lt is not None:
        charts["load_time"] = _fig_to_base64(lt)

    if len(runs) >= 1:
        charts["radar"] = _fig_to_base64(plot_radar(runs))

    eff = plot_efficiency(runs)
    if eff is not None:
        charts["efficiency"] = _fig_to_base64(eff)

    return charts


# --------------------------------------------------------------------------- #
# Report writers
# --------------------------------------------------------------------------- #

def to_csv(runs: List[dict], path: Optional[str] = None) -> str:
    df = summary_dataframe(runs)
    csv_text = df.to_csv(index=False)
    if path:
        Path(path).write_text(csv_text, encoding="utf-8")
    return csv_text


def to_markdown(runs: List[dict], path: Optional[str] = None) -> str:
    df = summary_dataframe(runs)
    best = best_variant(runs)
    lines = ["# LLM Quantization Benchmark Report", ""]
    if best is not None:
        lines += [
            f"**Best variant (efficiency):** `{best.get('tag')}` "
            f"— score {efficiency_score(best)}", "",
            "> Efficiency = (Quality × Speed) / Memory", "",
        ]
    lines.append(df.to_markdown(index=False))
    md = "\n".join(lines)
    if path:
        Path(path).write_text(md, encoding="utf-8")
    return md


_HTML_STYLE = """
<style>
  .qz-report { font-family: system-ui, -apple-system, Segoe UI, sans-serif;
               color: #1a1a1a; max-width: 1100px; margin: 0 auto; }
  .qz-report h1 { font-size: 1.6rem; margin-bottom: .2rem; }
  .qz-callout { background: #eef6ee; border: 1px solid #bcd8bc; border-radius: 10px;
                padding: 14px 18px; margin: 16px 0; font-size: 1.05rem; }
  .qz-callout b { color: #14611a; }
  .qz-report table { border-collapse: collapse; width: 100%; margin: 14px 0;
                     font-size: .9rem; }
  .qz-report th, .qz-report td { border: 1px solid #ddd; padding: 6px 10px;
                                 text-align: right; }
  .qz-report th { background: #f4f4f4; text-align: right; }
  .qz-report td:first-child, .qz-report th:first-child { text-align: left; }
  .qz-grid { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 8px; }
  .qz-card { flex: 1 1 420px; }
  .qz-card h3 { font-size: 1rem; margin: 6px 0; }
  .qz-card img { width: 100%; height: auto; border: 1px solid #eee; border-radius: 8px; }
  @media (prefers-color-scheme: dark) {
    .qz-report { color: #eee; }
    .qz-callout { background: #16311a; border-color: #2c6b33; }
    .qz-callout b { color: #7fdd8a; }
    .qz-report th { background: #2a2a2a; }
    .qz-report th, .qz-report td { border-color: #444; }
    .qz-card img { border-color: #333; }
  }
</style>
"""


def _df_to_html_table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, border=0, na_rep="n/a", float_format=lambda x: f"{x:.3f}")


def to_html(runs: List[dict], path: Optional[str] = None) -> str:
    """Self-contained HTML report string (charts embedded as base64)."""
    if not runs:
        return "<div class='qz-report'><p>No benchmark runs to report.</p></div>"

    df = summary_dataframe(runs)
    charts = build_charts(runs)
    best = best_variant(runs)

    parts = [_HTML_STYLE, "<div class='qz-report'>",
             "<h1>LLM Quantization Benchmark Report</h1>"]

    if best is not None:
        parts.append(
            f"<div class='qz-callout'>🏆 Best variant by efficiency: "
            f"<b>{best.get('tag')}</b> — score <b>{efficiency_score(best)}</b>"
            f"<br><small>Efficiency = (Quality × Speed) / Memory</small></div>"
        )

    parts.append("<h2>Summary</h2>")
    parts.append(_df_to_html_table(df))

    chart_titles = [
        ("efficiency", "Efficiency ranking"),
        ("radar", "Trade-off radar"),
        ("speed", "Speed"),
        ("memory", "Memory footprint"),
        ("quality", "Quality (accuracy)"),
        ("load_time", "Load / quantization time"),
    ]
    parts.append("<h2>Charts</h2><div class='qz-grid'>")
    for key, title in chart_titles:
        if key in charts:
            parts.append(
                f"<div class='qz-card'><h3>{title}</h3>"
                f"<img alt='{title}' src='data:image/png;base64,{charts[key]}'/></div>"
            )
    parts.append("</div></div>")

    html = "\n".join(parts)
    if path:
        Path(path).write_text(html, encoding="utf-8")
    return html


def write_all(runs: List[dict], out_dir: str = "./benchmark_results") -> Dict[str, str]:
    """Write CSV, Markdown and HTML report files; return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": str(out / "report.csv"),
        "markdown": str(out / "report.md"),
        "html": str(out / "report.html"),
    }
    to_csv(runs, paths["csv"])
    to_markdown(runs, paths["markdown"])
    to_html(runs, paths["html"])
    return paths


if __name__ == "__main__":
    # Render reports from existing JSON runs in a folder.
    import argparse
    import glob
    import json

    parser = argparse.ArgumentParser(description="Build reports from benchmark JSON runs")
    parser.add_argument("--results-dir", default="./benchmark_results")
    args = parser.parse_args()

    files = sorted(glob.glob(str(Path(args.results_dir) / "*.json")))
    runs = []
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("_source_file", Path(fp).name)
        runs.append(data)

    paths = write_all(runs, out_dir=args.results_dir)
    print("Wrote:", json.dumps(paths, indent=2))
