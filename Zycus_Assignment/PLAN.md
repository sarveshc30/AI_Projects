# Project Plan — Project Health Reporting Agent

## Deliverables checklist

- [x] `docs/RAG_Methodology.md` — one-page methodology
- [x] Working agent, all 8 core stages, runnable via a single documented command
      (`python src/run_weekly.py --all`)
- [x] Sample weekly output generated for both `S2P_Project.xlsx` and `Project_Plan_B.xlsx`
      (`outputs/weekly/S2P_Project/2026-07-02.md`, `outputs/weekly/Project_Plan_B/2026-07-02.md`)
- [x] Weekly scheduler stub + doc (`config/schedule.yaml`, `docs/schedule.md`)
- [x] Final `.pptx` deck, 6 slides (`outputs/deck/Monthly_Executive_Deck.pptx`)
- [x] `README.md` — architecture, how to run it, design decisions, limitations, what's next
- [x] `DECISIONS.md` — running log of assumptions/choices made autonomously during the build
- [x] `Study.md` — detailed explainer for answering questions about this build

## Build order (all stages complete)

- [x] 1. Ingestion & normalization (`src/ingestion.py`, `config/column_mapping.yaml`)
- [x] 2. Cleaning (`src/cleaning.py`)
- [x] 3. Metrics engineering (`src/metrics.py`, `src/sentiment.py` for VADER)
- [x] 4. Deterministic RAG engine (`src/rag_engine.py`)
- [x] 5. LLM reasoning layer (`src/llm_reasoner.py`, Groq Llama 3.3 70B, Pydantic schema)
- [x] 6. Report generation (`src/report_generator.py`, `templates/weekly_report.md.j2`)
- [x] 7. Weekly scheduler stub (`src/run_weekly.py`, `config/schedule.yaml`, `docs/schedule.md`)
- [x] 8. Monthly synthesis & deck (`src/ppt_generator.py`)

## Quality bar checks

- [x] Every module has at least one test under `tests/` (35 tests total, all passing)
- [x] Ingestion tests specifically assert both sample files normalize to the same
      canonical schema shape despite differing columns
- [x] Agent runs end-to-end on both sample files without crashing
      (`python src/run_weekly.py --all`)
- [x] Outputs are visibly different and data-grounded per project (different scores,
      different overrides, different narrative, different data gaps — see the two
      generated weekly reports)
- [x] Every place the pipeline can't compute a signal states so explicitly in the output
      (see "Data Gaps & Assumptions" section of each weekly report)
- [x] No hardcoded column indices or per-file `if/else` branches — all column resolution
      goes through `config/column_mapping.yaml`

## What's left / known gaps

- Groq API calls are billed against the provided free-tier keys; no cost-tracking wrapper
  was added since usage here is minimal (one call per project per run).
- No live scheduler is actually running (per the brief's own guidance not to
  over-engineer standing infra for a demo) — `docs/schedule.md` documents both a cron
  line and a GitHub Actions workflow.
- See `README.md` "Known Limitations" and "What I'd do differently" for the rest.
