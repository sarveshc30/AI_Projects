# Automated LLM Quantization Benchmark — Architecture & Interview Notes

> Internal reference doc summarizing the system design, technology choices, and
> the reasoning behind them — written to prepare for interview questions about
> this project.

---

## 1. One-line pitch

A config-driven pipeline that takes a Hugging Face causal LM, produces several
quantized variants of it (FP32/FP16/INT8/NF4/AWQ/GPTQ), benchmarks each on
**speed, memory, and quality**, and ranks them with a single **efficiency
score**, surfaced either via a Gradio web UI or the CLI.

## 2. Problem it solves

Quantization trades accuracy for speed/memory, but the trade-off is model- and
hardware-specific — you can't know in advance whether NF4 on model X will lose
2 points of accuracy for a 3x memory win, or whether it's not worth it. This
project automates the "quantize N ways, measure everything, compare" loop so
that decision is empirical instead of guesswork, and repeatable across models.

## 3. High-level architecture

```
config.yaml ──► config.py (Config dataclass, validated)
                     │
                     ▼
        ┌─────────────────────────────┐
        │   quantization.py           │  Quantization Engine
        │   registry of methods:      │  fp32/fp16 (transformers),
        │   fp32,fp16,int8,nf4,       │  int8/nf4 (bitsandbytes),
        │   awq,gptq                  │  awq/gptq (pre-quantized hub ckpt)
        │   -> (model, tokenizer,     │
        │       meta incl. load_time) │
        └──────────────┬──────────────┘
                        ▼
        ┌─────────────────────────────┐
        │   pipeline.py               │  Orchestrator
        │   for model x quantization: │
        │     - availability gate     │  (skip w/ reason, never crash)
        │     - load + time it        │
        │     - benchmark_llm calls   │
        │     - write JSON run        │
        └──────────────┬──────────────┘
                        ▼
        ┌─────────────────────────────┐
        │   benchmark_llm.py          │  Measurement layer
        │   - speed (TTFT, latency,   │
        │     tok/s, throughput)      │
        │   - memory (params, VRAM,   │
        │     on-disk size)           │
        │   - quality (lm-eval-       │
        │     harness: MMLU, GSM8K,   │
        │     HellaSwag, TruthfulQA,  │
        │     HumanEval)              │
        └──────────────┬──────────────┘
                        ▼
        ┌─────────────────────────────┐
        │   reports.py /              │  Reporting layer
        │   visualize_benchmarks.py   │  - efficiency = (Quality×Speed)/Memory
        │                             │  - CSV / Markdown / self-contained HTML
        │                             │  - matplotlib/seaborn bar + radar charts
        └──────────────┬──────────────┘
                        ▼
        ┌─────────────────────────────┐
        │   app.py                    │  Gradio frontend
        │   form -> run_pipeline ->   │  (inline HTML report + file downloads)
        │   inline report + downloads │
        └─────────────────────────────┘
```

Each stage is a separate module with a narrow contract, so the same pipeline
can be driven from `config.yaml` (CLI) or per-request UI state (Gradio) without
duplicating logic — `app.py` just builds a `Config` object and calls the same
`run_pipeline()` the CLI uses.

## 4. Technology stack

