"""
src/retriever.py
────────────────
Thin wrapper around the ChromaDB collection that:
  1. Embeds the user query with the same local MiniLM model used at ingest.
  2. Queries the collection for the top-k most similar chunks.
  3. Returns a list of RetrievedChunk dataclass instances with text + metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

import chromadb

from src.config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    TOP_K,
    get_embedding_function,
)

# Module-level singletons (lazy initialised on first retrieve() call)
_client: chromadb.PersistentClient | None = None
_collection = None
_embed_model = None


def _get_collection():
    global _client, _collection, _embed_model
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        _embed_model = get_embedding_function()
    return _collection, _embed_model


@dataclass
class RetrievedChunk:
    """A single chunk returned by the retriever."""
    chunk_id: str
    page: str
    text: str
    distance: float
    source: str = ""


def retrieve(query: str, k: int = TOP_K) -> list[RetrievedChunk]:
    """Return the *k* most relevant chunks for *query*.

    Args:
        query: The user's natural-language question.
        k:     Number of chunks to retrieve (default: ``TOP_K`` from config).

    Returns:
        List of :class:`RetrievedChunk` objects sorted by ascending cosine
        distance (most relevant first).
    """
    collection, model = _get_collection()

    # Embed the query with the same model used at ingest time
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        chunks.append(
            RetrievedChunk(
                chunk_id=meta.get("chunk_id", ""),
                page=meta.get("page", ""),
                text=doc,
                distance=float(dist),
                source=meta.get("source", ""),
            )
        )

    return chunks


def collection_is_populated() -> bool:
    """Return True if the ChromaDB collection exists and has at least one entry."""
    try:
        col, _ = _get_collection()
        return col.count() > 0
    except Exception:
        return False
