"""
src/logging_utils.py
────────────────────
Appends each Q&A exchange (question + answer + retrieved chunks) to
``answers/qa_chunks.md`` in a structured, human-readable Markdown format
suitable for direct use in the assignment submission form.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.config import ANSWERS_DIR
from src.rag_chain import AnswerResult

QA_LOG_PATH: Path = ANSWERS_DIR / "qa_chunks.md"


def _ensure_log_file() -> None:
    """Create the answers directory and file header if they don't exist."""
    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    if not QA_LOG_PATH.exists():
        QA_LOG_PATH.write_text(
            "# Q&A Log — Agent-as-a-Judge RAG Chatbot\n\n"
            "_Auto-generated. Each section contains the question, "
            "the generated answer, and the raw retrieved chunks._\n\n"
            "---\n\n",
            encoding="utf-8",
        )


def log_qa(result: AnswerResult) -> None:
    """Append *result* as a new Markdown section to ``qa_chunks.md``.

    Args:
        result: The :class:`~src.rag_chain.AnswerResult` to log.
    """
    _ensure_log_file()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        f"## Q: {result.question}\n",
        f"_Asked at {timestamp}_\n\n",
        "### Answer\n\n",
        f"{result.answer}\n\n",
        "### Retrieved Chunks\n\n",
    ]

    for i, chunk in enumerate(result.sources, start=1):
        lines.append(
            f"**[Chunk {i}/{len(result.sources)}]** "
            f"Page {chunk.page} | ID: `{chunk.chunk_id}` | "
            f"Distance: {chunk.distance:.4f}\n\n"
            f"```\n{chunk.text.strip()}\n```\n\n"
        )

    lines.append("---\n\n")

    with QA_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.writelines(lines)
