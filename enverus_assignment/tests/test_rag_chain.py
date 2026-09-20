"""
tests/test_rag_chain.py
───────────────────────
Unit tests for src/rag_chain.py.

The Groq LLM and the retriever are both mocked so these run offline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.rag_chain import AnswerResult, answer_question
from src.retriever import RetrievedChunk


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_chunk(i: int = 0) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"{i}-0",
        page=str(i),
        text=f"Relevant context passage {i}.",
        distance=float(i) * 0.1,
    )


def _mock_groq_response(text: str):
    """Build a minimal mock that mimics groq.chat.completions.create response."""
    choice = MagicMock()
    choice.message.content = text
    response = MagicMock()
    response.choices = [choice]
    return response


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_answer_question_returns_answer_result():
    """answer_question() must return an AnswerResult instance."""
    chunks = [_make_chunk(i) for i in range(3)]

    with patch("src.rag_chain.retrieve", return_value=chunks), \
         patch("src.rag_chain.get_groq_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            "According to page 0, the answer is X."
        )
        mock_client_factory.return_value = mock_client

        result = answer_question("What is X?", k=3)

    assert isinstance(result, AnswerResult)


def test_answer_has_non_empty_answer():
    """The answer field should not be empty when chunks are available."""
    chunks = [_make_chunk()]

    with patch("src.rag_chain.retrieve", return_value=chunks), \
         patch("src.rag_chain.get_groq_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            "The answer is Y."
        )
        mock_client_factory.return_value = mock_client

        result = answer_question("What is Y?")

    assert result.answer.strip() != ""


def test_sources_populated_when_chunks_exist():
    """result.sources should contain the retrieved chunks."""
    chunks = [_make_chunk(i) for i in range(4)]

    with patch("src.rag_chain.retrieve", return_value=chunks), \
         patch("src.rag_chain.get_groq_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response("Answer.")
        mock_client_factory.return_value = mock_client

        result = answer_question("Any question?", k=4)

    assert len(result.sources) == 4


def test_empty_retrieval_returns_decline_message():
    """When no chunks are retrieved, the answer must be the decline message."""
    with patch("src.rag_chain.retrieve", return_value=[]):
        result = answer_question("Unknown question?")

    assert "could not find" in result.answer.lower()
    assert result.sources == []


def test_question_preserved_in_result():
    """result.question must match the input query exactly."""
    query = "What is the DevAI dataset?"
    chunks = [_make_chunk()]

    with patch("src.rag_chain.retrieve", return_value=chunks), \
         patch("src.rag_chain.get_groq_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response("Some answer.")
        mock_client_factory.return_value = mock_client

        result = answer_question(query)

    assert result.question == query
