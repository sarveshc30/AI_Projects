"""
tests/test_ingest.py
────────────────────
Unit tests for src/ingest.py.

These tests run WITHOUT a live Groq API key or a real ChromaDB — they
use in-memory fixtures and mock the ChromaDB upsert call.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.ingest import chunk_documents, load_pdf


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_docs(texts: list[str]) -> list[Document]:
    """Create minimal LangChain Documents for testing."""
    return [
        Document(page_content=t, metadata={"page": i, "source": "test.pdf"})
        for i, t in enumerate(texts)
    ]


# ── Tests: chunk_documents ─────────────────────────────────────────────────────

def test_chunking_produces_chunks():
    """At least one chunk is produced from non-empty input."""
    docs = _make_docs(["Hello world. " * 100])
    chunks = chunk_documents(docs)
    assert len(chunks) > 0


def test_chunk_ids_are_unique():
    """Every chunk must have a unique chunk_id."""
    docs = _make_docs(["Word " * 500, "Foo " * 500])
    chunks = chunk_documents(docs)
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)), "Duplicate chunk IDs detected"


def test_chunk_metadata_fields():
    """Every chunk carries 'chunk_id' and 'page' in its metadata."""
    docs = _make_docs(["Sample text. " * 60])
    chunks = chunk_documents(docs)
    for chunk in chunks:
        assert "chunk_id" in chunk.metadata
        assert "page" in chunk.metadata


def test_chunk_size_respected():
    """No chunk should exceed CHUNK_SIZE + CHUNK_OVERLAP characters."""
    from src.config import CHUNK_OVERLAP, CHUNK_SIZE

    docs = _make_docs(["A" * 5000])
    chunks = chunk_documents(docs)
    for chunk in chunks:
        assert len(chunk.page_content) <= CHUNK_SIZE + CHUNK_OVERLAP + 50  # small buffer


def test_chunking_is_deterministic():
    """Running chunk_documents twice on the same input gives the same result."""
    docs = _make_docs(["Consistent text. " * 200])
    chunks_1 = chunk_documents(docs)
    chunks_2 = chunk_documents(docs)
    assert [c.page_content for c in chunks_1] == [c.page_content for c in chunks_2]


# ── Tests: load_pdf ────────────────────────────────────────────────────────────

def test_load_pdf_missing_file_exits(tmp_path):
    """load_pdf should call sys.exit when the file does not exist."""
    with pytest.raises(SystemExit):
        load_pdf(tmp_path / "nonexistent.pdf")


# ── Tests: build_or_update_index (mocked) ─────────────────────────────────────

def test_ingest_idempotent(tmp_path, monkeypatch):
    """Calling build_or_update_index twice should not raise and calls upsert twice."""
    from src import ingest as ingest_module

    mock_collection = MagicMock()
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_model = MagicMock()
    import numpy as np
    mock_model.encode.return_value = np.zeros((3, 384))

    monkeypatch.setattr(ingest_module, "get_embedding_function", lambda: mock_model)

    with patch("chromadb.PersistentClient", return_value=mock_client):
        docs = _make_docs(["Alpha " * 30, "Beta " * 30, "Gamma " * 30])
        chunks = chunk_documents(docs)
        ingest_module.build_or_update_index(chunks)
        ingest_module.build_or_update_index(chunks)

    # upsert called at least once per run
    assert mock_collection.upsert.call_count >= 2
