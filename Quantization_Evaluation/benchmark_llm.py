#!/usr/bin/env python3
"""
benchmark_llm.py

Benchmarks a Hugging Face causal LM on:
  1. Speed    -> tokens/sec, latency, throughput, TTFT
  2. Memory   -> on-disk model size, peak GPU/CPU memory during inference
  3. Smartness-> MMLU, GSM8K, HumanEval, TruthfulQA, HellaSwag (via lm-eval)

Each run is written as a timestamped JSON file to --output-dir so you can
run this against multiple model variants (fp16, AWQ, GPTQ, etc.) and diff
the results afterwards.

Install:
    pip install torch transformers accelerate lm-eval

For HumanEval (executes model-generated code to check correctness), you
must explicitly opt in:
    export HF_ALLOW_CODE_EVAL=1

Usage:
    python benchmark_llm.py --model google/gemma-2-2b --tag fp16
    python benchmark_llm.py --model ./gemma-2-2b-awq-4bit --tag awq4bit
    python benchmark_llm.py --model ./gemma-2-2b-awq-4bit --tag awq4bit --skip-smartness
"""

import argparse
import gc
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import torch


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def dir_size_bytes(path: str) -> int:
    """Sum file sizes under a local directory. Returns 0 for a Hub repo id
    (not a local path) — disk size for those isn't meaningful pre-download."""
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return 0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def bytes_to_gb(b: int) -> float:
    return round(b / (1024 ** 3), 3)


# --------------------------------------------------------------------------- #
# 1. Speed benchmark
# --------------------------------------------------------------------------- #