| Layer | Technology | Why |
|---|---|---|
| Model loading / inference | `transformers`, `torch`, `accelerate` | Standard HF stack; `device_map="auto"` for multi-GPU/CPU placement |
| Quantization backends | `bitsandbytes` (INT8/NF4), `autoawq`, `optimum`/`auto-gptq` | Each is the reference implementation for its method; kept as **optional** imports so the app degrades gracefully instead of hard-requiring every backend |
| Quality evaluation | `lm-eval` (EleutherAI's lm-evaluation-harness) | Industry-standard harness for MMLU/GSM8K/HellaSwag/TruthfulQA/HumanEval — avoids hand-rolling eval logic and scoring is directly comparable to published numbers |
| Config | `pyyaml` + a validated `dataclasses.Config` | Single source of truth; no benchmark parameters hardcoded in Python |
| Reporting / charts | `pandas`, `matplotlib`, `seaborn`, `tabulate` | DataFrame-based aggregation; matplotlib in `Agg` (headless) backend so it works on a server with no display; charts embedded as **base64 PNGs** so the HTML report is a single self-contained file (no static asset hosting needed) |
| Frontend | `gradio` | Fastest way to get a shareable web UI + progress bar for a Python ML pipeline; `share=True` gives a public URL for Colab use |
| Prototyping | Jupyter notebooks (`Biteandbytes.ipynb`, `Quantization_Testing.ipynb`) | Where the fp16/int8 and AWQ recipes were first worked out before being productionized into `quantization.py` |

## 5. Key design decisions (likely interview questions)

### Why a method **registry** (`QuantMethod` dataclass) instead of if/elif?
Each quantization method is described declaratively: its loader function, its
required CUDA/package dependencies, and whether it needs a pre-quantized hub
ID. `available()` on each method returns `(bool, reason)` so the pipeline can
skip unavailable variants with a clear logged reason instead of a stack trace.
Adding a new method = adding one entry to `METHODS`, not touching the
orchestrator.

### Why do AWQ/GPTQ load a **pre-quantized checkpoint** instead of quantizing live?
Both methods need a calibration pass over representative data to determine
quantization parameters — that's expensive and out of scope for a benchmarking
tool. Instead the config maps a base model to an already-quantized community
checkpoint on the Hub (e.g. TheBloke's AWQ/GPTQ repos), and `transformers`
auto-detects the baked-in `quantization_config`. This keeps the benchmark
loop fast and focused on *measuring*, not *producing*, quantized weights.

### Why is `fp32` special-cased as the only CPU-capable method?
Half-precision matmul is unsupported/unstable on many CPU ops, and the
bitsandbytes/AWQ/GPTQ kernels are CUDA-only outright. Rather than crash on a
CPU-only laptop, `fp32.needs_cuda = False` and everything else is gated behind
`_has_cuda()` — so the whole pipeline (speed/memory/quality/reports) still
runs end-to-end on a laptop, just with one variant instead of five, which is
useful for local development/testing before a GPU run.

### Why measure quality on the **already-loaded** model object instead of reloading by path?
`bitsandbytes` INT8/NF4 quantization happens at *load time* and only exists in
memory — there's no serialized quantized checkpoint to point `lm-eval` at.
`benchmark_smartness_loaded()` passes the live `(model, tokenizer)` into
`lm_eval`'s `HFLM` wrapper directly, avoiding a second (unquantized) load and
keeping speed/memory/quality all measured against the exact same in-memory
weights.

### What is the **efficiency score** and why that formula?
```
efficiency = (Quality × Speed) / Memory
```
Quality = mean of the configured lm-eval task scores (0–1 accuracy-style
metrics), Speed = avg tokens/sec, Memory = peak VRAM GB (falls back to
in-memory param size if no GPU). It's a single ranking number that rewards
being simultaneously fast, accurate, and small, and penalizes any one axis
dominating — e.g. a tiny fast model that's inaccurate scores low, and so does
a huge accurate model that's slow. It intentionally returns `None`/"n/a" if
any component is missing rather than silently guessing.

### Why is nothing benchmark-related hardcoded in Python?
`config.yaml` is the single source of truth (models, quantizations,
benchmarks, generation params, output dir), loaded through a validated
`Config` dataclass (`config.py`). The Gradio UI (`app.py`) pre-populates its
form fields from this same file and builds a per-run `Config` via
`with_overrides()`/direct construction — so CLI and UI runs are configured
identically and validation logic lives in exactly one place.

### Why does the pipeline continue after a variant fails?
`run_pipeline()` wraps each `(model, method)` job in a try/except so one
crashing variant (OOM, missing dependency, flaky download) doesn't abort the
whole matrix — it logs `FAILED {tag}: ...` and moves to the next job. This
matters because these are long-running, resource-heavy jobs (multi-GB model
loads + lm-eval passes) where you don't want to lose completed results because
of one broken variant late in the run.

### Why base64-embed charts in the HTML report instead of writing PNG files + `<img src="...">`?
The HTML report needs to render **inline inside Gradio's `gr.HTML`
component**, which has no access to a static file server. Embedding charts as
`data:image/png;base64,...` makes the report a single portable string/file —
same reason CSV/Markdown/JSON are also offered as direct downloads via
`gr.File`.

### How is GPU memory measured accurately across variants?
`torch.cuda.reset_peak_memory_stats()` is called before each variant loads, so
`torch.cuda.max_memory_allocated()` reflects that variant's peak in isolation
rather than accumulating across the whole run. The model is explicitly
`del`eted and `torch.cuda.empty_cache()` is called after each variant before
moving to the next, to prevent memory from one variant leaking into the next
one's measurement.

### What's TTFT and why measure it separately from full latency?
Time-to-first-token is measured by generating exactly 1 token (`max_new_tokens=1`)
and timing that in isolation — it captures prefill (processing the prompt)
plus the first decode step, which is what a user perceives as "responsiveness"
in a streaming chat UI. It's reported alongside full-generation latency and
decode-phase tokens/sec because they answer different questions: TTFT ≈
perceived responsiveness, tokens/sec ≈ sustained decode throughput.

## 6. Data flow / file formats

- **Per-run JSON** (`benchmark_results/<tag>_<timestamp>.json`): the atomic
  unit of output — one file per `(model, quantization method)` pair, containing
  `quantization` (method, source id, load time, on-disk size), `speed`,
  `memory`, and `smartness` (lm-eval results) sections. This schema is shared
  between `benchmark_llm.py`'s standalone CLI and `pipeline.py`'s orchestrated
  runs, so `reports.py`/`visualize_benchmarks.py` can consume either.
- **Aggregated reports** (`report.csv` / `report.md` / `report.html`): built by
  `reports.py` from a list of run dicts — one row per variant, sorted by
  efficiency score descending.

## 7. Notable engineering practices

- **Graceful degradation over hard failures**: missing GPU, missing optional
  package (`autoawq`, `optimum`), or missing pre-quantized repo ID are all
  caught by `available()` and turned into a skip + logged reason, never an
  unhandled exception.
- **Timed everything**: even model loading/quantization itself is timed
  (`load_time_sec`) and treated as a first-class benchmark metric, not just an
  implementation detail — quantization cost (e.g. NF4's on-the-fly quant) is
  part of the real-world trade-off.
- **Headless-safe plotting**: `matplotlib.use("Agg")` set explicitly before
  any `pyplot` import in `reports.py`, so chart generation works on a
  server/Colab with no display.
- **Test coverage**: `c0b4272 fp32 baseline tests added` — CPU-only path has
  dedicated tests since it's the one path guaranteed to run in CI without a
  GPU.

## 8. Possible extensions (good "what would you improve" answers)

- Parallelize the model matrix across multiple GPUs instead of running
  variants sequentially.
- Cache tokenizer/prompt tokenization across variants of the same base model.
- Add a live-calibration AWQ/GPTQ path (instead of relying on pre-quantized
  Hub checkpoints) for models without a community quantized version.
- Persist run history in a small DB instead of flat JSON files, to support
  cross-run trend charts (e.g. efficiency over time as new methods are added).
