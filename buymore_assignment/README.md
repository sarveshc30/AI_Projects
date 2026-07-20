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
uv run main.py "Mamaearth" --headless        # hide the browser (see caveat below)
uv run main.py "Mamaearth" --excel out.xlsx  # write to a different workbook
```

**The browser runs headed by default, deliberately.** Amazon fills sponsored ad slots
client-side via a separate ad call that routinely returns nothing for an automated or
cookie-less session — the organic results still render perfectly, so the page looks
healthy while every ad is missing. A headless run of Mamaearth found 0 sponsored tiles;
the identical headed run found 8. `--headless` is available for CI or debugging, but ad
presence will usually come back `Unknown` rather than a usable Yes/No.

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
| Data Accuracy | 15% | pack size **and** ingredients stated in the listing text |
| Social Proof | 20% | ≥1,000 ratings **and** ≥4.0 stars |

`score = round(Σ(grade × weight) × 10)`, floored at 1. The LLM only writes the one-sentence
remark naming the weakest areas.

### Category footprint (full breadcrumb tree)

Amazon exposes a complete hierarchy per product — `Beauty › Skin Care › Face › Cleansing
Creams & Milks › Face Wash` — but the Excel schema only has room for a flat
Category/Sub-Category pair. Rather than discard the intermediate levels, every scraped
product's breadcrumb is merged into one tree, rendered in the Markdown report:

```
├── Beauty (4)
│   ├── Skin Care (2)
│   │   └── Face (2)
│   │       └── Cleansing Creams & Milks (2)
│   │           └── Face Wash (2)
│   └── Hair Care (2)
│       └── Shampoo & Conditioner (2)
│           └── Shampoos (2)
└── Baby (1)
    └── Baby Care (1)
        └── Skin Care (1)
            └── Lotions (1)
```

Bracketed numbers are how many sampled listings pass through that node; branches sort
busiest-first. In Excel, the `Category` column stacks every top-level category and
`Sub-Category` stacks every deepest-level leaf, one per line.

### Ad presence is tri-state (Yes / No / **Unknown**)

`Running Ads` is not a boolean, because "we saw no ads" and "this brand runs no ads" are
different claims and conflating them fabricates a finding:

| Situation | Value |
|---|---|
| Brand's own sponsored tiles found | `Yes` |
| No tiles for this brand, but **other brands' ads did serve** on the same page | `No` |
| No ads at all on the page, for anyone — the ad call didn't fill | `Unknown` |

The third case is decided by `scraping_module.ad_slots_served()`, which looks for ad
scaffolding brand-agnostically (`sp_atf`/`sp_btf` slot ids, `/sspa/click` redirects, the
ad-feedback `aria-label`). If *anyone's* ad rendered, the ad pipeline worked and an absent
brand is a real negative. Note that Amazon ships the CSS that styles sponsored labels on
every page whether or not ads serve, so the stylesheet is explicitly not treated as
evidence. The per-product `Sponsored` column in the Markdown catalog follows the same
three states.

### Guarding the LLM against methodology artefacts

The weakness report is the easiest place for the pipeline to invent findings, because an
LLM reads collection limits as if they were facts about the brand — "only 5 products found"
is `MAX_PRODUCTS`, not a narrow catalogue. Three guards:

- **`METHODOLOGY_CONSTRAINTS`** — an explicit block naming each artefact (the product cap,
  the unvisited portals, the sampled-only category tree, the absence of any spend data, the
  single-query ad snapshot) and forbidding its conversion into a weakness.
- **`_evidence_pack()`** — derived facts computed in Python that the model cannot work out
  from truncated titles: duplicate-ASIN groups, sponsored-vs-bestseller overlap, and review
  spread measured against the even-split baseline. Statistics carry their baseline, because
  "top listing holds 25% of review volume" reads as concentration until you notice that 5
  listings split evenly at 20%.
- **`NEUTRAL CONTEXT`** — purely descriptive facts are passed in a separate block so they
  aren't mistaken for defects. Selling across Beauty and Baby is a business model, not a
  weakness.

Where a value is unmeasured the prompt says so and bans hedged speculation about it, so an
unfilled ad slot cannot become "may indicate limited ad spend".

---

## Known limitations and trade-offs

1. **Amazon.in only.** The `Portals Live` column reports only Amazon because that's the
   only portal actually checked. Flipkart/Nykaa/quick-commerce are listed as *unverified*
   in the weakness report rather than asserted absent — claiming "not on Flipkart" without
   checking would be a fabricated finding.
2. **Data Accuracy only checks the text side.** The brief asks whether pack size and
   ingredients match *between text and images*. Verifying that needs OCR over product
   imagery, which isn't implemented — so the dimension confirms the values are *stated*,
   not that they agree with the packaging artwork. A listing could state "200 ml" in text
   while the image shows 100 ml and still score GOOD here.
3. **Seller ownership can't be determined from a listing.** A seller name that doesn't
   contain the brand is not proof of a third party — for Mamaearth, *Honasa Consumer
   Limited* is the parent company, and an authorised distributor looks identical to a
   grey-market reseller from the search page. The report states the name mismatch and marks
   ownership unverified. Real classification needs a seller-profile lookup or a
   brand→legal-entity mapping.
4. **Sponsored ads are session-dependent, and headless suppresses them entirely.** Ad
   placements vary by session, geography, and time of day. The detector checks three
   independent signals (ad-feedback `aria-label`, a literal "Sponsored" badge, and
   `/sspa/click` redirect hrefs); the positive path is confirmed on a live headed run
   (8 sponsored Mamaearth tiles), while the same brand headless returns 0. Hence the headed
   default and the third state — `No` means ads served but none were this brand's,
   `Unknown` means the measurement itself failed.
5. **Selectors are brittle by nature.** Amazon reshuffles CSS class hashes periodically.
   The scraper prefers stable signals (`aria-label`, element IDs like `#productTitle`,
   `/dp/` in hrefs) over class names where possible, and every extraction falls back to a
   default rather than raising — but a major Amazon redesign will still require updates.
