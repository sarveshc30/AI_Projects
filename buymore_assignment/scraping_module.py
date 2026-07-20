"""Amazon.in scraping layer.

Every function here is defensive: a failure returns an empty/default value and logs a
warning rather than raising, so the pipeline in main.py can always continue to the
Excel/Markdown writers (Non-Functional Requirement 2, graceful degradation).

No URL is ever constructed from an ASIN pattern - every product URL returned by this
module was read off a real href on a real scraped page (Non-Functional Requirement 3).
"""

import re
from difflib import get_close_matches
from random import randint
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from logger import log, warn
from schemas import ProductRecord

AMAZON = "https://www.amazon.in"

# A human lingers longer on a product page than on a results grid, so pace accordingly.
SEARCH_WAIT = (2000, 4000)
PRODUCT_WAIT = (4000, 8000)

SPONSORED_LABEL = "View Sponsored information or leave ad feedback"

# Amazon reshuffles class names periodically; the brand text has been stable at this
# combination, but callers treat a miss as "no brand on this tile" rather than an error.
BRAND_SELECTOR = "span.a-size-base-plus.a-color-base"
CARD_SELECTOR = "div.puis-card-container"
TITLE_SELECTOR = "a.s-line-clamp-3"


def rand_wait(wait_time=SEARCH_WAIT):
    return randint(wait_time[0], wait_time[1])


def _abs_url(href):
    return href if href.startswith("http") else f"{AMAZON}{href}"


def _clean_url(url):
    """Strip tracking query strings so the same product doesn't appear as two URLs."""
    match = re.search(r"(https://www\.amazon\.in)?(/[^?]*?/dp/[A-Z0-9]{10})", url)
    return f"{AMAZON}{match.group(2)}" if match else url.split("?")[0]


def _parse_int(text):
    match = re.search(r"[\d,]+", text or "")
    return int(match.group().replace(",", "")) if match else 0


# --------------------------------------------------------------------------- #
# Step 1 - search + brand discovery
# --------------------------------------------------------------------------- #

def open_search_page(page, brand, max_retries=3):
    """Search for the brand on Amazon.in. Returns the results page HTML, or None."""
    search_box = page.locator("#twotabsearchtextbox")
    for attempt in range(max_retries):
        try:
            # "load"/"domcontentloaded" wait for the whole tracker-heavy homepage and time
            # out intermittently even though it's visually ready; "commit" resolves as soon
            # as the response arrives, and the search_box wait gates on real usability.
            page.goto(AMAZON, wait_until="commit", timeout=30000)
            search_box.wait_for(state="visible", timeout=15000)
            break
        except Exception as e:
            warn("discovery_agent", f"search box not ready (attempt {attempt + 1}/{max_retries}): {e}")
            page.wait_for_timeout(rand_wait())
    else:
        warn("discovery_agent", "could not reach the Amazon search box")
        return None

    try:
        page.wait_for_timeout(rand_wait())
        search_box.fill(brand)
        page.wait_for_timeout(rand_wait())
        # The autocomplete grid occasionally swallows the Enter keypress and the press()
        # call hangs, so cap it and fall back to navigating the search URL directly.
        search_box.press("Enter", timeout=10000)
        page.wait_for_timeout(rand_wait())
        page.locator(BRAND_SELECTOR).first.wait_for(state="visible", timeout=20000)
        return page.content()
    except Exception as e:
        warn("discovery_agent", f"typed search failed ({e}); retrying via direct search URL")

    try:
        page.goto(f"{AMAZON}/s?k={quote_plus(brand)}", wait_until="commit", timeout=30000)
        page.locator(BRAND_SELECTOR).first.wait_for(state="visible", timeout=20000)
        page.wait_for_timeout(rand_wait())
        return page.content()
    except Exception as e:
        warn("discovery_agent", f"search results did not render: {e}")
        # Return whatever did load - partial HTML still beats nothing downstream.
        try:
            return page.content()
        except Exception:
            return None


def match_brand(search_html, brand):
    """Find the closest brand name among the result tiles."""
    if not search_html:
        return None
    soup = BeautifulSoup(search_html, "html.parser")
    brand_names = {span.get_text(strip=True) for span in soup.select(BRAND_SELECTOR)}
    brand_names.discard("")
    if not brand_names:
        return None
    matches = get_close_matches(brand, brand_names, n=1, cutoff=0.0)
    return matches[0] if matches else None


# --------------------------------------------------------------------------- #
# Step 2 - product URL extraction (real hrefs only, ranked by rating count)
# --------------------------------------------------------------------------- #

# Matches "57,812 ratings" but deliberately NOT "4.1 out of 5 stars, rating details" -
# both carry the word "rating", and matching the latter yields the star score (4) instead
# of the count, which silently corrupts the popularity ranking.
_RATING_COUNT_LABEL = re.compile(r"^([\d,]+)\s+ratings?$", re.IGNORECASE)


