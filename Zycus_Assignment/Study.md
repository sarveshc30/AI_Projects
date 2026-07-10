# Study Notes — Project Health Reporting Agent

Deep-dive reference for this build. Read this and you should be able to answer any
question about what was built, why, and what the numbers mean.

## 1. The assignment in one paragraph

Zycus wants leadership to see project health without manually chasing PMs. The take-home
asked for three things: (1) a one-page RAG methodology doc a VP could read, (2) a working
agent that reads a real project plan (Excel export from a PM tool), computes a Red/Amber/
Green status with an exact prescribed formula, and explains its reasoning in plain English
even when the data is messy/incomplete, and (3) a monthly cross-project executive deck
that actually synthesizes patterns rather than pasting two summaries side by side.

## 2. The two sample files and what makes them different

| | `S2P_Project.xlsx` (Outokumpu / "Titan") | `Project_Plan_B.xlsx` (UniSan) |
|---|---|---|
| Task sheet name | `Outokumpu- S2P Project` | `Project Plan` |
| Rows | 493 | 383 |
| `Level` column | Present (0-8) | **Absent** — falls back to `Ancestors` |
| Per-row `RAG` column | Present | **Absent** |
| `Phase/Milestone` populated rows | 10 (all Level 1-2) | **0** |
| `Comments` sheet | 9 real comments (no header, row-triplets) | **Empty** (no header, no rows) |
| `Status Comment` column | Empty in all rows | Empty in all rows |
| `On Hold?` count | 3 | 0 |
| Today's Date (Summary sheet) | 2026-07-02 | 2026-07-02 |
| Project window | 2025-12-05 to 2026-12-07 | 2026-02-11 to 2026-10-09 |
| % Complete (Summary) | 71% | 44% |

These aren't contrived differences — they're what's actually in the files. Plan B is
deliberately the "messier/more incomplete" of the two, which is exactly the scenario the
brief says the pipeline must handle gracefully (never crash, never silently guess).

Both files share a `Summary` sheet with the same key/value shape (Project Manager, Project
Start/End Date, Not Started/In Progress/Completed/On Hold counts, At Risk, Project Stage,
% Complete, Schedule Health, **Today's Date**, Target Start/End Date, Schedule Delta,
Duration, Target Dates Variance, Schedule Variance, Project Status). In both files, every
"Target ..."/"Schedule Delta"/"Variance" field is literally the string `#UNPARSEABLE`.

## 3. The four signals, in detail

All code lives in `src/metrics.py`; constants at the top of that file (`FLOAT_PENALTY_PER_
CRITICAL_NEGATIVE_ROW = 8`, `MILESTONE_OVERDUE_PENALTY_PER_DAY = 2.5`, `BLOCKER_RATIO_SCALE
= 400`) are the "how do raw counts become 0-100" choices left to my judgment — the brief
fixes the four signals and their weights, not these curves.

### Schedule slippage (35%) — `compute_schedule_slippage`
1. `expected_pct = (todays_date - project_start_date).days / (project_end_date - project_start_date).days`, clamped to [0,1].
2. `actual_pct` = the Summary sheet's `% Complete`.
3. `behind_by = max(0, expected_pct - actual_pct)`; `base_score = 100 - behind_by * 200` (clamped 0-100). Ahead-of-schedule or on-schedule projects get a full 100 base.
4. Penalty: -8 points per row where `Critical? = True` AND `Total Float < 0`, capped at -60 total.
5. If any of Today's Date / start / end / % complete is missing, the whole sub-score defaults to 50 (neutral) and a data gap is recorded — never a guess.

**S2P**: expected 56.9% vs actual 71% → ahead of schedule → base 100. 0 critical-negative-float rows → **score 100**.
**Plan B**: expected 58.8% vs actual 44% → 14.8 points behind → base ≈70.5. 0 critical-negative-float rows → **score 70.5**.

