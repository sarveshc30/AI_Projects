"""
src/ingest.py
─────────────
PDF ingestion pipeline:
  1. Load the PDF with LangChain's PyPDFLoader (preserves page metadata).
  2. Chunk each page with RecursiveCharacterTextSplitter.
  3. Embed every chunk locally with MiniLM-L6-v2.
  4. Upsert into a ChromaDB persistent collection (idempotent).

Usage:
    python -m src.ingest                  # ingest data/source.pdf
    python -m src.ingest --pdf other.pdf  # ingest a different file
    python -m src.ingest --reset          # drop & rebuild the collection first
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_PATH,
    COLLECTION_NAME,
    DEFAULT_PDF,
    get_embedding_function,
)


# ── Loader ─────────────────────────────────────────────────────────────────────

def load_pdf(path: str | Path) -> list:
    """Load every page of *path* as a LangChain Document.

    Each document carries ``metadata['page']`` (0-indexed) and
    ``metadata['source']``.
    """
    path = Path(path)
    if not path.exists():
        print(f"[ERROR] PDF not found: {path}", file=sys.stderr)
        sys.exit(1)

    loader = PyPDFLoader(str(path))
    docs = loader.load()
    print(f"  Loaded {len(docs)} pages from '{path.name}'.")
    return docs


# ── Chunker ────────────────────────────────────────────────────────────────────

def chunk_documents(docs: list) -> list:
    """Split *docs* into smaller chunks, attaching a stable ``chunk_id``.

    ``chunk_id`` format: ``"<page>-<index_within_page>"``  (e.g. ``"3-2"``).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )
    chunks = splitter.split_documents(docs)

    # Assign stable chunk IDs and normalise page metadata
    page_counter: dict[int, int] = {}
    for chunk in chunks:
        page = int(chunk.metadata.get("page", 0))
        idx = page_counter.get(page, 0)
        chunk.metadata["chunk_id"] = f"{page}-{idx}"
        chunk.metadata["page"] = page
        page_counter[page] = idx + 1

    print(f"  Split into {len(chunks)} chunks "
          f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}).")
    return chunks


# ── Indexer ────────────────────────────────────────────────────────────────────

def build_or_update_index(chunks: list, reset: bool = False) -> None:
    """Embed *chunks* and upsert them into the ChromaDB collection.

    If *reset* is ``True``, the existing collection is deleted first.
    Ingestion is otherwise idempotent — re-running with the same PDF is safe.
    """
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"  Deleted existing collection '{COLLECTION_NAME}'.")
        except Exception:
            pass  # collection didn't exist yet

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    model = get_embedding_function()

    # Build batch lists
    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    for chunk in chunks:
        chunk_id = chunk.metadata["chunk_id"]
        ids.append(chunk_id)
        texts.append(chunk.page_content)
        metadatas.append({
            "page": str(chunk.metadata.get("page", "")),
            "chunk_id": chunk_id,
            "source": str(chunk.metadata.get("source", "")),
        })

    # Embed in one shot (faster than per-chunk)
    print("  Embedding chunks (this may take ~30 s on first run)…")
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    # Upsert in batches of 500 to stay within ChromaDB limits
    batch_size = 500
    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
            embeddings=embeddings[start:end],
        )

    print(f"  ✓ Upserted {len(chunks)} chunks into collection '{COLLECTION_NAME}'.")


# ── Entry point ────────────────────────────────────────────────────────────────

def ingest(pdf_path: str | Path = DEFAULT_PDF, reset: bool = False) -> None:
    """Full ingestion pipeline: load → chunk → embed → store."""
    print(f"\n[Ingest] PDF: {pdf_path}")
    docs = load_pdf(pdf_path)
    chunks = chunk_documents(docs)
    build_or_update_index(chunks, reset=reset)
    print("[Ingest] Done.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a PDF into ChromaDB.")
    parser.add_argument("--pdf", default=str(DEFAULT_PDF), help="Path to the PDF file.")
    parser.add_argument("--reset", action="store_true",
                        help="Delete the existing collection before ingesting.")
    args = parser.parse_args()
    ingest(pdf_path=args.pdf, reset=args.reset)
