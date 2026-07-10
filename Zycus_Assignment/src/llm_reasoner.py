"""LLM narrative layer: turns pre-computed deterministic scores into plain-English reasoning.

The model's job is narrative and risk articulation only -- it never re-computes the RAG
status. It may flag disagreement with the deterministic status, but must justify it in
`reasoning`, and the deterministic status is never silently overridden by the LLM.

Every call is wrapped so a Groq outage degrades to deterministic-only output rather than
crashing the pipeline (see get_rag_reasoning's return contract).
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

# This machine's conda env sets SSL_CERT_FILE to a path that doesn't exist, which makes
# httpx crash on client construction (before get_rag_reasoning's try/except can catch it).
# Repoint it at certifi's bundle, which is always present since httpx depends on it.
_cert_file = os.environ.get("SSL_CERT_FILE")
if not _cert_file or not os.path.isfile(_cert_file):
    import certifi

    os.environ["SSL_CERT_FILE"] = certifi.where()

MODEL_NAME = "llama-3.3-70b-versatile"


class RAGReasoning(BaseModel):
    rag_status: str
    confidence: float
    reasoning: list[str]
    key_risks: list[str]
    recommended_actions: list[str]
    data_gaps: list[str]


def _get_api_key() -> Optional[str]:
    return os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY_2") or os.environ.get("GROQ_API_KEY")


def _build_prompt(
    project_name: str,
    sub_scores: dict[str, float],
    deterministic_status: str,
    overrides_triggered: list[str],
    data_gaps: list[str],
    comments_sample: list[str],
) -> str:
    overrides_text = (
        "\n".join(f"- {o}" for o in overrides_triggered)
        if overrides_triggered
        else "None triggered."
    )
    gaps_text = "\n".join(f"- {g}" for g in data_gaps) if data_gaps else "None noted."
    comments_text = (
        "\n".join(f"- {c}" for c in comments_sample) if comments_sample else "(no stakeholder comments available)"
    )

    return f"""You are a project health analyst. A project's health has been scored using
a deterministic formula based on four signals:
- Schedule slippage (score {sub_scores['schedule']}/100, weight 35%)
- Milestone health (score {sub_scores['milestone']}/100, weight 30%)
- Blockers (score {sub_scores['blockers']}/100, weight 20%)
- Stakeholder sentiment (score {sub_scores['sentiment']}/100, weight 15%)

Project: {project_name}
Deterministic RAG status: {deterministic_status}

Hard override rules that fired (these force Red and win over the weighted composite):
{overrides_text}

Known data gaps from the pipeline (things it could NOT compute from source data):
{gaps_text}

Recent stakeholder comments:
{comments_text}

Respond ONLY as valid JSON (no preamble, no markdown, pure JSON):
{{
  "rag_status": "Green/Amber/Red",
  "confidence": 0.0-1.0,
  "reasoning": ["bullet 1", "bullet 2", "..."],
  "key_risks": ["risk 1", "risk 2", ...],
  "recommended_actions": ["action 1", "action 2", ...],
  "data_gaps": ["gap 1", "gap 2", ...]
}}

Be concise (3-5 bullets per list). Your "rag_status" should normally match the deterministic
status above -- you are narrating and articulating risk, not re-scoring. If you believe the
deterministic status is wrong, say so explicitly in "reasoning" and justify why, but do not
silently pick a different status without explanation. If confidence is low because of missing
data, say so in "data_gaps" rather than guessing."""


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def get_rag_reasoning(
    project_name: str,
    sub_scores: dict[str, float],
    deterministic_status: str,
    overrides_triggered: list[str],
    data_gaps: list[str],
    comments_sample: list[str],
) -> tuple[Optional[RAGReasoning], Optional[str]]:
    """Returns (reasoning, error). Exactly one of the two is non-None on return."""
    api_key = _get_api_key()
    if not api_key:
        return None, "No GROQ_API_KEY_1/GROQ_API_KEY_2 found in environment."

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        prompt = _build_prompt(
            project_name, sub_scores, deterministic_status, overrides_triggered, data_gaps, comments_sample
        )
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
        )
        raw_text = response.choices[0].message.content
        parsed: dict[str, Any] = json.loads(_strip_markdown_fence(raw_text))
        return RAGReasoning(**parsed), None
    except Exception as exc:  # noqa: BLE001 - any failure here must degrade gracefully
        return None, f"{type(exc).__name__}: {exc}"
