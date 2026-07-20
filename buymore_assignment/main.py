"""E-Commerce Brand Intelligence Agent - CLI entry point.

Usage:
    uv run main.py "Mamaearth"              # headed (default)
    uv run main.py "Mamaearth" --headless   # hidden browser; ad detection degrades

Runs discovery -> URL extraction -> marketplace data collection -> listing audit ->
weakness synthesis -> Excel + Markdown output. Every stage degrades gracefully: a failure
logs a warning and the pipeline continues so a row is always written.
"""

import argparse
import sys

from playwright.sync_api import sync_playwright

import scraping_module as scraper
from analysis import (
    build_category_tree,
    build_weakness_report,
    render_category_tree,
    resolve_category,
)
from listing_audit import audit_listing
from llm import get_llm, llm_available
from logger import end_banner, log, log_block, start_banner, warn
from outputs import EXCEL_PATH, write_excel, write_markdown
from schemas import BrandReport

MAX_PRODUCTS = 5


def _init_llm():
    if not llm_available():
        warn("llm", "GROQ_API_KEY_1/GROQ_API_KEY_2 not set - falling back to rule-based analysis")
        return None
    try:
        llm = get_llm()
        log("llm", "Groq client ready (dual-key fallback enabled)")
        return llm
    except Exception as e:
        warn("llm", f"could not initialise Groq client, continuing rule-based: {e}")
        return None


def _tree_summary(nodes):
    """One-line shape of the category tree for the console log."""
    if not nodes:
        return "none"
    leaves = 0
    stack = list(nodes)
    while stack:
        node = stack.pop()
        if node.children:
            stack.extend(node.children)
        else:
            leaves += 1
    return f"{len(nodes)} root(s), {leaves} leaf path(s) - {', '.join(n.name for n in nodes)}"


def collect(brand, headless=False):
    """Scrape Amazon and return a populated BrandReport."""
    report = BrandReport(brand_name=brand)
    llm = _init_llm()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        # A single context across the whole run keeps cookies/session continuity, which
        # looks far more like a real visitor than repeatedly launching fresh browsers.
        context = browser.new_context(
            locale="en-IN",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()

        try:
            search_html = scraper.open_search_page(page, brand)
            matched_brand = scraper.match_brand(search_html, brand)

            if not matched_brand:
                warn("discovery_agent", f"'{brand}' not found on Amazon.in - writing default row")
                report.weaknesses = [
                    f"Brand '{brand}' returned no matching listings on Amazon.in - no marketplace "
                    "presence could be verified.",
                    "No product URLs, sellers, or rating data available for analysis.",
                    "No sponsored ad activity observable without a search presence.",
                    "Listing quality could not be scored (no listing to audit).",
                ]
                return report

            report.found_on_amazon = True
            report.portals_live = ["Amazon"]
            log("discovery_agent", f"found on Amazon | matched brand: {matched_brand}")

            # --- Step 2: real product URLs, ranked by rating count ---------
            candidates = scraper.extract_product_urls(search_html, matched_brand, limit=MAX_PRODUCTS)
            log("url_extractor", f"{len(candidates)} amazon product URLs found")

            # --- Step 3: sponsored ads (a SERP property, not a product-page one) ---
            report.sponsored_products = scraper.get_sponsored_products(search_html, matched_brand)
            report.ad_slots_served = scraper.ad_slots_served(search_html)
            if report.sponsored_products:
                report.running_ads = True
            elif report.ad_slots_served:
                # Ads rendered for other brands, so this brand genuinely isn't bidding.
                report.running_ads = False
            else:
                # Not a single ad on the page for anyone - the ad call didn't fill, so we
                # learned nothing about this brand either way.
                report.running_ads = None
                warn(
                    "marketplace_agent",
                    "no sponsored slots filled for any brand - ad presence is Unknown, "
                    "not No (retry headed if this matters)",
                )

            # --- Step 3: per-product marketplace data ----------------------
            for candidate in candidates:
                record = scraper.scrape_product(
                    context,
                    candidate["url"],
                    rating_count_hint=candidate["rating_count"],
                    is_sponsored=candidate["is_sponsored"],
                )
                report.products.append(record)
                page.wait_for_timeout(scraper.rand_wait())

            # Deduplicate sellers while preserving discovery order.
            seen = set()
            for record in report.products:
                if record.seller_name and record.seller_name not in seen:
                    seen.add(record.seller_name)
                    report.sellers.append(record.seller_name)

            log(
                "marketplace_agent",
                f"{len(report.sellers)} sellers, running_ads: {report.running_ads_label}",
            )

            # --- Step 1 (cont.): brand-level category ----------------------
            report.category_tree = build_category_tree(report.products)
            report.category, report.sub_category = resolve_category(report.products, brand, llm)
            log(
                "discovery_agent",
                f"category: {report.category or 'unknown'}, sub_category: {report.sub_category or 'unknown'}",
            )
            log_block(
                "discovery_agent",
                f"category tree ({_tree_summary(report.category_tree)}):",
                render_category_tree(report.category_tree),
            )

            # --- Step 4: listing quality audit on the top-rated product ----
            report.audit = audit_listing(report.top_product, brand, report.sub_category, llm)

        except Exception as e:
            warn("pipeline", f"unrecoverable scraping error, continuing with partial data: {e}")
        finally:
            try:
                browser.close()
            except Exception:
                pass

    # --- Step 5: weakness synthesis ------------------------------------
    report.weaknesses = build_weakness_report(report, llm)
    return report


def main():
    parser = argparse.ArgumentParser(description="E-Commerce Brand Intelligence Agent")
    parser.add_argument("brand", help='Brand name to research, e.g. "Mamaearth"')
    parser.add_argument(
        "--headless",
        action="store_true",
        help=(
            "Run the browser hidden. Off by default: Amazon fills sponsored ad slots "
            "client-side and routinely serves none to a headless session, which makes "
            "'Running Ads' read Unknown instead of a usable Yes/No."
        ),
    )
    parser.add_argument("--excel", default=EXCEL_PATH, help="Excel file to append to")
    args = parser.parse_args()

    brand = args.brand.strip()
    if not brand:
        parser.error("brand name cannot be empty")

    start_banner(brand)
    ok = True
    try:
        report = collect(brand, headless=args.headless)
    except Exception as e:
        warn("pipeline", f"pipeline crashed: {e}")
        report = BrandReport(brand_name=brand)
        report.weaknesses = [f"Run failed before data collection completed: {e}"]
        ok = False

    ok = write_excel(report, args.excel) and ok
    ok = write_markdown(report) and ok
    end_banner(brand, ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
