# Automated LLM Quantization Benchmark

Quantize a model into multiple variants (FP16, INT8, NF4, AWQ, GPTQ), benchmark
each on **speed / memory / quality**, and get a report with an overall
**efficiency score** — driven from a web frontend or the command line.

```text
                Input Model
                     │
                     ▼
     ┌────────────────────────────┐
     │ Quantization Engine        │   quantization.py
     │  FP16 · INT8 · NF4 · AWQ ·  │
     │  GPTQ                       │
     └─────────────┬──────────────┘
                   ▼
      Automatic Benchmark Runner        pipeline.py  → benchmark_llm.py
        Speed · Memory · Quality
                   │
                   ▼
      Dashboard + Report (HTML/CSV/MD)   reports.py / app.py
```

## Quick start (Colab / any CUDA GPU)

```python
!pip install -r requirements.txt
!python app.py            # prints a public Gradio share URL
```

Then enter a model name, pick quantizations + benchmark tasks, and click **Run
benchmark**. The HTML report (efficiency ranking, radar + bar charts, tables)
renders inline, with CSV / Markdown / JSON downloads.

### Command line

```bash
python pipeline.py --config config.yaml     # run the full matrix + write reports
python reports.py --results-dir ./benchmark_results   # (re)build reports from JSON
```

## Configuration — everything lives in `config.yaml`

Nothing benchmark-related is hardcoded in Python. Edit `config.yaml`:

```yaml
models:
  - TinyLlama/TinyLlama-1.1B-Chat-v1.0
quantizations: [fp16, int8, nf4]        # subset of fp16/int8/nf4/awq/gptq
benchmarks:    [hellaswag, truthfulqa_mc2]   # lm-eval task names
generation:
  max_new_tokens: 256
  smartness_limit: 50                   # examples per task (null = full eval)
awq_ids:
  TinyLlama/TinyLlama-1.1B-Chat-v1.0: TheBloke/TinyLlama-1.1B-Chat-v1.0-AWQ
gptq_ids:
  TinyLlama/TinyLlama-1.1B-Chat-v1.0: TheBloke/TinyLlama-1.1B-Chat-v1.0-GPTQ
```

## Metrics

| Group   | Metrics |
|---------|---------|
| Speed   | tokens/sec, TTFT, latency, throughput |
| Memory  | peak VRAM, param size, on-disk size, **load/quantization time** |
| Quality | MMLU, GSM8K, HellaSwag, TruthfulQA, HumanEval (via `lm-eval`) |
| Overall | **Efficiency = (Quality × Speed) / Memory** |

Charts include per-metric **bar graphs**, a **trade-off radar** (Quality /
Speed / Memory / Model Size, outward = better), and an **efficiency ranking**.

## Method / dependency matrix

| Method | Backend | Needs |
|--------|---------|-------|
| `fp16` | transformers | CUDA GPU |
| `int8` | bitsandbytes | CUDA GPU + `bitsandbytes` |
| `nf4`  | bitsandbytes 4-bit NF4 | CUDA GPU + `bitsandbytes` |
| `awq`  | pre-quantized hub checkpoint | CUDA GPU + `autoawq`, an `awq_ids` entry |
| `gptq` | pre-quantized hub checkpoint | CUDA GPU + `optimum`/`auto-gptq`, a `gptq_ids` entry |

**CUDA-only:** every method except FP16 needs an NVIDIA GPU. On CPU those
variants are skipped automatically with a logged reason rather than crashing —
so `fp16` still works locally, and the full matrix runs in Colab.

For HumanEval (executes model-generated code): `export HF_ALLOW_CODE_EVAL=1`.

## Files

| File | Role |
|------|------|
| `config.yaml` / `config.py` | YAML-driven configuration (single source of truth) |
| `quantization.py` | quantization engine + method registry (+ load-time timing) |
| `benchmark_llm.py` | speed / memory / quality measurement |
| `pipeline.py` | orchestrator over models × quantizations |
| `reports.py` | CSV / Markdown / self-contained HTML + radar & efficiency |
| `visualize_benchmarks.py` | bar-chart helpers (reused by reports) |
| `app.py` | Gradio frontend |