def _card_rating_count(card):
    """Rating count from a search tile, e.g. the '12,453' beside the stars."""
    for el in card.select("[aria-label]"):
        match = _RATING_COUNT_LABEL.match(el.get("aria-label", "").strip())
        if match:
            return int(match.group(1).replace(",", ""))

    # Fallback: the underlined review-count link next to the stars.
    el = card.select_one("span.a-size-base.s-underline-text")
    if el:
        return _parse_int(el.get_text())

    return 0


def extract_product_urls(search_html, matched_brand, limit=5):
    """Return up to `limit` real product URLs for the brand, most-rated first.

    Ranking by rating count (popularity), per Requirement 2. Sponsored tiles are kept -
    they're still real listings - but the sponsored flag travels with them.
    """
    if not search_html or not matched_brand:
        return []

    soup = BeautifulSoup(search_html, "html.parser")
    candidates = {}

    for card in soup.select(CARD_SELECTOR):
        brand_el = card.select_one(BRAND_SELECTOR)
        if not brand_el or brand_el.get_text(strip=True) != matched_brand:
            continue

        link = card.select_one(TITLE_SELECTOR) or card.select_one('a[href*="/dp/"]')
        href = link.get("href") if link else None
        if not href:
            continue

        url = _clean_url(_abs_url(href))
        # Sponsored tiles route through /sspa/click; if that redirect hides the real /dp/
        # path we can't verify the URL, so skip rather than reconstruct one.
        if "/dp/" not in url:
            continue

        rating_count = _card_rating_count(card)
        sponsored = _is_sponsored_card(card)

        existing = candidates.get(url)
        if existing:
            # Same product can appear as both a sponsored and an organic tile.
            existing["rating_count"] = max(existing["rating_count"], rating_count)
            existing["is_sponsored"] = existing["is_sponsored"] or sponsored
        else:
            candidates[url] = {
                "url": url,
                "rating_count": rating_count,
                "is_sponsored": sponsored,
            }

    ranked = sorted(candidates.values(), key=lambda c: c["rating_count"], reverse=True)
    return ranked[:limit]


# --------------------------------------------------------------------------- #
# Step 3 - sponsored ad detection
# --------------------------------------------------------------------------- #

def _is_sponsored_card(card):
    """Three independent sponsored signals - Amazon restyles the badge fairly often.

    1. The ad-feedback aria-label (most explicit)
    2. A literal "Sponsored" text badge
    3. An /sspa/click tracking redirect in the tile's href (most durable - Amazon changes
       the label markup more often than the redirect mechanism)
    """
    if card.find("span", attrs={"aria-label": SPONSORED_LABEL}):
        return True
    if card.find(string=lambda s: s and s.strip() == "Sponsored"):
        return True
    return any("/sspa/click" in (a.get("href") or "") for a in card.select("a[href]"))


def ad_slots_served(search_html):
    """Did Amazon actually serve any sponsored placements on this SERP, for any brand?

    This is what separates "the brand runs no ads" from "we couldn't see the ads".
    Sponsored slots are filled client-side by a separate ad call, and an automated or
    cookie-less session routinely gets zero fill while the organic results render
    perfectly normally - so an empty result is otherwise indistinguishable from a brand
    that genuinely doesn't advertise.

    Matching is deliberately brand-agnostic: if *anyone's* ad rendered, the ad pipeline
    worked, and a brand with no tiles of its own is a real negative.

    Note that Amazon ships the CSS that styles sponsored labels on every page whether or
    not ads are served, so the stylesheet is not evidence - only markers that appear in
    filled tiles count.
    """
    if not search_html:
        return False

    soup = BeautifulSoup(search_html, "html.parser")
    if soup.find("span", attrs={"aria-label": SPONSORED_LABEL}):
        return True
    if soup.select_one('a[href*="/sspa/click"]'):
        return True
    # sp_atf / sp_btf are the above/below-the-fold ad slot placement ids, present only
    # once a slot has been filled.
    return any(marker in search_html for marker in ("sp_atf", "sp_btf"))


def get_sponsored_products(search_html, matched_brand):
    """Names of the brand's own sponsored products on the search results page.

    Sponsored status is a property of how a listing appears in search results, not of the
    product detail page - so it has to be read here, off the SERP.
    """
    if not search_html or not matched_brand:
        return []

    soup = BeautifulSoup(search_html, "html.parser")
    cards = soup.select(CARD_SELECTOR)

    # Drop every tile that isn't the matched brand so only its products remain in the tree.
    for card in list(cards):
        brand_el = card.select_one(BRAND_SELECTOR)
        if not brand_el or brand_el.get_text(strip=True) != matched_brand:
            card.decompose()

    sponsored = []
    for card in soup.select(CARD_SELECTOR):
        if not _is_sponsored_card(card):
            continue
        title_el = card.select_one(TITLE_SELECTOR)
        if not title_el:
            continue
        # The brand sits in its own span and the rest of the title in the anchor.
        name = f"{matched_brand} {title_el.get_text(strip=True)}".strip()
        if name not in sponsored:
            sponsored.append(name)
    return sponsored


