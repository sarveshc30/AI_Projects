# Project Health Reporting Agent

Automated RAG (Red/Amber/Green) health reporting for project plans, built for the Zycus AI
Engineer Intern take-home. Reads a project plan workbook, scores it deterministically
against four weighted signals, gets a plain-English narrative from an LLM, and produces a
weekly per-project report plus a monthly cross-project executive deck.

## Architecture

```
data/samples/*.xlsx              Sample project plan workbooks (3 sheets each)
config/column_mapping.yaml       Canonical schema <-> per-file column name mapping
config/schedule.yaml             Documented weekly cadence (see docs/schedule.md)

src/ingestion.py     Stage 1  Reads the 3-sheet workbook via column_mapping.yaml.
                              No hardcoded column positions or per-file branching.
src/cleaning.py      Stage 2  #UNPARSEABLE/blank -> None, type coercion, task-tree build.
src/sentiment.py     Stage 3a VADER sentiment scoring of the Comments sheet (no LLM).
src/metrics.py       Stage 3b Computes the four 0-100 sub-scores + records data gaps.
src/rag_engine.py    Stage 4  Deterministic weighted composite -> threshold -> overrides.
                              Zero external dependencies; the audit trail.
src/llm_reasoner.py  Stage 5  Groq Llama 3.3 70B narrative layer, Pydantic-validated JSON.
                              Never re-scores; degrades gracefully if Groq is unavailable.
src/report_generator.py Stage 6  Jinja2 -> outputs/weekly/{project}/{date}.md
src/pipeline.py               Orchestrates stages 1-6 for one workbook.
src/run_weekly.py    Stage 7  CLI entrypoint: runs the pipeline over one or more files.
src/ppt_generator.py Stage 8  Monthly cross-project deck, reusing stage 5's output.

docs/RAG_Methodology.md   One-page methodology (the "why" behind the scoring).
docs/schedule.md          How to wire run_weekly.py to cron or GitHub Actions.
templates/weekly_report.md.j2  Report template.
outputs/weekly/, outputs/deck/  Generated artifacts (checked in as sample outputs).
tests/                    35 tests across ingestion/cleaning/metrics/rag_engine/sentiment.
```

## How to run it

### 1. Environment

This was built and tested against the **`LangGraph` conda environment** (Python 3.12),
which already had `groq`, `pydantic`, and `PyYAML`. Everything else came from
`requirements.txt`:

```bash
conda activate LangGraph      # or any Python 3.10+ environment
pip install -r requirements.txt
python -c "import nltk; nltk.download('vader_lexicon')"   # one-time, first run only
```

### 2. Groq API key

Put your key(s) in a `.env` file at the repo root:

```
GROQ_API_KEY_1="gsk_..."
GROQ_API_KEY_2="gsk_..."      # optional fallback
```

The code tries `GROQ_API_KEY_1`, then `GROQ_API_KEY_2`, then a plain `GROQ_API_KEY`. If
none are set or the Groq call fails for any reason, the pipeline **does not crash** — it
falls back to the deterministic RAG status with a note explaining the LLM narrative is
unavailable this run (see `src/llm_reasoner.py`'s `get_rag_reasoning`, always wrapped in
`try/except`).

### 3. Run the weekly report

```bash
python src/run_weekly.py --all
# or target specific files:
python src/run_weekly.py data/samples/S2P_Project.xlsx data/samples/Project_Plan_B.xlsx
```

