#!/usr/bin/env python3
"""
pipeline.py — the automatic Benchmark Runner / orchestrator.

Driven entirely by a `config.Config`. For every (model x quantization) pair it:

  1. skips the variant if its method isn't available (no GPU / missing dep),
  2. loads/quantizes the model (recording load time),
  3. measures speed + memory (reusing benchmark_llm),
  4. scores quality on the configured lm-eval tasks (on the loaded object),
  5. writes a timestamped JSON run to config.output_dir,
  6. frees the model before moving on.

Returns the list of run dicts (also usable directly by reports.py).

Run standalone:
    python pipeline.py --config config.yaml
"""

from __future__ import annotations

import gc
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

import torch

import benchmark_llm as bench
from config import Config, load_config
from quantization import METHODS, load_quantized


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _tag(model: str, method: str) -> str:
    """Human/file-friendly label, e.g. TinyLlama-1.1B-Chat-v1.0_nf4."""
    return f"{Path(model).name}_{method}"


def _report(cb: Optional[Callable], frac: float, msg: str) -> None:
    _log(msg)
    if cb is not None:
        try:
            cb(frac, msg)
        except Exception:
            # Progress reporting must never break the run.
            pass


def run_variant(base_model: str, method: str, cfg: Config, device: str) -> dict:
    """Benchmark a single (model, method) pair and return its run dict."""
    source_id = None
    if method == "awq":
        source_id = cfg.awq_id_for(base_model)
    elif method == "gptq":
        source_id = cfg.gptq_id_for(base_model)

    tag = _tag(base_model, method)
    report = {
        "tag": tag,
        "model": base_model,
        "method": method,
        "device": device,
        "timestamp_utc": _timestamp(),
    }

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()

    _log(f"Loading {tag} ...")
    model, tokenizer, meta = load_quantized(base_model, method, source_id=source_id)
    report["quantization"] = meta  # includes load_time_sec, source_id, on-disk size

    # 1) Speed
    _log(f"  speed benchmark ({tag}) ...")
    prompts = cfg.prompts or bench.DEFAULT_PROMPTS
    report["speed"] = bench.benchmark_speed(
        model, tokenizer, device, prompts,
        max_new_tokens=cfg.generation.max_new_tokens,
    )

    # 2) Memory
    _log(f"  memory benchmark ({tag}) ...")
    report["memory"] = bench.benchmark_memory(model, meta["source_id"], device)
    # Prefer the quantization engine's cache-resolved size when present.
    if meta.get("on_disk_size_gb") is not None:
        report["memory"]["on_disk_size_gb"] = meta["on_disk_size_gb"]

    # 3) Quality (score the already-loaded object)
    _log(f"  quality benchmark ({tag}) ...")
    report["smartness"] = bench.benchmark_smartness_loaded(
        model, tokenizer,
        tasks=cfg.benchmarks,
        limit=cfg.generation.smartness_limit,
    )

    # Free memory before the next variant.
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    return report


def run_pipeline(cfg: Config, progress_cb: Optional[Callable] = None) -> List[dict]:
    """
    Execute the full matrix (cfg.models x cfg.quantizations).

    progress_cb(fraction: float, message: str) is called as work proceeds so a
    UI (e.g. Gradio) can show progress. Unavailable variants are skipped with a
    logged reason rather than aborting the run.
    """
    device = bench.get_device()
    _log(f"Device: {device}")

    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(m, q) for m in cfg.models for q in cfg.quantizations]
    total = len(jobs)
    runs: List[dict] = []

    for i, (base_model, method) in enumerate(jobs):
        frac = i / total if total else 0.0
        tag = _tag(base_model, method)

        # Availability gate (clear skip, no crash).
        spec = METHODS.get(method)
        source_id = (cfg.awq_id_for(base_model) if method == "awq"
                     else cfg.gptq_id_for(base_model) if method == "gptq"
                     else None)
        ok, reason = (spec.available(source_id) if spec else (False, f"unknown method {method}"))
        if not ok:
            _report(progress_cb, frac, f"Skipping {tag}: {reason}")
            continue

        _report(progress_cb, frac, f"[{i+1}/{total}] Benchmarking {tag} ...")
        try:
            report = run_variant(base_model, method, cfg, device)
        except Exception as e:  # keep going even if one variant fails
            _report(progress_cb, frac, f"FAILED {tag}: {type(e).__name__}: {e}")
            continue

        out_path = out_dir / f"{report['tag']}_{report['timestamp_utc']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        report["_source_file"] = out_path.name
        runs.append(report)
        _report(progress_cb, (i + 1) / total, f"Wrote {out_path.name}")

    _report(progress_cb, 1.0, f"Done. {len(runs)} variant(s) benchmarked.")
    return runs


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the quantization benchmark pipeline")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    runs = run_pipeline(cfg)

    # Also emit reports for CLI users.
    try:
        import reports
        reports.write_all(runs, out_dir=cfg.output_dir)
        _log(f"Reports written to {cfg.output_dir}/")
    except Exception as e:
        _log(f"(report generation skipped: {e})")

    print(json.dumps([{"tag": r["tag"]} for r in runs], indent=2))


if __name__ == "__main__":
    main()