def benchmark_speed(model, tokenizer, device, prompts, max_new_tokens=128, warmup=1):
    """
    Measures:
      - TTFT: time to first generated token (prefill + first decode step)
      - per-request latency: total wall time for a full generation
      - tokens/sec: decode-phase throughput per request
      - throughput: total generated tokens / total wall time across all prompts
    """
    results = []

    # Warmup run(s) - not counted, lets CUDA kernels/caches settle
    for _ in range(warmup):
        inputs = tokenizer(prompts[0], return_tensors="pt").to(device)
        with torch.no_grad():
            model.generate(**inputs, max_new_tokens=16, do_sample=False)
    if device == "cuda":
        torch.cuda.synchronize()

    total_generated_tokens = 0
    total_wall_time = 0.0

    for i, prompt in enumerate(prompts):
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        input_len = inputs["input_ids"].shape[1]

        if device == "cuda":
            torch.cuda.synchronize()
        t_start = time.perf_counter()

        # TTFT: generate exactly 1 token to capture prefill + first decode step
        with torch.no_grad():
            first_out = model.generate(
                **inputs, max_new_tokens=1, do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        if device == "cuda":
            torch.cuda.synchronize()
        t_first_token = time.perf_counter()
        ttft = t_first_token - t_start

        # Full generation for latency / throughput
        with torch.no_grad():
            out = model.generate(
                **inputs, max_new_tokens=max_new_tokens, do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        if device == "cuda":
            torch.cuda.synchronize()
        t_end = time.perf_counter()

        latency = t_end - t_start
        gen_tokens = out.shape[1] - input_len
        tok_per_sec = gen_tokens / latency if latency > 0 else 0.0

        total_generated_tokens += gen_tokens
        total_wall_time += latency

        results.append({
            "prompt_index": i,
            "input_tokens": input_len,
            "generated_tokens": gen_tokens,
            "ttft_sec": round(ttft, 4),
            "latency_sec": round(latency, 4),
            "tokens_per_sec": round(tok_per_sec, 2),
        })
        log(f"  prompt {i}: TTFT={ttft:.3f}s  latency={latency:.3f}s  "
            f"{tok_per_sec:.1f} tok/s")

    throughput = total_generated_tokens / total_wall_time if total_wall_time > 0 else 0.0

    return {
        "per_prompt": results,
        "avg_ttft_sec": round(sum(r["ttft_sec"] for r in results) / len(results), 4),
        "avg_latency_sec": round(sum(r["latency_sec"] for r in results) / len(results), 4),
        "avg_tokens_per_sec": round(
            sum(r["tokens_per_sec"] for r in results) / len(results), 2
        ),
        "overall_throughput_tok_per_sec": round(throughput, 2),
    }


# --------------------------------------------------------------------------- #
# 2. Memory benchmark
# --------------------------------------------------------------------------- #

def benchmark_memory(model, model_path, device):
    on_disk_bytes = dir_size_bytes(model_path)

    param_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    buffer_bytes = sum(b.numel() * b.element_size() for b in model.buffers())
    n_params = sum(p.numel() for p in model.parameters())

    mem = {
        "on_disk_size_gb": bytes_to_gb(on_disk_bytes) if on_disk_bytes else None,
        "in_memory_param_size_gb": bytes_to_gb(param_bytes + buffer_bytes),
        "num_parameters": n_params,
        "num_parameters_billions": round(n_params / 1e9, 3),
    }

    if device == "cuda":
        mem["gpu_allocated_gb"] = bytes_to_gb(torch.cuda.memory_allocated())
        mem["gpu_reserved_gb"] = bytes_to_gb(torch.cuda.memory_reserved())
        mem["gpu_peak_allocated_gb"] = bytes_to_gb(torch.cuda.max_memory_allocated())

    return mem


# --------------------------------------------------------------------------- #
# 3. Smartness benchmark (lm-eval-harness)
# --------------------------------------------------------------------------- #

DEFAULT_TASKS = {
    "mmlu": "mmlu",
    "gsm8k": "gsm8k",
    "humaneval": "humaneval",
    "truthfulqa": "truthfulqa_mc2",
    "hellaswag": "hellaswag",
}


def _filter_task_list(tasks):
    """Drop humaneval unless the user has opted into code execution."""
    if "humaneval" in tasks and os.environ.get("HF_ALLOW_CODE_EVAL") != "1":
        log("Skipping humaneval: set HF_ALLOW_CODE_EVAL=1 to allow code "
            "execution required for this benchmark.")
        tasks = [t for t in tasks if t != "humaneval"]
    return tasks


def _summarize_lmeval(raw):
    """Keep only primary numeric metrics, drop the "_stderr" clutter."""
    summary = {}
    for task_name, metrics in raw["results"].items():
        summary[task_name] = {
            k: v for k, v in metrics.items()
            if isinstance(v, (int, float)) and not k.endswith("_stderr,none")
        }
    return summary


def benchmark_smartness(model_path, tasks=None, limit=None, batch_size="auto"):
    """
    Runs lm-eval-harness tasks against a model *by path/id* (lm-eval loads it).
    `limit` caps the number of examples per task (use e.g. 100 for a fast
    sanity pass; leave None for the full, publication-comparable score).
    """
    try:
        import lm_eval
        from lm_eval.models.huggingface import HFLM
    except ImportError:
        log("lm_eval not installed. Run: pip install lm-eval")
        return {"error": "lm_eval not installed"}

    tasks = _filter_task_list(tasks or list(DEFAULT_TASKS.values()))
    if not tasks:
        return {}

    lm = HFLM(pretrained=model_path, batch_size=batch_size)

    log(f"Running lm-eval tasks: {tasks} (limit={limit})")
    raw = lm_eval.simple_evaluate(model=lm, tasks=tasks, limit=limit)
    return _summarize_lmeval(raw)


def benchmark_smartness_loaded(model, tokenizer, tasks=None, limit=None,
                               batch_size="auto"):
    """
    Same as benchmark_smartness, but scores an *already-loaded* model object.

    This is required for bitsandbytes-quantized models (int8/nf4), which are
    quantized at load time and only exist in memory — they can't be reloaded
    from a path. Passing the live model object to HFLM avoids a second load
    (and a second, unquantized copy of the weights).
    """
    try:
        import lm_eval
        from lm_eval.models.huggingface import HFLM
    except ImportError:
        log("lm_eval not installed. Run: pip install lm-eval")
        return {"error": "lm_eval not installed"}

    tasks = _filter_task_list(tasks or list(DEFAULT_TASKS.values()))
    if not tasks:
        return {}

    lm = HFLM(pretrained=model, tokenizer=tokenizer, batch_size=batch_size)

    log(f"Running lm-eval tasks: {tasks} (limit={limit})")
    raw = lm_eval.simple_evaluate(model=lm, tasks=tasks, limit=limit)
    return _summarize_lmeval(raw)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

DEFAULT_PROMPTS = [
    "Explain the difference between supervised and unsupervised learning.",
    "Write a short story about a robot learning to paint.",
    "What are the main causes of inflation in an economy?",
    "Describe how a binary search algorithm works.",
]


def main():
    parser = argparse.ArgumentParser(description="Benchmark an LLM: speed, memory, smartness")
    parser.add_argument("--model", required=True, help="HF model id or local path")
    parser.add_argument("--tag", default=None,
                         help="Label for this run, e.g. 'fp16' or 'awq4bit' (default: model name)")
    parser.add_argument("--output-dir", default="./benchmark_results")
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--dtype", default="auto", choices=["auto", "float16", "bfloat16", "float32"])
    parser.add_argument("--skip-speed", action="store_true")
    parser.add_argument("--skip-memory", action="store_true")
    parser.add_argument("--skip-smartness", action="store_true")
    parser.add_argument("--smartness-tasks", nargs="*", default=None,
                         help="Subset of tasks, e.g. --smartness-tasks mmlu gsm8k")
    parser.add_argument("--smartness-limit", type=int, default=None,
                         help="Cap examples/task for a quick pass (omit for full eval)")
    args = parser.parse_args()

    tag = args.tag or Path(args.model).name
    device = get_device()
    log(f"Device: {device}")

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(args.output_dir) / f"{tag}_{timestamp}.json"

    report = {
        "tag": tag,
        "model": args.model,
        "device": device,
        "timestamp_utc": timestamp,
    }

    # --- Load model once, reuse for speed + memory sections ---
    if not args.skip_speed or not args.skip_memory:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        log(f"Loading model: {args.model}")
        dtype = None if args.dtype == "auto" else getattr(torch, args.dtype)
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            torch_dtype=dtype or "auto",
            device_map="auto" if device == "cuda" else None,
        )
        if device != "cuda":
            model = model.to(device)
        model.eval()

        if device == "cuda":
            torch.cuda.reset_peak_memory_stats()

        if not args.skip_speed:
            log("Running speed benchmark...")
            report["speed"] = benchmark_speed(
                model, tokenizer, device, DEFAULT_PROMPTS,
                max_new_tokens=args.max_new_tokens,
            )

        if not args.skip_memory:
            log("Running memory benchmark...")
            report["memory"] = benchmark_memory(model, args.model, device)

        del model
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

    # --- Smartness: lm-eval loads/manages the model itself ---
    if not args.skip_smartness:
        log("Running smartness benchmarks (this can take a while)...")
        report["smartness"] = benchmark_smartness(
            args.model,
            tasks=args.smartness_tasks,
            limit=args.smartness_limit,
        )

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"Results written to {out_path}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