This writes `outputs/weekly/{project}/{YYYY-MM-DD}.md` for each file, where the date is
the plan's own `Today's Date` (from its `Summary` sheet), not the system clock.

### 4. Generate the monthly executive deck

```bash
python src/ppt_generator.py
```

Writes `outputs/deck/Monthly_Executive_Deck.pptx` (6 slides), running the full pipeline
across every file in `data/samples/` and synthesizing cross-project themes from stage 5's
LLM output (no additional LLM call in this stage).

### 5. Run the tests

```bash
python -m pytest tests/ -v
```

## Key design decisions

The full list with reasoning is in `DECISIONS.md`. The highlights:

- **Config-driven ingestion, not per-file code.** `config/column_mapping.yaml` maps every
  canonical field to each file's actual header name (or `null` if that file doesn't have
  it). Adding a third project plan with yet another column layout means adding a YAML
  block, not touching `ingestion.py`.
- **`Project_Plan_B.xlsx` has no `Level` column at all** — only `Ancestors`, which
  empirically behaves as a depth proxy. Ingestion falls back to it and records the gap.
- **Milestone identification uses `Level <= 2`**, not exactly `1`, because one of S2P's
  10 real milestones ("Pre UAT") is tagged one level deeper than its siblings — a
  labeling inconsistency in the source, not a different kind of row.
- **`Status Comment` is empty in both files.** The blockers signal falls back to `On
  Hold?` flags and predecessor-overdue detection, and every report says so explicitly.
- **Sentiment uses VADER, not an LLM call**, per the brief — fast, deterministic, free.
  Groq is used only for the narrative layer in stage 5, and again is not called a second
  time in the deck-generation stage.
- **The sentiment formula deliberately differs from `SENTIMENT_SCORING_GUIDE.md`'s
  literal sample code.** That guide's formula computes a HIGH score for concerning
  comments (it even labels its own worked example "85 (high concern)"), which
  contradicts both its own stated contract ("high = calm") and the master prompt's
  methodology table ("invert so calm = high score") — and would let alarming
  stakeholder comments *improve* a project's composite score. Fixed to
  `(1 + avg_compound) / 2 * 100` so higher always means healthier, consistent with the
  other three signals. See `DECISIONS.md` item 20 for the full writeup.
- **Nothing is silently defaulted.** Every sub-score that can't be computed from the
  source data (missing dates, zero milestones detected, zero comments, etc.) falls back
  to a neutral default (50) and states why in the report's "Data Gaps & Assumptions"
  section — never a guessed value.

## Known limitations

- **Budget burn is explicitly out of scope.** Neither sample project plan has a cost or
  budget column. This is stated in `docs/RAG_Methodology.md` and in every generated
  report, not silently ignored or proxied by task count/duration.
- **Predecessor resolution is simplified**, not a full critical-path-method engine: it
  parses the leading row-number reference in a `Predecessors` cell and ignores FS/FF/SS
  dependency-type and lag-day suffixes. Good enough for "is my predecessor still open
  past its date," not for full schedule-network recalculation.
- **The reconstructed task tree isn't strictly single-rooted for S2P** (a project root
  row and two phase-rollup rows all share `Level == 0` in the source data). This doesn't
  affect any of the four scoring signals, which never depend on tree structure, but it
  means the tree shouldn't be trusted for anything beyond display context.
- **Sub-score scaling constants** (e.g., "8 points per critical-path row with negative
  float," "25% blocked-task ratio drives blockers to 0") are my implementation choices
  where the brief specifies the signal and weight but not the exact curve — documented
  as constants at the top of `src/metrics.py`, easy to retune against more historical
  data later.
- **No live scheduler is running.** `docs/schedule.md` documents a cron line and a GitHub
  Actions workflow; per the brief, standing up real infrastructure for a demo would be
  over-engineering.
- Only two sample project plans exist, so the monthly deck's cross-project "trend"
  slide is explicitly framed as a first synthesis across two single time-snapshots, not
  a fabricated multi-period trend line.

## What I'd do differently with more time

- Pull a small labeled set of historical weekly snapshots (even just 3-4 weeks) to
  validate and retune the sub-score scaling constants against actual outcomes, instead of
  reasoned-but-unvalidated defaults.
- Add a genuine critical-path-method pass over `Predecessors`/`Duration`/`Total Float`
  instead of the simplified leading-row-reference parse, to make the blockers signal's
  predecessor-overdue detection exact rather than approximate.
- Wire `docs/schedule.md`'s GitHub Actions option into an actual `.github/workflows/`
  file with a Slack/email delivery step, since "generate a report artifact" and "someone
  actually sees it weekly" are different problems.
- Add a confidence-weighted blend between the deterministic status and the LLM's own
  `confidence`/disagreement signal, surfaced distinctly in the report, rather than only
  showing the LLM's narrative alongside the (always-authoritative) deterministic status.
