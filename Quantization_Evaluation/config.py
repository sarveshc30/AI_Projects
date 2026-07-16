#!/usr/bin/env python3
"""
config.py

Loads and validates the YAML configuration that drives the whole pipeline.
This is the single source of truth for which models, quantizations, benchmark
tasks and generation settings are used — nothing benchmark-related is hardcoded
in Python.

Usage:
    from config import load_config
    cfg = load_config("config.yaml")
    cfg.models          # -> ["TinyLlama/..."]
    cfg.quantizations   # -> ["fp16", "int8", ...]
    cfg.benchmarks      # -> ["hellaswag", ...]
    cfg.generation.max_new_tokens
    cfg.awq_id_for(model)   # -> pre-quantized AWQ repo id, or None
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List, Optional

import yaml

VALID_QUANTIZATIONS = ["fp32", "fp16", "int8", "nf4", "awq", "gptq"]

# Defaults applied when a key is missing from the YAML file.
DEFAULT_MODELS = ["TinyLlama/TinyLlama-1.1B-Chat-v1.0"]
DEFAULT_QUANTIZATIONS = ["fp16", "int8", "nf4"]
DEFAULT_BENCHMARKS = ["hellaswag", "truthfulqa_mc2"]
DEFAULT_MAX_NEW_TOKENS = 256
DEFAULT_SMARTNESS_LIMIT = 50
DEFAULT_OUTPUT_DIR = "./benchmark_results"


@dataclass
class GenerationConfig:
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS
    smartness_limit: Optional[int] = DEFAULT_SMARTNESS_LIMIT


@dataclass
class Config:
    models: List[str] = field(default_factory=lambda: list(DEFAULT_MODELS))
    quantizations: List[str] = field(default_factory=lambda: list(DEFAULT_QUANTIZATIONS))
    benchmarks: List[str] = field(default_factory=lambda: list(DEFAULT_BENCHMARKS))
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    prompts: Optional[List[str]] = None
    awq_ids: Dict[str, str] = field(default_factory=dict)
    gptq_ids: Dict[str, str] = field(default_factory=dict)
    output_dir: str = DEFAULT_OUTPUT_DIR

    # -- helpers ------------------------------------------------------------
    def awq_id_for(self, model: str) -> Optional[str]:
        return self.awq_ids.get(model)

    def gptq_id_for(self, model: str) -> Optional[str]:
        return self.gptq_ids.get(model)

    def validate(self) -> "Config":
        if not self.models:
            raise ValueError("config: 'models' must list at least one model.")
        if not self.quantizations:
            raise ValueError("config: 'quantizations' must list at least one method.")
        bad = [q for q in self.quantizations if q not in VALID_QUANTIZATIONS]
        if bad:
            raise ValueError(
                f"config: unknown quantization(s) {bad}. "
                f"Valid options: {VALID_QUANTIZATIONS}"
            )
        if not self.benchmarks:
            raise ValueError("config: 'benchmarks' must list at least one lm-eval task.")
        if self.generation.max_new_tokens <= 0:
            raise ValueError("config: generation.max_new_tokens must be > 0.")
        return self

    def with_overrides(self, **kwargs) -> "Config":
        """Return a copy with top-level fields overridden (used by the UI to
        build a per-run config without mutating the loaded defaults)."""
        gen = kwargs.pop("generation", None)
        new = replace(self, **kwargs)
        if gen is not None:
            new.generation = gen
        return new.validate()


def load_config(path: str = "config.yaml") -> Config:
    """Load a Config from a YAML file, applying defaults for missing keys."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return config_from_dict(raw)


def config_from_dict(raw: dict) -> Config:
    """Build a validated Config from a plain dict (YAML- or UI-sourced)."""
    gen_raw = raw.get("generation") or {}
    generation = GenerationConfig(
        max_new_tokens=gen_raw.get("max_new_tokens", DEFAULT_MAX_NEW_TOKENS),
        smartness_limit=gen_raw.get("smartness_limit", DEFAULT_SMARTNESS_LIMIT),
    )
    cfg = Config(
        models=raw.get("models") or list(DEFAULT_MODELS),
        quantizations=raw.get("quantizations") or list(DEFAULT_QUANTIZATIONS),
        benchmarks=raw.get("benchmarks") or list(DEFAULT_BENCHMARKS),
        generation=generation,
        prompts=raw.get("prompts") or None,
        awq_ids=raw.get("awq_ids") or {},
        gptq_ids=raw.get("gptq_ids") or {},
        output_dir=raw.get("output_dir") or DEFAULT_OUTPUT_DIR,
    )
    return cfg.validate()


if __name__ == "__main__":
    # Quick self-check: parse the default config file and print a summary.
    import json

    cfg = load_config("config.yaml")
    print("Parsed config:")
    print(json.dumps({
        "models": cfg.models,
        "quantizations": cfg.quantizations,
        "benchmarks": cfg.benchmarks,
        "generation": {
            "max_new_tokens": cfg.generation.max_new_tokens,
            "smartness_limit": cfg.generation.smartness_limit,
        },
        "awq_ids": cfg.awq_ids,
        "gptq_ids": cfg.gptq_ids,
        "output_dir": cfg.output_dir,
    }, indent=2))
