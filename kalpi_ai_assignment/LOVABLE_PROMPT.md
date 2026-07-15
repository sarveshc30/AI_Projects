# Lovable prompt — Kalpi Strategy Builder frontend

Paste everything below the line into Lovable.dev to rebuild the frontend. The
backend (FastAPI) already exists and works — this only needs a new UI on top
of the existing API contract.

---

Build a web app called **Kalpi Strategy Builder** — a chat-style tool that turns a plain-English investment idea into a concrete, data-backed stock portfolio for the Indian equity market (NSE). It talks to an existing FastAPI backend; do not invent new endpoints, use the contract below exactly.

## Product flow

1. **Describe a strategy.** The user types a free-text investing idea (e.g. "buy Nifty 50 stocks with high RSI and strong 3-month momentum") into a chat box. A few example suggestion cards should be clickable to prefill the input (Momentum, Value, Quality, Trend-following are good examples).
2. **Clarification (optional, conversational).** The backend may come back asking a single follow-up question if the input was too vague (e.g. missing a universe or thesis). Render this as a normal chat message from the assistant and let the user reply in the same input box — the reply goes to a different endpoint (see below).
3. **Strategy review card.** Once the backend has enough detail, it returns a complete structured strategy: a stock universe, a list of hard filter conditions, a list of ranking/scoring metrics, a weighting scheme, and a target number of stocks. Render this as a clean summary card: universe name, filter conditions as readable rows ("RSI 14 > 55"), ranking metrics as a numbered list, weighting scheme, and the LLM's plain-English reasoning for each section (universe/filters/ranking/weighting) in a collapsible or subtly-styled explanation block. Two actions: **Modify strategy** (opens the input box for a free-text modification instruction) and **Accept & Screen** (primary CTA).
4. **Modification loop.** If the user asks to modify, show their instruction as a chat message, call the modify endpoint, then re-render the (possibly conflict-flagged) updated strategy card. If the backend flags a logical conflict between the modification and the original thesis (e.g. "add volatile microcaps" to a "conservative large-cap" strategy), show that warning prominently in a distinct color before the updated card.
5. **Live screening results.** Clicking "Accept & Screen" calls the screening endpoint, which fetches live market data and returns the actual matching stocks — this is the payoff moment of the whole app, so give it real design attention. Show a loading state ("Fetching live market data…", can take 10-60+ seconds depending on universe size) then render:
   - A summary line: how many stocks were screened out of the universe, how many passed filters, how many were selected, and when the data was fetched.
   - A results table/card grid: rank, ticker + company name, weight %, and the specific filter/ranking metric values relevant to *this* strategy (columns are dynamic — don't hardcode metric names, read them from the response). Sortable columns are a nice-to-have.
   - A visual weight breakdown (donut or bar chart of the portfolio weights) would elevate this a lot.
   - A "Skipped metrics" notice: some metrics the LLM chose aren't computable from free live data (e.g. anything needing 5-10 years of financial history); show these clearly but non-alarmingly, each with its stated reason.
   - Any data-quality warnings (partial fetch failures, universe truncated for size) shown as a small dismissible banner, not blocking.
   - If zero stocks passed the filters, say so plainly with the eligible/screened counts — this is a valid, expected outcome (the strategy was simply too strict for current market conditions), not an error state.
6. A **workflow tracker** (sidebar or top stepper) showing progress through: Strategy input → Universe → Filters → Ranking → Weighting → Complete → Screened. A **"New strategy"** action resets the session.
7. **Session history** — a lightweight sidebar list of past strategies run in this browser session (title = truncated original input), clickable to recall that conversation.

## Visual direction

Dark, modern, "quant fintech" aesthetic — think a trading terminal crossed with a clean AI chat product. Data-dense tables should stay readable (tabular numerals, right-aligned numbers, subtle zebra striping). It's fine to lean techy/glassmorphic. Mobile-responsive is a bonus, not a requirement — this is primarily a desktop analysis tool.

## API contract (FastAPI backend, base path `/api`)

All requests/responses are JSON. Maintain a `session_id` (any client-generated string, e.g. a timestamp) for the lifetime of one strategy conversation.

### `POST /api/chat/start`
Start a new strategy from a free-text description.
```json
// request
{ "session_id": "string", "user_input": "string" }
// response
{ "session_id": "string", "stage": "clarification" | "complete", "state": { /* Strategy object, see below */ }, "message": "string" }
```
If `stage` is `"clarification"`, `message` is the follow-up question to show the user — collect their answer and send it to `/api/chat/respond` next. If `stage` is `"complete"`, `state` contains the full generated strategy — render the review card.

### `POST /api/chat/respond`
Answer a pending clarification question.
```json
// request
{ "session_id": "string", "answer": "string" }
// response — same shape as /api/chat/start (may ask another clarification, or come back "complete")
```

### `POST /api/modify`
Request a change to an existing (complete) strategy.
```json
// request
{ "session_id": "string", "modification_input": "string" }
// response
{ "session_id": "string", "stage": "complete", "state": { /* updated Strategy object, includes latest_mod_plan */ }, "message": "string" }
```
`state.latest_mod_plan` (string, may contain `\n`) is the LLM's plain-English modification plan — show it as a message before the updated card. If it starts with "⚠ Conflict:", style that line as a warning.

### `POST /api/screen`
Run the approved strategy against live market data. Call this right after the user accepts the strategy (the session already has the complete strategy server-side; you only send the session id).
```json
// request
{ "session_id": "string" }
// response: ScreenResult (see below)
```
This call is slow (10-90+ seconds depending on universe size) — show a clear loading state, don't let the UI look frozen.

### `POST /api/reset`
Clear a session.
```json
// request
{ "session_id": "string", "user_input": "" }
// response
{ "ok": true }
```

### `GET /api/session/{session_id}`
Fetch the current state of a session (useful for restoring a session on page reload).

## Data shapes

**Strategy object** (the `state` field returned by start/respond/modify):
```ts
{
  input: string;                  // original user text
  enriched_input: string;         // LLM-expanded strategy description
  universe: string;                // e.g. "Nifty 50", "Nifty 500", "Nifty Microcap 250"
  filters: Array<{
    metric: string;                // e.g. "RSI 14", "PE"
    operator: "<" | ">" | "<=" | ">=" | "==";
    compare_type: "value" | "metric";
    value: number | null;          // set when compare_type === "value"
    compare_metric: string | null; // set when compare_type === "metric" (metric-vs-metric filter, e.g. "EMA 20 > EMA 50")
  }>;
  ranking_metrics: string[];       // ordered list, first = highest priority
  weight_type: "equal" | "metric";
  weight_metric: { metric: string; inverse: boolean } | null; // set when weight_type === "metric"; inverse = lower value gets higher weight
  top_n: number;                   // target portfolio size
  reasoning: {                     // plain-English LLM explanations, one per section
    universe?: string; filter?: string; rank?: string; weightage?: string;
  };
  latest_mod_plan?: string;        // only present after a /api/modify call
  is_complete: boolean;
}
```

**ScreenResult object** (the response of `/api/screen`):
```ts
{
  success: boolean;
  message?: string;                // set when success === false, explains what went wrong
  universe: string;
  universe_total_tickers: number;  // total constituents in this universe
  universe_screened_tickers: number; // how many were actually fetched (may be capped for large universes)
  universe_truncated: boolean;
  eligible_count: number;          // passed all filters
  selected_count: number;          // final portfolio size (<= top_n if fewer stocks were eligible)
  requested_top_n: number;
  weight_type: "equal" | "metric";
  weight_metric?: string;
  results: Array<{
    ticker: string;                // e.g. "RELIANCE.NS"
    symbol: string;                 // e.g. "RELIANCE"
    company_name: string;
    rank: number;
    composite_score: number;        // 0-1, higher = better rank
    weight_pct: number;             // portfolio weight, all selected stocks sum to 100
    filter_values: Record<string, number | null>;   // this stock's value for each filter metric used
    ranking_values: Record<string, number | null>;  // this stock's value for each ranking metric used
    weight_metric_value: number | null;
    missing_metrics: string[];      // metrics that had no data for this specific stock
  }>;
  skipped_metrics: Array<{
    metric: string;
    reason: string;                 // human-readable, show as-is
    scope: "global" | "near_unsupported"; // "global" = never computable; "near_unsupported" = mostly missing across this universe
  }>;
  failed_tickers: Array<{ ticker: string; reason: string }>;
  data_quality_warning: string | null; // free-text summary banner, may combine multiple issues
  fetched_at: string;               // ISO timestamp
}
```

Build the columns of the results table dynamically from the union of keys across `filter_values` and `ranking_values` in the first result item — different strategies use different metrics, so don't hardcode column names beyond rank/ticker/company/weight.