# --------------------------------------------------------------------------- #
# Step 3/4 - product detail page scraping
# --------------------------------------------------------------------------- #

def _breadcrumb_path(soup):
    """The product's full category breadcrumb, top-level first.

    e.g. ["Beauty", "Skin Care", "Face", "Creams & Moisturisers", "Moisturizers"]

    Only the real crumb links are picked up - the "›" separators are
    <li class="a-breadcrumb-divider"> with no <a>, so they drop out on their own and the
    remaining anchors are already in hierarchy order.
    """
    for selector in (
        "#wayfinding-breadcrumbs_feature_div ul.a-unordered-list a",
        "#wayfinding-breadcrumbs_feature_div a",
        # Some layouts render the trail outside the wayfinding wrapper.
        "#nav-subnav a.nav-a",
    ):
        crumbs = [
            text
            for el in soup.select(selector)
            if (text := el.get_text(strip=True)) and text != "›"
        ]
        # Collapse consecutive duplicates; the leaf crumb is sometimes repeated as the
        # aria-current="page" entry.
        deduped = [c for i, c in enumerate(crumbs) if i == 0 or c != crumbs[i - 1]]
        if deduped:
            return deduped
    return []


def scrape_product(context, url, rating_count_hint=0, is_sponsored=False):
    """Open a product page and pull every field the audit and Excel row need."""
    product_page = None
    record = ProductRecord(url=url, rating_count=rating_count_hint, is_sponsored=is_sponsored)
    try:
        product_page = context.new_page()
        product_page.goto(url, wait_until="commit", timeout=30000)
        try:
            product_page.locator("#productTitle").wait_for(state="attached", timeout=20000)
        except Exception:
            warn("marketplace_agent", f"no product title rendered for {url}; parsing what loaded")
        product_page.wait_for_timeout(rand_wait(PRODUCT_WAIT))

        soup = BeautifulSoup(product_page.content(), "html.parser")

        title_el = soup.select_one("#productTitle")
        record.title = title_el.get_text(strip=True) if title_el else None

        # #wayfinding-breadcrumbs_feature_div a picks up only the real crumb links; the
        # "›" separators are <li class="a-breadcrumb-divider"> with no <a>, so the full
        # path can be joined in order.
        crumbs = _breadcrumb_path(soup)
        if crumbs:
            record.category_path = crumbs
            record.category_hierarchy = " > ".join(crumbs)
            record.category = crumbs[0]
            record.sub_category = crumbs[-1]

        ratings_el = soup.select_one("#acrCustomerReviewText")
        if ratings_el:
            record.rating_count = _parse_int(ratings_el.get_text()) or rating_count_hint

        star_el = soup.select_one("#acrPopover")
        if star_el and star_el.get("title"):
            star_match = re.search(r"([\d.]+)", star_el["title"])
            if star_match:
                record.star_rating = float(star_match.group(1))

        seller_el = (
            soup.select_one("#sellerProfileTriggerId")
            or soup.select_one("#merchant-info a")
            or soup.select_one("#merchant-info")
        )
        if seller_el:
            seller = seller_el.get_text(strip=True)
            # #merchant-info sometimes carries a full sentence rather than just the name.
            record.seller_name = seller[:120] if seller else None

        # Thumbnail strip is the reliable image count; the main image alone is not.
        thumbs = soup.select("#altImages li.imageThumbnail, #altImages li.item")
        record.image_count = len(thumbs) if thumbs else (1 if soup.select_one("#landingImage") else 0)

        bullets = soup.select("#feature-bullets li span.a-list-item")
        record.bullet_count = len([b for b in bullets if b.get_text(strip=True)])

        desc_el = soup.select_one("#productDescription")
        record.description_length = len(desc_el.get_text(strip=True)) if desc_el else 0

        record.has_aplus_content = bool(soup.select_one("#aplus, #aplus_feature_div"))
        record.has_specifications = bool(
            soup.select_one("#productDetails_techSpec_section_1, #detailBullets_feature_div, #technicalSpecifications_feature_div")
        )

        log("marketplace_agent", f"{record.rating_count} ratings | seller: {record.seller_name} | {url}")
    except Exception as e:
        warn("marketplace_agent", f"failed to scrape {url}: {e}")
    finally:
        if product_page:
            try:
                product_page.close()
            except Exception:
                pass
    return record
