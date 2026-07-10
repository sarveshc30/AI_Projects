# Decisions Log

Running log of assumptions and design choices made autonomously during the build, and why.
Ordered roughly by when they came up.

## Data discoveries (from directly inspecting both workbooks before writing code)

1. **`Project Plan B.xlsx` has no `Level` column at all** (only `Ancestors`). Empirically,
   `Ancestors`' integer values (0–8) match the same distribution shape as S2P's `Level`
   column, so it behaves as a depth proxy. Decision: `config/column_mapping.yaml` maps
   `level: null` for Plan B and `level_fallback.fallback_field: ancestors`; ingestion
   substitutes `ancestors` for `level` on that file and records a data gap saying so.

2. **`Status Comment` is 100% empty in both sample files** (0 of ~494 and ~384 rows). The
   brief's blockers signal leans on this column; since it's unusable here, blockers is
   driven by `On Hold? = Yes` counts and not-started tasks whose predecessor is overdue.
   The report states this column was empty rather than silently treating blockers as
   perfect.

3. **`Project Plan B.xlsx`'s `Comments` sheet is completely empty** (no header, no rows).
   S2P's has 9 real informal comments, with **no header row** — data starts at row 1 in
   triplets (1 data row + 2 blank spacer rows), columns = task-row-reference, comment
   text, author, timestamp. Sentiment for Plan B defaults to neutral (50) with an
   explicit data gap; this is a real difference in data richness between the two plans,
   not an ingestion bug.

4. **`Project Plan B.xlsx` has no per-row `RAG` column** (S2P has both `RAG` and
   `Schedule Health` per row; Plan B only has `Schedule Health`). `task_rag` is treated
   as optional/nullable in the canonical schema — never backfilled from `Schedule Health`,
   since that would silently conflate two different source signals.

5. **The `Project Name` column is blank on every row in both files.** The actual project
   name text lives in the root task row's `Task Name` (e.g., "Zycus - Titan S2P
   Implementation"). `CleanedProject.project_display_name` reads the first row at the
   plan's minimum `Level`/`Ancestors` value, falling back to the file name if that's
   also missing.

6. **Milestone rows are not consistently tagged at `Level == 1`.** 9 of S2P's 10
   `Phase/Milestone`-populated rows sit at `Level 1`; one ("Pre UAT") sits at `Level 2`.
   Decision: interpret the brief's "low Level" as `Level <= 2` rather than exactly 1 —
   this still safely excludes the hundreds of leaf-level task rows (Levels go up to 8)
   while not dropping a milestone due to what looks like a one-off labeling
   inconsistency in the source data.

7. **S2P's `Level` values are not strictly single-rooted**: the project root row and two
   phase-rollup rows ("Phase 1- S2C", "Phase 2 - P2P") all share `Level == 0`. The
   reconstructed task tree (`cleaning._build_task_tree`) is therefore not a clean single
   tree. This is left as-is and documented rather than "fixed," since none of the four
   RAG signals depend on strict tree correctness — the tree is informational only.

8. **Predecessors reference raw Excel row numbers**, sometimes suffixed with dependency
   type/lag notation (`FS +1d`, `FF`, `SS`). Verified empirically that predecessor `226`
   in S2P resolves to the correct row. Decision: parse only the leading integer per
   comma-separated token and ignore the FS/FF/SS/lag suffix — a deliberate
   simplification, not a full critical-path-method dependency engine, since the brief's
   blockers signal only needs "is my predecessor still open past its date," not full
   schedule-network recalculation.

9. **Checkbox-style columns** (`On Hold?`, `Not Applicable?`, `Critical ?`) only ever
   contain `True` or blank in both files — never an explicit `False`. Decision: treat
   blank as `False` for these three fields specifically (a checkbox semantics), unlike
   every other field where blank/`#UNPARSEABLE` means "missing data" and becomes `None`.
   This is a narrower, explicitly documented exception to the "never guess" rule.

10. **Neither file has a cost/budget column.** Budget burn is out of scope for scoring,
    stated explicitly in `docs/RAG_Methodology.md` and in every generated report's data
    gap list — never silently substituted with a proxy (e.g., task count or duration).

## Implementation choices (the brief specifies signals/weights exactly; these are the
## "how do raw counts become a 0-100 number" details it leaves to us)

