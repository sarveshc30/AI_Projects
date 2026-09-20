"""
src/config.py
─────────────
Central configuration module.

Loads environment variables (via python-dotenv) and exposes:
  - Path / collection settings for ChromaDB
  - Chunking parameters
  - Groq LLM client factory
  - Local sentence-transformers embedding factory

Fails fast with a readable error if GROQ_API_KEY is not set.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env from the project root (parent of this file's directory) ──────────
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env", override=False)

# ── ChromaDB ───────────────────────────────────────────────────────────────────
CHROMA_PATH: str = os.getenv("CHROMA_PATH", str(_project_root / "chroma_db"))
COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "devai_paper")

# ── Chunking ───────────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "120"))

# ── Retrieval ──────────────────────────────────────────────────────────────────
TOP_K: int = int(os.getenv("TOP_K", "4"))

# ── Groq ───────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
# Default to llama-3.3-70b-versatile — widely available on free-tier Groq keys.
# Change via GROQ_MODEL in your .env if you have access to a stronger model.
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Embedding model ────────────────────────────────────────────────────────────
EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR: Path = _project_root / "data"
ANSWERS_DIR: Path = _project_root / "answers"
DEFAULT_PDF: Path = DATA_DIR / "source.pdf"


# ── Factories ──────────────────────────────────────────────────────────────────

def get_embedding_function():
    """Return a local SentenceTransformer embedding model instance.

    Downloads the model on first call; cached on disk afterwards.
    """
    from sentence_transformers import SentenceTransformer  # type: ignore

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def get_groq_client():
    """Return an authenticated Groq client.

    Raises SystemExit with a helpful message if GROQ_API_KEY is missing.
    """
    if not GROQ_API_KEY:
        print(
            "\n[ERROR] GROQ_API_KEY is not set.\n"
            "  1. Copy .env.example → .env\n"
            "  2. Paste your Groq API key from https://console.groq.com\n"
            "  3. Re-run the script.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    from groq import Groq  # type: ignore

    return Groq(api_key=GROQ_API_KEY)