6. **Rate limiting / bot detection.** Requests are paced with randomised delays (2–4s on
   search pages, 4–8s on product pages) and run serially in one browser context. This is
   adequate for occasional single-brand runs; a high-volume batch would need residential
   proxies and would likely hit CAPTCHAs.
7. **Top 5 products come from page one of search.** Ranking is by rating count as read off
   the search tiles, so a highly-rated product that doesn't surface on page one is missed.
   This cap also means the category tree shows only where those few listings sit, not the
   brand's full footprint — the LLM is explicitly told not to read it as catalogue size.
8. **Duplicate ASINs inflate the tree counts.** When one product is listed under several
   ASINs (Mamaearth's Onion Shampoo appears twice), the tree counts listings rather than
   distinct products. The duplication is itself surfaced as a weakness bullet, but the
   bracketed counts overstate breadth wherever it occurs.
9. **`gpt-oss-120b` is not a drop-in upgrade.** It's on the same free tier and is a stronger
   reasoner, but on Groq it fails `with_structured_output` — the API rejects the call with
   `tool_use_failed: model did not call a tool`, and the pipeline falls back to rule-based
   bullets. It would need JSON mode plus manual parsing, so `llama-3.3-70b-versatile` is the
   default.

---

## Sample output

### Console

```
======================================================================
  LEAD GEN AGENT  |  Brand: Mamaearth
  Started: 2026-07-20 08:52:47
======================================================================

  [08:52:48] llm -> Groq client ready (dual-key fallback enabled)
  [08:53:07] discovery_agent -> found on Amazon | matched brand: Mamaearth
  [08:53:10] url_extractor -> 5 amazon product URLs found
  [08:53:27] marketplace_agent -> 57813 ratings | seller: RK World Infocom Pvt Ltd | https://www.amazon.in/Mamaearth-Natural-Turmeric-Saffron-Removal/dp/B0FPWWH55W
  [08:53:42] marketplace_agent -> 57784 ratings | seller: Honasa Consumer Limited | https://www.amazon.in/Mamaearth-Shampoo-Growth-Control-Keratin/dp/B099F3WJKW
  [08:53:58] marketplace_agent -> 30637 ratings | seller: Honasa Consumer Limited | https://www.amazon.in/Mamaearth-Vitamin-Face-Turmeric-Illumination/dp/B08MF36S6C
  [08:54:14] marketplace_agent -> 28439 ratings | seller: RK World Infocom Pvt Ltd | https://www.amazon.in/Mamaearth-Daily-Moisturizing-Lotion-Babies/dp/B0774TQRBZ
  [08:54:34] marketplace_agent -> 2 sellers, running_ads: Yes
  [08:54:36] discovery_agent -> category: Beauty, sub_category: Face Wash
  [08:54:36] discovery_agent -> category tree (2 root(s), 3 leaf path(s) - Beauty, Baby):
      +-- Beauty (4)
      |   +-- Skin Care (2)
      |   |   `-- Face (2)
      |   |       `-- Cleansing Creams & Milks (2)
      |   |           `-- Face Wash (2)
      |   `-- Hair Care (2)
      |       `-- Shampoo & Conditioner (2)
      |           `-- Shampoos (2)
      `-- Baby (1)
          `-- Baby Care (1)
              `-- Skin Care (1)
                  `-- Lotions (1)
  [08:54:36] listing_quality -> score: 9/10
  [08:54:39] weakness_agent -> 6 weakness bullets generated
  [08:54:41] excel -> saved row 5 to output.xlsx
  [08:54:41] markdown -> saved .\Mamaearth.md

  [08:54:41] DONE: Mamaearth
======================================================================
```

The tree prints with ASCII connectors (`+--`) because Windows consoles default to cp1252
and can't encode box-drawing characters; the Markdown file is written UTF-8 and keeps the
real glyphs. All console output is sanitised against the terminal's actual encoding, so a
curly quote or non-breaking hyphen in an LLM error payload can't kill a run.

The `no product title rendered ... parsing what loaded` warnings that appear on some runs
are graceful degradation working: the page didn't fully render, the pipeline logged it,
extracted what it could, and carried on.

### Excel (`output.xlsx`)

| Brand Name | Category | Sub-Category | Portals Live | Running Ads | Listing Quality |
|---|---|---|---|---|---|
| Mamaearth | Beauty<br>Baby | Face Wash<br>Shampoos<br>Lotions | Amazon | Yes | 9 |
| Biotique | Beauty | Moisturizers | Amazon | No | 8 |

`Category` and `Sub-Category` are multi-line cells (wrap enabled): every top-level category
and every deepest-level sub-category found across the sampled products, one per line.

(`Check Ratings`, `Sellers Name`, and `Weakness Report` columns omitted here for width —
see the file. Rows were produced by separate runs, demonstrating append-only. Note that
`output.xlsx` cannot be open in Excel during a run — the file lock raises `PermissionError`,
which is caught and logged rather than crashing the pipeline, but the row won't be written.)

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
| Rating counts, seller names, sponsored ads | Done — ad presence is Yes/No/Unknown, never a guess |
| 5-dimension listing audit → 1–10 weighted score | Done (Data Accuracy is text-only, see limitation 2) |
| 4–6 bullet weakness report | Done — floor of 4 enforced in both LLM and fallback paths |
| Append-only styled Excel, 9 columns | Done |
| `<brand>.md` report | Done |
| Autonomous / resilient / no hallucination / logging / scalable | Done |
