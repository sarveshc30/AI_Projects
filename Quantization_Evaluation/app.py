#!/usr/bin/env python3
"""
app.py — Gradio frontend for the quantization benchmark pipeline.

Enter a model name, pick which quantizations and benchmark tasks to run, hit
"Run benchmark", and the HTML report (efficiency ranking, radar + bar charts,
comparison tables) renders inline. CSV / Markdown / raw-JSON downloads are
offered alongside.

Defaults are seeded from config.yaml, so the whole thing stays config-driven.

Launch (Colab or local):
    python app.py
In Colab this prints a public share URL (share=True).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import gradio as gr

import reports
from config import Config, GenerationConfig, load_config
from quantization import METHODS
from pipeline import run_pipeline

DEFAULTS = load_config("config.yaml")

ALL_METHODS = list(METHODS.keys())          # fp16, int8, nf4, awq, gptq
ALL_TASKS = ["mmlu", "gsm8k", "hellaswag", "truthfulqa_mc2", "humaneval"]


def _write_temp(text: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


def run(model_name, methods, awq_id, gptq_id, tasks, smartness_limit,
        max_new_tokens, progress=gr.Progress()):
    """Build a per-run config from the UI, run the pipeline, return report +
    downloadable files."""
    if not model_name or not model_name.strip():
        return "<p style='color:#b00'>Please enter a model name.</p>", None, None, None
    if not methods:
        return "<p style='color:#b00'>Select at least one quantization method.</p>", None, None, None
    if not tasks:
        return "<p style='color:#b00'>Select at least one benchmark task.</p>", None, None, None

    model_name = model_name.strip()
    cfg = Config(
        models=[model_name],
        quantizations=list(methods),
        benchmarks=list(tasks),
        generation=GenerationConfig(
            max_new_tokens=int(max_new_tokens),
            smartness_limit=int(smartness_limit) if smartness_limit else None,
        ),
        prompts=DEFAULTS.prompts,
        awq_ids={model_name: awq_id.strip()} if awq_id and awq_id.strip() else {},
        gptq_ids={model_name: gptq_id.strip()} if gptq_id and gptq_id.strip() else {},
        output_dir=DEFAULTS.output_dir,
    ).validate()

    def cb(frac, msg):
        progress(min(max(frac, 0.0), 1.0), desc=msg)

    runs = run_pipeline(cfg, progress_cb=cb)

    if not runs:
        return ("<p style='color:#b00'>No variants completed — check the logs. "
                "On a CPU-only machine, GPU-only methods (int8/nf4/awq/gptq) are "
                "skipped.</p>", None, None, None)

    html = reports.to_html(runs)
    csv_path = _write_temp(reports.to_csv(runs), ".csv")
    md_path = _write_temp(reports.to_markdown(runs), ".md")
    json_path = _write_temp(json.dumps(runs, indent=2), ".json")
    return html, csv_path, md_path, json_path


def build_ui():
    with gr.Blocks(title="LLM Quantization Benchmark") as demo:
        gr.Markdown(
            "# 🧪 Automated LLM Quantization Benchmark\n"
            "Enter a model, choose quantizations and benchmark tasks, and get a "
            "speed / memory / quality report with an overall efficiency score."
        )
        with gr.Row():
            with gr.Column(scale=1):
                model_name = gr.Textbox(
                    label="Base model (HF id or local path)",
                    value=DEFAULTS.models[0],
                )
                methods = gr.CheckboxGroup(
                    choices=ALL_METHODS, value=DEFAULTS.quantizations,
                    label="Quantizations",
                    info="int8/nf4/awq/gptq require a CUDA GPU (skipped otherwise)",
                )
                default_model = DEFAULTS.models[0]
                awq_id = gr.Textbox(
                    label="Pre-quantized AWQ repo id (optional)",
                    value=DEFAULTS.awq_id_for(default_model) or "",
                )
                gptq_id = gr.Textbox(
                    label="Pre-quantized GPTQ repo id (optional)",
                    value=DEFAULTS.gptq_id_for(default_model) or "",
                )
                tasks = gr.CheckboxGroup(
                    choices=ALL_TASKS, value=DEFAULTS.benchmarks,
                    label="Benchmark tasks (lm-eval)",
                )
                smartness_limit = gr.Slider(
                    minimum=0, maximum=500, step=10,
                    value=DEFAULTS.generation.smartness_limit or 0,
                    label="Examples per task (0 = full eval, slow)",
                )
                max_new_tokens = gr.Slider(
                    minimum=16, maximum=1024, step=16,
                    value=DEFAULTS.generation.max_new_tokens,
                    label="Max new tokens (speed test)",
                )
                run_btn = gr.Button("Run benchmark", variant="primary")
            with gr.Column(scale=2):
                report_html = gr.HTML(label="Report")
                with gr.Row():
                    csv_file = gr.File(label="CSV")
                    md_file = gr.File(label="Markdown")
                    json_file = gr.File(label="Raw JSON")

        run_btn.click(
            fn=run,
            inputs=[model_name, methods, awq_id, gptq_id, tasks,
                    smartness_limit, max_new_tokens],
            outputs=[report_html, csv_file, md_file, json_file],
        )
    return demo


if __name__ == "__main__":
    build_ui().launch(share=True)
