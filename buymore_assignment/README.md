# E-Commerce Brand Intelligence Agent

**Candidate:** Sarvesh C

Given a brand name, this agent autonomously researches the brand's presence on Amazon.in
and produces a structured Excel row plus a detailed Markdown report — replacing 30–45
minutes of manual research per brand with a ~90 second run.

---

## Setup

```bash
# 1. Install dependencies (uv reads pyproject.toml / uv.lock)
uv sync

# 2. Install the Playwright browser binary
uv run playwright install chromium

# 3. Configure environment
cp .env.example .env
#    then edit .env and add your two Groq API keys
```

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY_1` | Yes (for LLM analysis) | Primary Groq key |
| `GROQ_API_KEY_2` | Yes (for LLM analysis) | Secondary key, used automatically when the primary rate-limits, expires, or times out |
| `GROQ_MODEL` | No | Defaults to `llama-3.3-70b-versatile` |

If the keys are absent the agent **still runs end-to-end** — it logs a warning and falls
back to deterministic rule-based category resolution and weakness generation.

### Run

```bash
uv run main.py "Mamaearth"

# options
uv run main.py "Biotique" --headed          # watch the browser (debugging selectors)
uv run main.py "Mamaearth" --excel out.xlsx # write to a different workbook
```

---

## Tools used and why

| Choice | Why |
|---|---|
| **Playwright** (sync API) | Amazon.in renders search results and product detail sections client-side; a plain `requests` fetch returns a shell. Playwright also lets one browser *context* persist cookies across the whole run, which looks far more like a real visitor than repeatedly launching fresh browsers. |
| **BeautifulSoup** | Once a page has rendered, parsing the static snapshot with `page.content()` → BS4 is much faster and more readable than dozens of Playwright locator round-trips. |
| **Groq + `llama-3.3-70b-versatile`** | Free tier, very fast inference, and good enough at short structured-extraction and summarisation tasks. Speed matters against the 2–5 minute budget. |
| **LangChain (`ChatGroq`, `Runnable`)** | Used narrowly for `with_structured_output(...)` — it binds a Pydantic schema to the call so the LLM returns a validated object rather than text I'd have to regex. The dual-key fallback is implemented as a `Runnable` subclass so `prompt \| llm` still composes natively. |
| **Pydantic** | Every value that crosses a module boundary is a validated model (`schemas.py`) — this is what enforces "no free-form text in structured fields". |
| **pandas + openpyxl** | pandas handles the read-modify-append cycle for the workbook in a few lines; openpyxl is dropped to afterwards purely to style the header row and set column widths. |

### Architecture

```
main.py            CLI + orchestration, per-stage error isolation
├── scraping_module.py   Playwright/BS4 scraping (search, URL extraction, product pages)
├── listing_audit.py     Deterministic 5-dimension weighted scoring
├── analysis.py          LLM synthesis: category resolution + weakness report
├── outputs.py           Excel (pandas) + Markdown writers
├── schemas.py           Pydantic models for every structured value
├── llm.py               Groq client with two-key fallback
└── logger.py            Timestamped console logging
```

### Listing quality formula

The 1–10 score is **computed deterministically**, not asked of the LLM, so it's
reproducible and auditable. Each dimension is graded `GOOD` (1.0) / `MODERATE` (0.5) /
`BAD` (0.0) and weighted:

| Dimension | Weight | GOOD when |
|---|---|---|
| Title Quality | 20% | ≥8 words **and** brand **and** sub-category present |
| Visual Quality | 20% | ≥6 images |
| Content Richness | 25% | ≥3 of {bullets, description, specifications, A+ content} |
| Data Accuracy | 15% | capped at MODERATE — see limitations |
| Social Proof | 20% | ≥1,000 ratings **and** ≥4.0 stars |

`score = round(Σ(grade × weight) × 10)`, floored at 1. The LLM only writes the one-sentence
remark naming the weakest areas.

---

## Known limitations and trade-offs

1. **Amazon.in only.** The `Portals Live` column reports only Amazon because that's the
   only portal actually checked. Flipkart/Nykaa/quick-commerce are listed as *unverified*
   in the weakness report rather than asserted absent — claiming "not on Flipkart" without
   checking would be a fabricated finding.
2. **Data Accuracy caps at MODERATE.** The brief asks whether pack size and ingredients
   match *between text and images*. Verifying that needs OCR over product imagery, which
   isn't implemented — so the dimension only checks the text side and never awards GOOD.
   This deliberately costs a point rather than overstating confidence.
3. **Seller classification is naive.** A seller is called "third-party" when the brand name
   isn't a substring of the seller name. For Mamaearth this flags *Honasa Consumer Limited*
   as third-party even though Honasa is Mamaearth's parent company. Resolving this properly
   needs a brand→legal-entity mapping.
4. **Sponsored ads are session-dependent.** Ad placements vary by session, geography, and
   time of day. Both sample runs legitimately returned `Running Ads: No` on the live SERP.
   The detector checks three independent signals (ad-feedback `aria-label`, a literal
   "Sponsored" badge, and `/sspa/click` redirect hrefs) and was verified positively against
   a saved SERP fixture and synthetic fixtures for all three — but **the positive path was
   not observed on a live run**, so treat a `No` as "none seen this run", not "never runs ads".
5. **The LLM path is wired but unverified end-to-end.** No Groq keys were present in the
   environment during development, so every sample output in this repo was produced by the
   **rule-based fallback**. The LLM code paths (structured category resolution, weakness
   generation, audit remark) are implemented and defensively wrapped, but have not been run
   against the live Groq API.
6. **Selectors are brittle by nature.** Amazon reshuffles CSS class hashes periodically.
   The scraper prefers stable signals (`aria-label`, element IDs like `#productTitle`,
   `/dp/` in hrefs) over class names where possible, and every extraction falls back to a
   default rather than raising — but a major Amazon redesign will still require updates.
