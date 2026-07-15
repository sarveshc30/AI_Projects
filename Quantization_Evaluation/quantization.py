#!/usr/bin/env python3
"""
quantization.py — the Quantization Engine.

Given a base model and a method name, produce a loaded (model, tokenizer)
pair plus metadata. Supported methods:

  fp16  - half-precision baseline               (any CUDA GPU)
  int8  - bitsandbytes 8-bit                     (CUDA + bitsandbytes)
  nf4   - bitsandbytes 4-bit NF4 + double-quant  (CUDA + bitsandbytes)
  awq   - load a pre-quantized AWQ hub checkpoint (CUDA + autoawq kernels)
  gptq  - load a pre-quantized GPTQ hub checkpoint (CUDA + optimum/auto-gptq)

The recipes mirror the user's notebooks (Biteandbytes.ipynb for fp16/int8,
Quantization_Testing.ipynb for AWQ). AWQ/GPTQ load a pre-quantized repo from
the hub rather than quantizing live, to avoid the calibration pass.

Each loader is timed, so `meta["load_time_sec"]` records how long it took to
load/quantize the variant — a first-class benchmark metric.

Every method exposes `available()` so the pipeline can skip a variant with a
clear reason (e.g. no GPU, missing bitsandbytes) instead of crashing.
"""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import torch


# --------------------------------------------------------------------------- #
# Availability helpers
# --------------------------------------------------------------------------- #

def _has_cuda() -> bool:
    return torch.cuda.is_available()


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _hf_snapshot_size_gb(model_id: str) -> Optional[float]:
    """Best-effort on-disk size (GB) of a model already cached by huggingface.
    Returns None if the snapshot can't be resolved (e.g. not downloaded yet)."""
    try:
        from huggingface_hub import try_to_load_from_cache
        from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE
    except Exception:
        return None

    # If it's a local directory, just measure it directly.
    p = Path(model_id)
    if p.exists() and p.is_dir():
        total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        return round(total / (1024 ** 3), 3) if total else None

    # Otherwise walk the HF cache snapshot dir for this repo, if present.
    try:
        cache_root = Path(HUGGINGFACE_HUB_CACHE)
        repo_dir = cache_root / ("models--" + model_id.replace("/", "--"))
        snap = repo_dir / "snapshots"
        if not snap.exists():
            return None
        total = sum(f.stat().st_size for f in snap.rglob("*") if f.is_file())
        return round(total / (1024 ** 3), 3) if total else None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Method descriptor
# --------------------------------------------------------------------------- #

@dataclass
class QuantMethod:
    name: str
    description: str
    loader: Callable  # (base_model, source_id) -> (model, tokenizer)
    requires: list = field(default_factory=list)   # extra python modules
    needs_cuda: bool = True
    needs_prequant_id: bool = False                 # awq/gptq load a hub repo

    def available(self, source_id: Optional[str] = None) -> Tuple[bool, str]:
        if self.needs_cuda and not _has_cuda():
            return False, f"{self.name}: requires a CUDA GPU (none detected)"
        for mod in self.requires:
            if not _has_module(mod):
                return False, f"{self.name}: requires the '{mod}' package (not installed)"
        if self.needs_prequant_id and not source_id:
            return False, (f"{self.name}: needs a pre-quantized hub id "
                           f"(set awq_ids/gptq_ids in config.yaml)")
        return True, ""


# --------------------------------------------------------------------------- #
# Loaders (each returns (model, tokenizer))
# --------------------------------------------------------------------------- #

def _load_tokenizer(model_id: str):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model_id)


def _load_fp16(base_model: str, source_id: Optional[str]):
    from transformers import AutoModelForCausalLM
    tokenizer = _load_tokenizer(base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    model.eval()
    return model, tokenizer


def _load_int8(base_model: str, source_id: Optional[str]):
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(load_in_8bit=True)
    tokenizer = _load_tokenizer(base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model.eval()
    return model, tokenizer


def _load_nf4(base_model: str, source_id: Optional[str]):
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = _load_tokenizer(base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model.eval()
    return model, tokenizer


def _load_prequant(base_model: str, source_id: Optional[str]):
    """Load a pre-quantized AWQ/GPTQ checkpoint from the hub. transformers
    auto-detects the quantization_config baked into the repo."""
    from transformers import AutoModelForCausalLM
    repo = source_id or base_model
    tokenizer = _load_tokenizer(repo)
    model = AutoModelForCausalLM.from_pretrained(
        repo,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    model.eval()
    return model, tokenizer


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

METHODS: Dict[str, QuantMethod] = {
    "fp16": QuantMethod(
        name="fp16",
        description="Half-precision (FP16) baseline",
        loader=_load_fp16,
        needs_cuda=True,
    ),
    "int8": QuantMethod(
        name="int8",
        description="bitsandbytes 8-bit",
        loader=_load_int8,
        requires=["bitsandbytes"],
        needs_cuda=True,
    ),
    "nf4": QuantMethod(
        name="nf4",
        description="bitsandbytes 4-bit NF4 (double quant)",
        loader=_load_nf4,
        requires=["bitsandbytes"],
        needs_cuda=True,
    ),
    "awq": QuantMethod(
        name="awq",
        description="Pre-quantized AWQ 4-bit checkpoint",
        loader=_load_prequant,
        requires=["awq"],
        needs_cuda=True,
        needs_prequant_id=True,
    ),
    "gptq": QuantMethod(
        name="gptq",
        description="Pre-quantized GPTQ 4-bit checkpoint",
        loader=_load_prequant,
        requires=["optimum"],
        needs_cuda=True,
        needs_prequant_id=True,
    ),
}


def load_quantized(base_model: str, method: str, source_id: Optional[str] = None):
    """
    Load `base_model` under the given quantization `method`.

    For awq/gptq, `source_id` is the pre-quantized hub repo id.

    Returns:
        (model, tokenizer, meta) where meta contains:
            method, source_id, load_time_sec, on_disk_size_gb
    """
    if method not in METHODS:
        raise ValueError(f"Unknown quantization method '{method}'. "
                         f"Valid: {list(METHODS)}")
    spec = METHODS[method]

    ok, reason = spec.available(source_id)
    if not ok:
        raise RuntimeError(reason)

    effective_source = source_id if spec.needs_prequant_id else base_model

    t0 = time.perf_counter()
    model, tokenizer = spec.loader(base_model, effective_source)
    load_time = time.perf_counter() - t0

    meta = {
        "method": method,
        "source_id": effective_source,
        "load_time_sec": round(load_time, 4),
        "on_disk_size_gb": _hf_snapshot_size_gb(effective_source),
    }
    return model, tokenizer, meta


if __name__ == "__main__":
    # Availability report — safe to run on CPU (nothing is loaded).
    for name, m in METHODS.items():
        ok, reason = m.available(source_id="dummy/repo" if m.needs_prequant_id else None)
        status = "available" if ok else f"SKIP ({reason})"
        print(f"{name:6s} - {m.description:40s} -> {status}")