### Milestone health (30%) — `compute_milestone_health`
1. A row is a "milestone" if `Level <= 2` AND `Phase/Milestone` is populated. (Brief says "populated Phase/Milestone, low Level"; empirically S2P's 10 milestones sit at Level 1 except one ["Pre UAT"] at Level 2 — `<=2` catches all 10 without pulling in any of the hundreds of leaf-level rows, which go up to Level 8.)
2. For each milestone, if `Status != Completed` and `Baseline Finish < Today's Date`, it's overdue; penalty = `min(40, days_overdue * 2.5)`.
3. Score = `100 - sum(penalties)`, clamped 0-100.
4. If zero milestones are found (as in Plan B, where `Phase/Milestone` is populated on 0 rows), the sub-score defaults to 50 (neutral) with a data gap — the rule is applied exactly as specified, not redesigned to invent milestones from task names.

**S2P**: 10 milestones found; 2 overdue — "Configuration and Build phase" (105 days overdue) and "Hyper Care(Measure and Adoption) Solution" (34 days overdue). Penalty = min(40,105*2.5)+min(40,34*2.5) = 40+40 = 80 (capped). **Score 20.**
**Plan B**: 0 milestones found → **score 50 (neutral, flagged as a data gap)**.

### Blockers (20%) — `compute_blockers`
1. Three inputs, summed into `open_items_count`: rows with non-empty `Status Comment`; rows with `On Hold? = True`; not-started rows whose predecessor (parsed from `Predecessors`, leading row-number reference only — see `cleaning.parse_predecessor_refs`) is itself not Completed and past its Baseline Finish/End Date.
2. `score = 100 - min(100, (open_items_count / total_task_count) * 400)` — i.e. a 25% "open item" ratio drives the score to 0. Ratio-based so it's comparable across differently-sized plans.
3. `Status Comment` being empty in both files is recorded as a data gap every time (it degrades this signal's precision but doesn't zero it out — On Hold and predecessor-overdue still work).

**S2P**: 0 status-comment rows + 3 on-hold + 7 predecessor-overdue = 10 open items / 493 = 2.03% → **score 91.9**.
**Plan B**: 0 + 0 + 19 = 19 / 383 = 4.96% → **score 80.2**.

### Stakeholder sentiment (15%) — `src/sentiment.py`, VADER
1. Every comment's text is scored with NLTK's VADER `polarity_scores()['compound']`
   (range -1 very negative .. +1 very positive).
2. Average the compound scores, then map to 0-100 with `score = (1 + avg_compound) / 2 * 100`,
   so calm/positive comments (compound near +1) score near 100 and alarming ones
   (compound near -1) score near 0 — the same "higher = healthier" direction as the
   other three signals.
3. **This formula deliberately differs from `SENTIMENT_SCORING_GUIDE.md`'s literal
   sample code**, which computes `(1 - compound) / 2 * 100` and calls the result an
   "urgency" score. That formula is internally inconsistent with its own stated contract
   ("high = calm, low = urgent") and with the master prompt's methodology table ("Invert
   so calm = high score") — plugging in the guide's own worked example
   (`compound = -0.7`) gives 85, which the guide itself labels "high concern," i.e. a
   HIGH score for CONCERNING comments. Wired unmodified into a composite where higher
   always means healthier, that would let alarming stakeholder comments *improve* a
   project's RAG status. This was caught and fixed rather than copied literally — see
   `DECISIONS.md` item 20 for the full writeup.
4. If there are no usable comments (empty list, or all `None`/blank), the score defaults
   to 50 (neutral) with a data gap recorded.

**S2P**: 9 comments, avg_compound = -0.072 (slightly negative — mentions of pending JDE mapping, impacted workshop dates) → `(1 + (-0.072)) / 2 * 100` → **score 46** (mildly below neutral, consistent with "slightly concerning but mostly calm" comments).
**Plan B**: 0 comments → **score 50 (neutral, flagged)**.

## 4. Composite scores and final status

`composite = 0.35*schedule + 0.30*milestone + 0.20*blockers + 0.15*sentiment`. Thresholds:
>=80 Green, 60-79 Amber, <60 Red. Two hard overrides (checked after thresholding, win if
triggered): any milestone overdue >10 days (configurable) forces Red; any critical-path
task with negative float and zero documented recovery plan (i.e., zero non-empty Status
Comment rows anywhere in the file) forces Red.

**S2P**: composite = 0.35*100 + 0.30*20 + 0.20*91.9 + 0.15*46 = 35 + 6 + 18.38 + 6.9 = **66.28 -> 66.3, Amber by threshold**. But 2 milestones are overdue by >10 days -> **override fires -> final status = Red**. This is the single most important "gotcha" in the sample outputs: the weighted average alone would call this project Amber, but the deterministic override rule (correctly) escalates it to Red because real, named milestones have blown past their dates by 34 and 105 days. The generated report and the LLM narrative both call this out explicitly.

**Plan B**: composite = 0.35*70.5 + 0.30*50 + 0.20*80.2 + 0.15*50 = 24.675+15+16.04+7.5 = **63.2 -> Amber**. No overrides fire (0 milestones detected so none can be "overdue"; 0 critical-negative-float rows). **Final status = Amber.**

## 5. Code walkthrough (file by file)

- **`config/column_mapping.yaml`** — the only place that knows both files' actual header
  names. `task_sheet_column_map` is `canonical_field -> {file_key: source_header_or_null}`.
  `level_fallback` documents the Ancestors substitution. `summary_key_aliases` maps the
  Summary sheet's raw row-1 label text to canonical keys. `comments_sheet_format`
  documents the header-less row-triplet layout. `null_tokens` lists `#UNPARSEABLE`/`""`.
- **`src/ingestion.py`** — `ingest_workbook()` resolves a file's profile from the YAML
  (normalizing filename spacing/case), picks the task/comments/summary sheets (falling
  back to heuristics for an unrecognized file), and produces an `IngestionResult` of raw
  (uncleaned) dict records plus a running `data_gaps` list. `_row_id` is the literal Excel
  row number, used later to resolve `Predecessors` references.
- **`src/cleaning.py`** — `clean_project()` converts null tokens to `None`, coerces
  numeric/date fields, applies checkbox-field blank=False semantics, parses `Duration`/
  `Variance` strings (e.g. `"262d"`, `"-6d"`) to floats, parses `Predecessors` into
  `predecessor_row_ids` (`parse_predecessor_refs`), and builds a best-effort task tree
  (`_build_task_tree`) for `project_display_name` resolution.
- **`src/sentiment.py`** — thin wrapper around NLTK's VADER, exactly per
  `SENTIMENT_SCORING_GUIDE.md`.
- **`src/metrics.py`** — the four `compute_*` functions described in section 3, plus
  `ProjectMetrics.all_data_gaps` which flattens every sub-score's gap list for reporting.
- **`src/rag_engine.py`** — `compute_rag_status()`: weighted composite, threshold mapping,
  then the two override checks. Pure function of a `ProjectMetrics` object; no I/O, no
  LLM, so it's exactly reproducible and is what a report falls back to if Groq is down.
- **`src/llm_reasoner.py`** — `get_rag_reasoning()` builds a prompt embedding the four
  sub-scores, the deterministic status, any triggered overrides, the data gaps, and a
  sample of real stakeholder comments; calls Groq's `llama-3.3-70b-versatile` via
  `chat.completions.create` (note: the brief's example code used Anthropic's
  `messages.create` shape by mistake — corrected here); validates the response against
  the `RAGReasoning` Pydantic model. Returns `(reasoning, None)` on success or
  `(None, error_string)` on any failure — callers never need to catch exceptions
  themselves. Also works around a local environment quirk: this machine's
  `SSL_CERT_FILE` env var points at a non-existent path, which crashes httpx before the
  try/except can help; fixed by repointing it at `certifi.where()` when the configured
  path is missing.
- **`src/report_generator.py`** + **`templates/weekly_report.md.j2`** — assembles a
  context dict (scores, overrides, LLM output or fallback note, all data gaps
  deduplicated, per-signal detail) and renders it with Jinja2 to
  `outputs/weekly/{project_slug}/{YYYY-MM-DD}.md`, where the date is the plan's own
  Today's Date.
- **`src/pipeline.py`** — `run_pipeline_for_file()` wires stages 1-6 together; this is
  what both `run_weekly.py` and `ppt_generator.py` call.
- **`src/run_weekly.py`** — CLI: `python src/run_weekly.py --all` or specific file paths.
- **`src/ppt_generator.py`** — `generate_deck()` runs the pipeline for every sample file
  (via `run_pipeline_for_file(..., write_report=False)` to avoid re-writing the weekly
  markdown), then builds 6 slides:
  1. Title + reporting period (derived from the max Today's Date across projects)
  2. Portfolio RAG overview (table: project, status, composite, primary driver — the
     override reason if one fired, else "weighted composite (X/100)")
  3. Cross-project trends — rule-based keyword clustering (`THEME_KEYWORDS`) over both
     projects' `overrides_triggered` + LLM `key_risks`/`data_gaps`, split into "recurring
     across both" vs "project-specific," explicitly framed as a first synthesis given
     only one time-snapshot per project (not a fabricated trend line)
  4. Emerging risks, ranked by how many projects raised a theme, then tagged
     `[Both projects]` or `[ProjectName]`
  5. Compact snapshots table (project, RAG, % complete, top risk)
  6. Recommendations — deduped-by-theme actions pulled from each project's LLM output,
     plus one portfolio-wide action (stand up the weekly cadence)

  Crucially, this stage never calls the LLM again — everything on the cross-project
  slides is assembled from stage 5's already-computed `key_risks`/`recommended_actions`/
  `data_gaps`, per the brief's explicit instruction.

## 6. Tests (`tests/`, 35 total, all passing)

- `test_ingestion.py` — both files normalize to the identical set of canonical dict keys
  despite different source columns; Plan B's `Level`/`RAG` gaps are recorded; S2P's 9
  comments and Plan B's 0 comments are both asserted; predecessor row-id resolution.
- `test_cleaning.py` — `#UNPARSEABLE` -> `None`; duration/variance string parsing;
  checkbox blank=False semantics; project display name resolution; predecessor lag-suffix
  parsing (`"263FS +1d"` -> `[263]`).
- `test_metrics.py` — synthetic edge cases (missing summary dates -> neutral default;
  zero milestones -> neutral default; more open items -> strictly lower blockers score)
  plus real-file assertions (S2P has 10 milestones, Plan B has 0; S2P has 9 comments,
  Plan B has 0).
- `test_rag_engine.py` — threshold boundaries; milestone-overdue override firing (and not
  firing when under the day threshold); critical-negative-float override firing (and not
  firing when a recovery plan is documented); weights sum to 1.0.
- `test_sentiment.py` — empty/blank input -> neutral 50; positive text scores low-concern;
  negative text scores high-concern; score always in [0,100].

## 7. Anticipated Q&A

**Q: Why does S2P show Red when its composite score (66.3) is in the Amber band?**
A hard override fired: two named milestones ("Configuration and Build phase," "Hyper
Care...") are overdue by more than 10 days without being marked Completed. The brief's
override rules are designed to catch exactly this — an average that looks "OK" while a
real, specific commitment has blown past its date. See section 4 above.

**Q: Why is Plan B's milestone score exactly 50 and not computed at all?**
Its `Phase/Milestone` column is populated on zero rows — the milestone-identification
rule (populated Phase/Milestone + low Level) as specified in the brief simply finds no
milestones in this file. Rather than redesigning the rule or inventing milestones from
task names, the sub-score defaults to neutral (50) and the report states this explicitly
as a data gap.

**Q: Why does the sentiment score for a "slightly concerned" set of comments come out
lower (46) than 50?** The sub-score is on a "high = calm/healthy" scale, matching every
other signal's "higher = healthier" direction so the composite adds up sensibly. A
slightly negative average compound (-0.072) maps to a score just under the 50 neutral
midpoint via `(1 + avg_compound) / 2 * 100`. Note this deliberately corrects
`SENTIMENT_SCORING_GUIDE.md`'s own sample formula, which computes the opposite direction
and contradicts its own stated contract — see `DECISIONS.md` item 20.

**Q: Would this break on a third project plan with yet another column layout?**
Only if that file's canonical fields weren't in `config/column_mapping.yaml` yet — the
ingestion code has a documented fallback (first non-Comments/Summary sheet as the task
sheet; match any configured header name that exists in the new file), but for full
correctness you'd add a new block to the YAML, not touch any `.py` file.

**Q: What happens if the Groq API key is invalid or Groq is down?**
`get_rag_reasoning()` catches any exception and returns `(None, error_message)`. The
report generator then renders the deterministic status and sub-scores exactly as normal,
with a note that the LLM narrative was unavailable this run. This was verified live by
running the pipeline with a deliberately invalid key (see `DECISIONS.md` item 15/16 and
the conversation transcript where this was tested).

**Q: Where's budget/cost in the scoring?**
Nowhere, on purpose — neither source file has a cost or budget column. This is named
explicitly in `docs/RAG_Methodology.md`, in `DECISIONS.md`, and in every generated
report's "Data Gaps & Assumptions" section.