7. **Rate limiting / bot detection.** Requests are paced with randomised delays (2–4s on
   search pages, 4–8s on product pages) and run serially in one browser context. This is
   adequate for occasional single-brand runs; a high-volume batch would need residential
   proxies and would likely hit CAPTCHAs.
8. **Top 5 products come from page one of search.** Ranking is by rating count as read off
   the search tiles, so a highly-rated product that doesn't surface on page one is missed.

---

## Sample output

### Console

```
======================================================================
  LEAD GEN AGENT  |  Brand: Mamaearth
  Started: 2026-07-20 02:13:55
======================================================================

  [02:13:55] llm !! GROQ_API_KEY_1/GROQ_API_KEY_2 not set - falling back to rule-based analysis
  [02:14:10] discovery_agent -> found on Amazon | matched brand: Mamaearth
  [02:14:11] url_extractor -> 5 amazon product URLs found
  [02:14:21] marketplace_agent -> 57812 ratings | seller: RK World Infocom Pvt Ltd | https://www.amazon.in/Mamaearth-Natural-Turmeric-Saffron-Removal/dp/B0FPWWH55W
  [02:14:32] marketplace_agent -> 57785 ratings | seller: Honasa Consumer Limited | https://www.amazon.in/Mamaearth-Shampoo-Growth-Control-Keratin/dp/B099F3WJKW
  [02:14:44] marketplace_agent -> 30637 ratings | seller: Honasa Consumer Limited | https://www.amazon.in/Mamaearth-Vitamin-Face-Turmeric-Illumination/dp/B08MF36S6C
  [02:14:57] marketplace_agent -> 28439 ratings | seller: RK World Infocom Pvt Ltd | https://www.amazon.in/Mamaearth-Daily-Moisturizing-Lotion-Babies/dp/B0774TQRBZ
  [02:15:17] marketplace_agent -> 2 sellers, running_ads: False
  [02:15:17] discovery_agent -> category: Beauty, sub_category: Face Wash
  [02:15:18] listing_quality -> score: 9/10
  [02:15:19] weakness_agent -> 4 weakness bullets generated (rule-based)
  [02:15:20] excel -> saved row 2 to output.xlsx
  [02:15:20] markdown -> saved .\Mamaearth.md

  [02:15:20] DONE: Mamaearth
======================================================================
```

Note the `no product title rendered ... parsing what loaded` warnings that appear on some
runs — that's graceful degradation working: the page didn't fully render, the pipeline
logged it, extracted what it could, and carried on.

### Excel (`output.xlsx`)

| Brand Name | Category | Sub-Category | Portals Live | Running Ads | Listing Quality |
|---|---|---|---|---|---|
| Mamaearth | Beauty | Face Wash | Amazon | No | 9 |
| Biotique | Beauty | Moisturizers | Amazon | No | 8 |

(`Check Ratings`, `Sellers Name`, and `Weakness Report` columns omitted here for width —
see the file. Both rows were produced by separate runs, demonstrating append-only.)

### Markdown

See [`Mamaearth.md`](Mamaearth.md) and [`Biotique.md`](Biotique.md) — each covers brand
overview, product catalog, marketplace intelligence, the full listing quality audit
breakdown, and the weakness report.

---

## Requirements coverage

| Requirement | Status |
|---|---|
| Brand discovery + category/sub-category | Done |
| Up to 5 real product URLs, ranked by rating count | Done — every URL read off a real `href` |
| Rating counts, seller names, sponsored ads | Done |
| 5-dimension listing audit → 1–10 weighted score | Done (Data Accuracy capped, see limitation 2) |
| 4–6 bullet weakness report | Done — floor of 4 enforced in both LLM and fallback paths |
| Append-only styled Excel, 9 columns | Done |
| `<brand>.md` report | Done |
| Autonomous / resilient / no hallucination / logging / scalable | Done |
