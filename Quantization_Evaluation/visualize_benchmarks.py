#!/usr/bin/env python3
"""
visualize_benchmarks.py

Reads one or more JSON files produced by benchmark_llm.py and renders
comparison charts across model variants (e.g. fp16 vs awq4bit vs gptq).

Usage:
    # Compare every run in a folder
    python visualize_benchmarks.py --results-dir ./benchmark_results

    # Or point at specific files
    python visualize_benchmarks.py --files run1.json run2.json

Outputs (written to --output-dir, default ./benchmark_plots):
    speed.png       - avg tokens/sec, latency, TTFT, throughput per model
    memory.png      - GPU memory + param size per model
    smartness.png   - accuracy per benchmark task per model
    combined.png    - all of the above as one dashboard image

Missing sections (e.g. a run with --skip-smartness) are handled gracefully -
that model just won't appear in the corresponding chart.
"""

import argparse
import glob
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", context="talk")
PALETTE = "viridis"


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_runs(paths):
    runs = []
    for p in paths:
        with open(p) as f:
            data = json.load(f)
        data["_source_file"] = os.path.basename(p)
        runs.append(data)
    if not runs:
        raise SystemExit("No benchmark JSON files found.")
    return runs


def speed_dataframe(runs):
    rows = []
    for r in runs:
        s = r.get("speed")
        if not s:
            continue
        rows.append({
            "model": r["tag"],
            "Avg Tokens/sec": s["avg_tokens_per_sec"],
            "Avg Latency (s)": s["avg_latency_sec"],
            "Avg TTFT (s)": s["avg_ttft_sec"],
            "Throughput (tok/s)": s["overall_throughput_tok_per_sec"],
        })
    return pd.DataFrame(rows)


def memory_dataframe(runs):
    rows = []
    for r in runs:
        m = r.get("memory")
        if not m:
            continue
        row = {
            "model": r["tag"],
            "Param size (GB)": m.get("in_memory_param_size_gb"),
            "GPU allocated (GB)": m.get("gpu_allocated_gb"),
            "GPU peak (GB)": m.get("gpu_peak_allocated_gb"),
        }
        if m.get("on_disk_size_gb") is not None:
            row["On-disk size (GB)"] = m["on_disk_size_gb"]
        rows.append(row)
    return pd.DataFrame(rows)


def smartness_dataframe(runs):
    rows = []
    for r in runs:
        sm = r.get("smartness")
        if not sm:
            continue
        for task, metrics in sm.items():
            for metric_name, value in metrics.items():
                if not isinstance(value, (int, float)) or metric_name == "sample_len":
                    continue
                rows.append({
                    "model": r["tag"],
                    "task": f"{task} ({metric_name.split(',')[0]})",
                    "score": value,
                })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Plotting
# --------------------------------------------------------------------------- #

def plot_speed(ax_group, df):
    metrics = ["Avg Tokens/sec", "Throughput (tok/s)", "Avg Latency (s)", "Avg TTFT (s)"]
    for ax, metric in zip(ax_group, metrics):
        if df.empty or metric not in df:
            ax.axis("off")
            continue
        sns.barplot(data=df, x="model", y=metric, hue="model", ax=ax,
                    palette=PALETTE, legend=False)
        ax.set_title(metric, pad=14)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_ylim(top=df[metric].max() * 1.2)
        ax.bar_label(ax.containers[0], fmt="%.3f", padding=3)
        ax.tick_params(axis="x", rotation=20)


def plot_memory(ax, df):
    if df.empty:
        ax.axis("off")
        return
    value_cols = [c for c in df.columns if c != "model"]
    melted = df.melt(id_vars="model", value_vars=value_cols,
                      var_name="metric", value_name="GB")
    melted = melted.dropna(subset=["GB"])
    sns.barplot(data=melted, x="model", y="GB", hue="metric", ax=ax, palette=PALETTE)
    ax.set_title("Memory footprint")
    ax.set_xlabel("")
    ax.set_ylabel("GB")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(title="", loc="upper right", fontsize=10)


def plot_smartness(ax, df):
    if df.empty:
        ax.axis("off")
        return
    sns.barplot(data=df, x="task", y="score", hue="model", ax=ax, palette=PALETTE)
    ax.set_title("Capability benchmarks (accuracy)")
    ax.set_xlabel("")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1)
    ax.tick_params(axis="x", rotation=20)
    ax.legend(title="", loc="upper right", fontsize=10)


def build_dashboard(speed_df, memory_df, smartness_df, out_path, model_tags):
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 4, height_ratios=[1, 1, 1.1])

    speed_axes = [fig.add_subplot(gs[0, i]) for i in range(4)]
    plot_speed(speed_axes, speed_df)

    mem_ax = fig.add_subplot(gs[1, :2])
    plot_memory(mem_ax, memory_df)

    smart_ax = fig.add_subplot(gs[1:, 2:])
    plot_smartness(smart_ax, smartness_df)

    fig.suptitle(f"LLM Benchmark Comparison: {', '.join(model_tags)}",
                 fontsize=18, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="Visualize benchmark_llm.py JSON results")
    parser.add_argument("--results-dir", default=None,
                         help="Folder containing *.json result files")
    parser.add_argument("--files", nargs="*", default=None,
                         help="Explicit list of JSON files (alternative to --results-dir)")
    parser.add_argument("--output-dir", default="./benchmark_plots")
    args = parser.parse_args()

    if args.files:
        paths = args.files
    elif args.results_dir:
        paths = sorted(glob.glob(os.path.join(args.results_dir, "*.json")))
    else:
        paths = sorted(glob.glob("./benchmark_results/*.json"))

    runs = load_runs(paths)
    model_tags = [r["tag"] for r in runs]
    print(f"Loaded {len(runs)} run(s): {model_tags}")

    os.makedirs(args.output_dir, exist_ok=True)

    speed_df = speed_dataframe(runs)
    memory_df = memory_dataframe(runs)
    smartness_df = smartness_dataframe(runs)

    # Individual charts
    if not speed_df.empty:
        fig, axes = plt.subplots(1, 4, figsize=(20, 5))
        plot_speed(axes, speed_df)
        fig.suptitle("Speed", fontsize=16, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        fig.savefig(Path(args.output_dir) / "speed.png", dpi=150)
        plt.close(fig)

    if not memory_df.empty:
        fig, ax = plt.subplots(figsize=(8, 6))
        plot_memory(ax, memory_df)
        fig.tight_layout()
        fig.savefig(Path(args.output_dir) / "memory.png", dpi=150)
        plt.close(fig)

    if not smartness_df.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        plot_smartness(ax, smartness_df)
        fig.tight_layout()
        fig.savefig(Path(args.output_dir) / "smartness.png", dpi=150)
        plt.close(fig)

    # Combined dashboard
    build_dashboard(speed_df, memory_df, smartness_df,
                     Path(args.output_dir) / "combined.png", model_tags)

    print(f"Charts written to {args.output_dir}/")


if __name__ == "__main__":
    main()