11. Schedule slippage base score: `100 - min(100, max(0, expected_pct - actual_pct) * 200)`,
    then an additional penalty of 8 points per critical-path row with negative float
    (capped at 60). Ahead-of-schedule projects get a full 100 base score.
12. Milestone health penalty: `2.5 points per day overdue`, capped at 40 per milestone.
13. Blockers score: ratio of "open items" (on-hold + status-comment + predecessor-overdue
    rows) to total task count, scaled so a 25% open-item ratio drives the score to 0.
    Ratio-based (not raw count) so scores are comparable across differently-sized plans
    (S2P: 493 rows vs. Plan B: 383 rows).
14. Both hard override rules use a configurable `milestone_overdue_override_days` param
    (default 10, per the brief) and treat "no documented recovery plan" as "this file has
    zero non-empty Status Comment rows anywhere" — since that's true for both sample
    files, any critical-path negative-float row would trigger this override the moment
    one exists (neither sample project currently has one).

## A real bug caught in the provided sentiment formula

20. **`SENTIMENT_SCORING_GUIDE.md`'s own formula is internally inconsistent, and I
    deviated from its literal code to fix it.** The guide's `compound_to_urgency_score`
    (and the identical formula inside its `SentimentAnalyzer.compute_project_sentiment`
    example) is `score = (1 - compound) / 2 * 100`. Plugging in the guide's own worked
    example (`compound = -0.7`, "very negative") gives `score = 85`, which the guide
    itself labels **"85 (high concern)."** But the guide's class docstring says the
    method should return "0-100 sentiment score (**high = calm**, low = urgent...)" —
    and the master prompt's methodology table says the same ("Invert so calm = high
    score"). The literal formula and the stated contract point in opposite directions:
    following the formula as written means a project with alarming, urgent stakeholder
    comments gets a **high** sentiment sub-score, which — combined with a positive 15%
    weight in a composite where higher always means healthier — would make alarming
    comments *improve* a project's RAG status. That's backwards from what every other
    signal in the composite does and from what both source documents say they intend.
    Decision: implement `score = (1 + compound) / 2 * 100` instead (calm/positive
    comments -> near 100, alarming ones -> near 0), matching the stated contract and
    making the composite direction consistent across all four signals. See the
    docstring in `src/sentiment.py` for the same explanation inline. This changed
    S2P's sentiment sub-score from 53 to **46** and its composite from 67.3 to **66.3**
    — the final RAG status (Red, via the milestone override) is unaffected either way,
    but the corrected number is the one that's actually meaningful.

## LLM / infra

15. Confirmed `llama-3.3-70b-versatile` is a live, working Groq model via a real test
    call before committing to it in code (the brief's example code used
    `client.messages.create`, which is Anthropic's Messages API shape, not Groq's —
    corrected to Groq's OpenAI-compatible `client.chat.completions.create`).
16. This machine's conda env (`LangGraph`) sets `SSL_CERT_FILE` to a path that doesn't
    exist, crashing httpx before `get_rag_reasoning`'s try/except could catch it.
    Fixed by repointing `SSL_CERT_FILE` at `certifi.where()` when the configured path is
    missing — necessary for the Groq call to work at all in this environment, not a
    workaround for a code bug.
17. `.env` provides `GROQ_API_KEY_1` and `GROQ_API_KEY_2`; code tries `_1` then `_2` then
    a generic `GROQ_API_KEY`, so either provided key works.
18. Stage 8 (`ppt_generator.py`) does **not** make a fresh LLM call. Per the brief, it
    reuses stage 5's `key_risks`/`recommended_actions`/`data_gaps` and does rule-based
    keyword clustering (schedule/milestone/sentiment/blockers/data-gap themes) to build
    the cross-project synthesis and ranked-risk slides. This keeps the "don't regenerate
    insights from scratch" instruction literal, not just directionally followed.

## File/naming

19. Sample files were **copied** (not moved) from the repo root (`S2P Project.xlsx`,
    `Project Plan B.xlsx`) into `data/samples/S2P_Project.xlsx` and
    `data/samples/Project_Plan_B.xlsx` to match the brief's exact naming, without
    touching the user's original files.
