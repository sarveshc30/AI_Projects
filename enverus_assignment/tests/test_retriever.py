"""
tests/test_retriever.py
───────────────────────
Unit tests for src/retriever.py.

All ChromaDB interactions are mocked so these tests run offline with no
persistent store.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.retriever import RetrievedChunk, retrieve


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_chroma_result(n: int) -> dict:
    """Build a fake ChromaDB query result with *n* entries."""
    return {
        "documents": [[f"Text of chunk {i}" for i in range(n)]],
        "metadatas": [
            [{"chunk_id": f"{i}-0", "page": str(i), "source": "test.pdf"}
             for i in range(n)]
        ],
        "distances": [[float(i) * 0.1 for i in range(n)]],
    }


# ── Tests ──────────────────────────────────────────────────────────────────────

def _patched_retrieve(n_results: int, k: int) -> list[RetrievedChunk]:
    """Helper: patch internals and call retrieve() returning *n_results* chunks."""
    import src.retriever as ret_module

    mock_collection = MagicMock()
    mock_collection.query.return_value = _make_chroma_result(n_results)
    mock_collection.count.return_value = n_results

    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((1, 384))

    ret_module._collection = mock_collection
    ret_module._embed_model = mock_model

    try:
        return retrieve("test query", k=k)
    finally:
        ret_module._collection = None
        ret_module._embed_model = None
        ret_module._client = None


def test_retrieve_returns_k_results():
    """retrieve() should return exactly k chunks."""
    chunks = _patched_retrieve(n_results=4, k=4)
    assert len(chunks) == 4


def test_retrieve_returns_fewer_when_collection_small():
    """If the collection has fewer docs than k, all available docs are returned."""
    chunks = _patched_retrieve(n_results=2, k=4)
    assert len(chunks) == 2


def test_retrieve_chunk_fields_populated():
    """Every RetrievedChunk must have non-empty chunk_id, page, and text."""
    chunks = _patched_retrieve(n_results=3, k=3)
    for chunk in chunks:
        assert chunk.chunk_id, "chunk_id should not be empty"
        assert chunk.page is not None, "page should not be None"
        assert chunk.text, "text should not be empty"


def test_retrieve_sorted_by_distance():
    """Chunks should be ordered ascending by distance (most relevant first)."""
    chunks = _patched_retrieve(n_results=4, k=4)
    distances = [c.distance for c in chunks]
    assert distances == sorted(distances), "Chunks are not sorted by distance"


def test_retrieve_returns_retrieved_chunk_instances():
    """retrieve() should return RetrievedChunk dataclass instances."""
    chunks = _patched_retrieve(n_results=2, k=2)
    for chunk in chunks:
        assert isinstance(chunk, RetrievedChunk)
