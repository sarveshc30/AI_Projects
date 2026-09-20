"""
src/rag_chain.py
────────────────
RAG chain: build a prompt from retrieved chunks, call the Groq LLM,
and return a structured AnswerResult with the generated answer + source chunks.

Design decisions:
  - The system prompt strictly instructs the model to answer ONLY from the
    provided context, and to explicitly say so if the answer is not present.
  - A simple retry/backoff wrapper handles Groq 429 rate-limit responses so
    rapid batch runs (e.g. all 15 questions) don't crash.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.config import GROQ_MODEL, get_groq_client
from src.retriever import RetrievedChunk, retrieve, TOP_K

# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a precise research assistant. Your ONLY source of information is the
context passages provided below. Do not use any prior knowledge.

Rules:
1. Answer ONLY based on the context passages.
2. If the answer is not found in the context, say:
   "I could not find this information in the provided paper."
3. Be concise but thorough. Quote specific numbers, percentages, or table
   values whenever the question asks for them.
4. Cite which chunk(s) you drew from by mentioning the page number(s) when
   relevant (e.g., "According to page 5, ...").
"""

_USER_TEMPLATE = """\
Context passages (from the paper):
{context}

---
Question: {question}

Answer:"""


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class AnswerResult:
    """Container for a generated answer and its supporting chunks."""
    question: str
    answer: str
    sources: list[RetrievedChunk] = field(default_factory=list)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks as numbered context passages."""
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[Passage {i} | Page {chunk.page} | ID: {chunk.chunk_id}]\n"
            f"{chunk.text}"
        )
    return "\n\n".join(parts)


def _call_groq(messages: list[dict], max_retries: int = 4) -> str:
    """Call the Groq chat completions API with simple exponential backoff."""
    client = get_groq_client()
    wait = 5  # seconds
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            err = str(exc)
            # Retry on rate-limit (429) or transient server errors (5xx)
            if "429" in err or "rate_limit" in err.lower() or "5" in err[:3]:
                if attempt < max_retries - 1:
                    print(f"  [Groq] Rate-limited or transient error. "
                          f"Retrying in {wait}s… (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    wait *= 2
                else:
                    raise
            else:
                raise
    return ""  # unreachable


# ── Public API ─────────────────────────────────────────────────────────────────

def answer_question(query: str, k: int = TOP_K) -> AnswerResult:
    """Full RAG pipeline for a single question.

    Args:
        query: The user's question.
        k:     Number of chunks to retrieve.

    Returns:
        :class:`AnswerResult` with the generated answer and source chunks.
    """
    chunks = retrieve(query, k=k)

    if not chunks:
        return AnswerResult(
            question=query,
            answer="I could not find this information in the provided paper.",
            sources=[],
        )

    context = _build_context(chunks)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _USER_TEMPLATE.format(
            context=context, question=query
        )},
    ]

    answer = _call_groq(messages)

    return AnswerResult(question=query, answer=answer, sources=chunks)
