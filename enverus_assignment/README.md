# PDF RAG Chatbot — Agent-as-a-Judge

A **Retrieval-Augmented Generation (RAG)** chatbot that answers questions about
the paper _"Agent-as-a-Judge: Evaluate Agents with Agents"_ (arXiv:2410.10934).

**Stack:** ChromaDB · LangChain · sentence-transformers (MiniLM-L6-v2) · Groq LLM · Typer CLI

---

## RAG Pipeline

```
PDF → PyPDFLoader → Chunker (800/120) → MiniLM embeds → ChromaDB
                                                              ↑
User query → MiniLM embed ──────────────────────────── top-k chunks
                                                              ↓
                                          Prompt builder → Groq LLM → Answer
                                                              ↓
                                                    answers/qa_chunks.md
```

See [`docs/rag_workflow.md`](docs/rag_workflow.md) for the full Mermaid diagram
and stage-by-stage explanation.

---

## Quick Start

### 1. Clone & enter the project

```bash
git clone <your-repo-url>
cd pdf-rag-chatbot
```

### 2. Activate the conda environment

```bash
conda activate LangGraph
```

### 3. Configure your Groq API key

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY=<your-key>
# Get a free key at https://console.groq.com
```

### 4. Add the PDF

Place the paper PDF at `data/source.pdf`  
(Already committed as part of this repo.)

### 5. Run the chatbot

```bash
# Interactive REPL (auto-ingests PDF on first run)
python src/cli.py

# Or:
python -m src
```

The first run will embed the PDF into ChromaDB (~30 seconds). Subsequent runs
load instantly from the persistent store.

---

## Commands

### Interactive chat (default)

```bash
python src/cli.py chat
python src/cli.py             # same — 'chat' is the default
```

Override k per-question inline:
```
> What is DevAI? --k 6
```

### Batch mode — all 15 assignment questions

```bash
python src/cli.py batch
```

Results are printed to stdout AND logged to `answers/qa_chunks.md`.

### Force re-ingest

```bash
python src/cli.py chat --reset
python src/cli.py batch --reset
```

### Ingest only (no chat)

```bash
python -m src.ingest
python -m src.ingest --reset   # drop & rebuild
```

---

## Project Structure

```
pdf-rag-chatbot/
├── data/source.pdf            # Assignment paper (input)
├── chroma_db/                 # ChromaDB persistent store (gitignored)
├── src/
│   ├── config.py              # Env vars, paths, model factories
│   ├── ingest.py              # PDF → chunks → ChromaDB
│   ├── retriever.py           # ChromaDB query wrapper
│   ├── rag_chain.py           # Prompt + Groq LLM call
│   ├── logging_utils.py       # Auto-log Q&A to answers/qa_chunks.md
│   ├── cli.py                 # Typer CLI (chat + batch commands)
│   └── __main__.py            # python -m src entry point
├── docs/
│   ├── rag_workflow.md        # Mermaid pipeline diagram (assignment deliverable)
│   └── rag_workflow.png       # Rendered PNG for offline viewing
├── answers/
│   └── qa_chunks.md           # Auto-generated Q&A + chunk log
├── tests/
│   ├── test_ingest.py
│   ├── test_retriever.py
│   └── test_rag_chain.py
├── .env.example
├── requirements.txt
└── pyproject.toml
```

---

## Configuration

All settings can be overridden via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | _(required)_ | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model ID |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `CHROMA_PATH` | `chroma_db/` | ChromaDB storage path |
| `COLLECTION_NAME` | `devai_paper` | ChromaDB collection name |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `120` | Overlap between chunks |
| `TOP_K` | `4` | Default number of retrieved chunks |

> **Tip:** For table-heavy questions (Q6, Q8–Q14, Q17), use `--k 6` to ensure
> the relevant table rows end up in context.

---

## Running Tests

```bash
conda activate LangGraph
cd pdf-rag-chatbot
python -m pytest tests/ -v
```

All tests run offline with mocked ChromaDB and Groq — no API key required.

---

## Deliverables

| Deliverable | Location |
|---|---|
| Working RAG chatbot | `python src/cli.py` |
| RAG workflow visualization | [`docs/rag_workflow.md`](docs/rag_workflow.md) / [`docs/rag_workflow.png`](docs/rag_workflow.png) |
| Q&A log with retrieved chunks | [`answers/qa_chunks.md`](answers/qa_chunks.md) |
| Public GitHub repo | _(push and share)_ |
