"""Listing quality audit - the 5-dimension evaluation from Requirement 4.

The dimension assessments and the 1-10 score are computed deterministically from scraped
fields so the number is reproducible and auditable; the LLM is used only for the free-text
remark that names the weakest areas.
"""

from logger import log, warn
from schemas import ListingQualityAudit

# Weights sum to 1.0; each dimension contributes its share of the final 10 points.
WEIGHTS = {
    "title": 0.20,
    "visual": 0.20,
    "content": 0.25,
    "accuracy": 0.15,
    "social": 0.20,
}

_ASSESSMENT_VALUE = {"GOOD": 1.0, "MODERATE": 0.5, "BAD": 0.0}

# Rough pack-size markers: "100g", "200 ml", "2 x 50 g", "500gm".
_PACK_SIZE_PATTERN = r"\d+\s*(?:g|gm|gms|kg|ml|l|litre|liter|oz|pcs|pack|n)\b"


def _yn(condition):
    return "YES" if condition else "NO"


def _grade(good, moderate):
    if good:
        return "GOOD"
    return "MODERATE" if moderate else "BAD"


def audit_listing(product, brand, sub_category, llm=None):
    """Score one product's listing across the 5 dimensions."""
    import re

    audit = ListingQualityAudit()
    if product is None:
        warn("listing_quality", "no product available to audit; scoring 0")
        audit.remark = "No product page could be scraped, so no listing audit was possible."
        return audit

    title = product.title or ""
    title_lower = title.lower()
    words = [w for w in title.split() if w.strip()]

    # --- Title quality -----------------------------------------------------
    audit.title_word_count = len(words)
    audit.title_includes_brand = _yn(brand.lower() in title_lower)
    audit.title_includes_subcategory = _yn(
        bool(sub_category) and any(tok in title_lower for tok in sub_category.lower().split())
    )
    title_ok = audit.title_word_count >= 8
    audit.title_quality = _grade(
        title_ok and audit.title_includes_brand == "YES" and audit.title_includes_subcategory == "YES",
        title_ok or audit.title_includes_brand == "YES",
    )

    # --- Visual quality ----------------------------------------------------
    audit.image_count = product.image_count
    audit.visual_quality = _grade(product.image_count >= 6, product.image_count >= 3)

    # --- Content richness --------------------------------------------------
    audit.has_bullets = _yn(product.bullet_count >= 3)
    audit.has_description = _yn(product.description_length >= 200)
    audit.has_specifications = _yn(product.has_specifications)
    audit.has_aplus_content = _yn(product.has_aplus_content)
    content_hits = sum(
        1
        for v in (audit.has_bullets, audit.has_description, audit.has_specifications, audit.has_aplus_content)
        if v == "YES"
    )
    audit.content_richness = _grade(content_hits >= 3, content_hits >= 2)

    # --- Data accuracy -----------------------------------------------------
    # We verify the text side only (no OCR on the images), so this checks that pack size
    # and ingredients are *stated*, not that they match the packaging artwork.
    #
    # Previously both the 1-hit and 2-hit branches returned MODERATE, making GOOD
    # unreachable. That capped every possible listing at 9/10 and put "Data Accuracy" in
    # the weak-dimensions list forever, so the audit remark described this scoring code
    # rather than the listing. Both signals present now scores GOOD.
    audit.pack_size_stated = _yn(bool(re.search(_PACK_SIZE_PATTERN, title_lower)))
    audit.ingredients_listed = _yn("ingredient" in title_lower or product.bullet_count >= 3)
    accuracy_hits = sum(1 for v in (audit.pack_size_stated, audit.ingredients_listed) if v == "YES")
    audit.data_accuracy = _grade(accuracy_hits == 2, accuracy_hits == 1)

    # --- Social proof ------------------------------------------------------
    audit.star_rating = product.star_rating
    audit.rating_count = product.rating_count
    strong = product.rating_count >= 1000 and (product.star_rating or 0) >= 4.0
    decent = product.rating_count >= 100
    audit.social_proof = _grade(strong, decent)

    # --- Weighted score ----------------------------------------------------
    weighted = (
        _ASSESSMENT_VALUE[audit.title_quality] * WEIGHTS["title"]
        + _ASSESSMENT_VALUE[audit.visual_quality] * WEIGHTS["visual"]
        + _ASSESSMENT_VALUE[audit.content_richness] * WEIGHTS["content"]
        + _ASSESSMENT_VALUE[audit.data_accuracy] * WEIGHTS["accuracy"]
        + _ASSESSMENT_VALUE[audit.social_proof] * WEIGHTS["social"]
    )
    audit.score = max(1, round(weighted * 10))

    audit.remark = _build_remark(audit, llm, brand)
    log("listing_quality", f"score: {audit.score}/10")
    return audit


def _weak_dimensions(audit):
    pairs = [
        ("Title Quality", audit.title_quality),
        ("Visual Quality", audit.visual_quality),
        ("Content Richness", audit.content_richness),
        ("Data Accuracy", audit.data_accuracy),
        ("Social Proof", audit.social_proof),
    ]
    return [name for name, value in pairs if value != "GOOD"]


def _build_remark(audit, llm, brand):
    weak = _weak_dimensions(audit)
    fallback = (
        f"Scored {audit.score}/10. Weakest areas: {', '.join(weak)}."
        if weak
        else f"Scored {audit.score}/10. All five dimensions assessed GOOD."
    )
    if llm is None:
        return fallback

    try:
        prompt = (
            "You are auditing an Amazon.in product listing. Write ONE sentence (max 40 words) "
            "naming the listing's weakest areas and why. Be specific and factual; do not invent data.\n\n"
            f"Brand: {brand}\n"
            f"Score: {audit.score}/10\n"
            f"Title words: {audit.title_word_count}, includes brand: {audit.title_includes_brand}, "
            f"includes sub-category: {audit.title_includes_subcategory}\n"
            f"Images: {audit.image_count}\n"
            f"Bullets: {audit.has_bullets}, description: {audit.has_description}, "
            f"specs: {audit.has_specifications}, A+: {audit.has_aplus_content}\n"
            f"Star rating: {audit.star_rating}, rating count: {audit.rating_count}\n"
            f"Dimensions below GOOD: {', '.join(weak) if weak else 'none'}"
        )
        return llm.invoke([("human", prompt)]).content.strip()
    except Exception as e:
        warn("listing_quality", f"LLM remark failed, using computed summary: {e}")
        return fallback
