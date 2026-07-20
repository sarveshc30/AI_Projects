"""LLM-backed synthesis steps: brand category normalisation and the weakness report.

Both have deterministic fallbacks so the pipeline still produces a complete row when the
Groq keys are missing or the API is unreachable.
"""

from collections import Counter

from logger import log, warn
from schemas import CategoryNode, CategoryVerdict, WeaknessReport

# Portals the brief asks about; only Amazon is actually checked by this implementation.
ALL_PORTALS = ["Amazon", "Flipkart", "Nykaa", "Blinkit", "Zepto"]


def build_category_tree(products):
    """Merge every product's breadcrumb path into one tree of the brand's categories.

    Amazon exposes the full hierarchy per product (Beauty > Skin Care > Face > ...), so
    merging the paths shows the whole footprint rather than the single flat
    category/sub-category pair the Excel schema is limited to.

    Children keep first-seen order, and each node counts the products passing through it.
    """
    roots = []

    for product in products:
        if not product.category_path:
            continue
        siblings = roots
        for crumb in product.category_path:
            node = next((n for n in siblings if n.name == crumb), None)
            if node is None:
                node = CategoryNode(name=crumb)
                siblings.append(node)
            node.product_count += 1
            siblings = node.children

    # Busiest branch first, so the brand's primary line of business reads at the top.
    def sort_nodes(nodes):
        nodes.sort(key=lambda n: -n.product_count)
        for node in nodes:
            sort_nodes(node.children)

    sort_nodes(roots)
    return roots


def render_category_tree(nodes, prefix=""):
    """ASCII tree lines for the Markdown report."""
    lines = []
    for i, node in enumerate(nodes):
        last = i == len(nodes) - 1
        lines.append(f"{prefix}{'└── ' if last else '├── '}{node.name} ({node.product_count})")
        lines += render_category_tree(node.children, prefix + ("    " if last else "│   "))
    return lines


def resolve_category(products, brand, llm=None):
    """Collapse per-product breadcrumbs into one brand-level category / sub-category."""
    categories = [p.category for p in products if p.category]
    sub_categories = [p.sub_category for p in products if p.sub_category]

    fallback_cat = Counter(categories).most_common(1)[0][0] if categories else ""
    fallback_sub = Counter(sub_categories).most_common(1)[0][0] if sub_categories else ""

    if llm is None or not (categories or sub_categories):
        return fallback_cat, fallback_sub

    try:
        titles = [p.title for p in products if p.title][:5]
        prompt = (
            "Given Amazon.in breadcrumb data for a brand's products, state the single "
            "top-level category and the single most representative sub-category the brand "
            "primarily operates in. Use short retail terms (e.g. 'Beauty' / 'Face Wash'). "
            "Base your answer only on the data given.\n\n"
            f"Brand: {brand}\n"
            f"Breadcrumb categories: {categories}\n"
            f"Breadcrumb sub-categories: {sub_categories}\n"
            f"Product titles: {titles}"
        )
        verdict = llm.with_structured_output(CategoryVerdict).invoke([("human", prompt)])
        return verdict.category, verdict.sub_category
    except Exception as e:
        warn("discovery_agent", f"LLM category resolution failed, using breadcrumb mode: {e}")
        return fallback_cat, fallback_sub


def _fallback_weaknesses(report):
    """Deterministic, evidence-cited bullets used when the LLM is unavailable."""
    bullets = []

    missing = [p for p in ALL_PORTALS if p not in report.portals_live]
    if missing:
        bullets.append(
            f"Portal gap: brand verified only on {', '.join(report.portals_live) or 'no portal'}; "
            f"not checked/found on {', '.join(missing)} - unverified reach on those channels."
        )

    top = report.top_product
    if top and top.title:
        word_count = len(top.title.split())
        if word_count < 8:
            bullets.append(
                f"Listing deficiency: top product title is only {word_count} words - below the "
                "recommended 8+ for search relevance."
            )

    if top and top.image_count < 6:
        bullets.append(
            f"Visual gap: top listing carries {top.image_count} image(s); listings with 6+ images "
            "convert better and reduce returns."
        )

    for group in _duplicate_listings(report.products):
        asins = ", ".join(p.url.rsplit("/", 1)[-1] for p in group)
        bullets.append(
            f"Duplicate listings: {len(group)} separate ASINs ({asins}) sell the same product, "
            "splitting reviews and sales rank between them - consolidate into one ASIN or set "
            "them up as variations of a single parent."
        )
        break  # One duplicate bullet is enough; the rest are the same finding.

    # A seller name that doesn't contain the brand is not proof of a third party - it could
    # be the brand's own parent company or an authorised distributor. State what was seen.
    unmatched = [s for s in report.sellers if report.brand_name.lower() not in s.lower()]
    if unmatched:
        bullets.append(
            f"Buy Box control unverified: {len(unmatched)} of {len(report.sellers)} seller(s) "
            f"({', '.join(unmatched[:3])}) do not carry the brand name in their storefront - "
            "confirm which are brand-owned or authorised before treating the Buy Box as controlled."
        )

    if report.running_ads is True:
        bullets.append(
            f"Ad spend is active ({len(report.sponsored_products)} sponsored listing(s) seen), so "
            "measure ACoS against the organic ranking of the same ASINs to check for cannibalisation."
        )
    elif report.running_ads is False:
        bullets.append(
            "Visibility issue: no sponsored ads detected on Amazon search results, while other "
            "brands' ads did serve on the same page - this brand is relying entirely on organic "
            "ranking and is losing the paid slots to competitors."
        )
    else:
        # Unknown. Stating "no ads" here would invent a finding the run never observed.
        bullets.append(
            "Ad presence could not be verified: Amazon served no sponsored slots to this session "
            "for any brand, so paid activity is unmeasured - re-run headed before treating "
            "advertising as a gap."
        )

    if report.audit.score and report.audit.score < 7:
        bullets.append(
            f"Listing quality scored {report.audit.score}/10 - {report.audit.remark}"
        )

    # The brief mandates 4-6 bullets, so top up with lower-priority observations when a
    # brand happens to look healthy on the checks above.
    for extra in _padding_bullets(report):
        if len(bullets) >= 4:
            break
        if extra not in bullets:
            bullets.append(extra)

    return bullets[:6]


def _padding_bullets(report):
    """Lower-priority but still evidence-backed observations, used to reach the 4-bullet floor."""
    extras = []
    thin = [p for p in report.products if p.rating_count <= 100]
    if thin:
        extras.append(
            f"Catalog depth risk: {len(thin)} of {len(report.products)} discovered listings have "
            "100 or fewer ratings, so review volume is concentrated in a few hero SKUs."
        )
    if len(report.sellers) <= 1:
        extras.append(
            f"Seller concentration: only {len(report.sellers)} seller found across the sampled "
            "listings - a single point of failure for stock and Buy Box control."
        )
    if report.audit.score >= 7:
        extras.append(
            f"Listing scored {report.audit.score}/10 but is not maximal - {report.audit.remark}"
        )
    # Deliberately no "few products found" bullet here. The sample size is set by the
    # scraper's cap, so it says nothing about the brand's catalogue.
    extras.append(
        "Competitive benchmarking is absent: no share-of-voice comparison against rival brands "
        "in the same sub-category was possible from search data alone."
    )
    extras.append(
        "Cross-portal reach is unmeasured: this run only visited Amazon.in, so presence on "
        "Flipkart, Nykaa and quick-commerce apps is unknown and needs a separate check."
    )
    return extras


def _duplicate_listings(products):
    """Groups of separate ASINs selling what looks like the same product.

    Amazon lets a brand (or its resellers) list one product under several ASINs. That
    splits reviews across duplicates and makes the listings compete with each other, so
    it is a genuine, actionable weakness - and one the LLM cannot spot unless the
    comparison is done here, because it only sees truncated titles.
    """
    groups = {}
    for product in products:
        if not product.title:
            continue
        # Titles are near-identical across duplicate ASINs; the leading chunk is enough
        # to group them without matching unrelated products in the same range.
        key = " ".join(product.title.lower().split())[:60]
        groups.setdefault(key, []).append(product)
    return [group for group in groups.values() if len(group) > 1]


def _evidence_pack(report):
    """Facts derived from the collected data that the raw fields don't state outright.

    Everything here is computed from what was actually scraped - no estimates - and is
    fed to the LLM so its bullets can rest on real comparisons rather than on the shape
    of our own sampling.
    """
    facts = []

    duplicates = _duplicate_listings(report.products)
    for group in duplicates:
        asins = ", ".join(p.url.rsplit("/", 1)[-1] for p in group)
        facts.append(
            f"DUPLICATE LISTING: {len(group)} separate ASINs ({asins}) carry what appears to be "
            f"the same product ('{(group[0].title or '')[:60]}'). Reviews and sales rank are "
            "split across them and they compete for the same Buy Box."
        )

    # Which SKUs get ad spend vs which SKUs actually sell.
    if report.sponsored_products and report.products:
        catalog_keys = {
            " ".join((p.title or "").lower().split())[:40] for p in report.products if p.title
        }
        overlap = [
            name
            for name in report.sponsored_products
            if " ".join(name.lower().split())[:40] in catalog_keys
        ]
        facts.append(
            f"AD TARGETING: {len(overlap)} of the {len(report.sponsored_products)} sponsored SKUs "
            f"also appear among the {len(report.products)} highest-rated listings. "
            + (
                "Ad spend is going almost entirely to SKUs that are not the brand's proven "
                "bestsellers, so the hero products are undefended on the brand's own query."
                if not overlap
                else "Ad spend overlaps the bestsellers, which risks paying for traffic that "
                "would have converted organically."
            )
        )

    # Sellers whose name doesn't match the brand. Deliberately not called "third-party":
    # corporate ownership isn't visible on a listing (a parent company or an authorised
    # distributor both look like a stranger here), and asserting otherwise invents a fact.
    unmatched = [s for s in report.sellers if report.brand_name.lower() not in s.lower()]
    if unmatched:
        facts.append(
            f"SELLER NAMES: {len(unmatched)} of {len(report.sellers)} seller(s) do not carry the "
            f"brand name ({', '.join(unmatched)}). Whether these are the brand's own corporate "
            "entity, an authorised distributor, or an unauthorised reseller CANNOT be determined "
            "from the listing - do not assert which without evidence."
        )

    # Review concentration is only meaningful against the even-split baseline. Stating a
    # bare "top listing holds 25%" reads as concentration when 5 listings split evenly at
    # 20% - both models tested turned that into a false "heavily concentrated" finding.
    rated = [p.rating_count for p in report.products if p.rating_count]
    if len(rated) > 1:
        share = max(rated) / sum(rated)
        even = 1 / len(rated)
        gap = share - even
        if gap > 0.15:
            facts.append(
                f"REVIEW CONCENTRATION: the top listing holds {share:.0%} of sampled review "
                f"volume against an even split of {even:.0%} across {len(rated)} listings - "
                f"{gap * 100:.0f} points above even, so social proof really is concentrated "
                "in one hero SKU."
            )
        else:
            facts.append(
                f"REVIEW SPREAD (NOT a weakness): the top listing holds {share:.0%} of sampled "
                f"review volume against an even split of {even:.0%} - only {gap * 100:.0f} "
                "points above even, so review volume is well distributed. Do NOT describe this "
                "as concentrated or uneven."
            )

    return facts


def _neutral_context(report):
    """Descriptive facts that are NOT weaknesses.

    These are given to the model as background only. Listing them alongside the evidence
    invites it to manufacture a defect - "spans 2 categories" became "lack of focus" in a
    previous run, when selling across Beauty and Baby is simply the brand's business model.
    """
    context = []
    if report.category_tree:
        roots = [n.name for n in report.category_tree]
        context.append(
            f"The sampled products span {len(roots)} top-level "
            f"{'category' if len(roots) == 1 else 'categories'} ({', '.join(roots)}). "
            "Operating across several categories is normal for a diversified brand and is "
            "NOT by itself a weakness."
        )
    if report.audit.score >= 8:
        context.append(
            f"The audited listing scored {report.audit.score}/10, which is strong. Do not "
            "manufacture a criticism of it merely because the score is short of 10."
        )
    return context


# Limits of our own collection method. These describe the scraper, not the brand, and the
# model must never convert them into findings - that is exactly how "only 5 products found"
# became a "low product diversity" weakness.
METHODOLOGY_CONSTRAINTS = """\
METHODOLOGY CONSTRAINTS - read carefully. The following are artefacts of how this data was
collected. They are NOT facts about the brand and MUST NOT appear as weaknesses:

1. PRODUCT COUNT IS A HARD CAP. The scraper deliberately keeps only the top {max_products}
   listings by rating count from page one of a single search. The brand's real catalogue is
   very likely far larger. Never write that the brand has few products, a narrow range, low
   diversity, or limited shelf space based on this number.
2. ONLY AMAZON.IN WAS CHECKED. No other marketplace was visited at all. "Portals not
   verified" means NOT LOOKED AT - it does not mean the brand is absent there. Never claim
   the brand is missing from, or has no presence on, any other portal.
3. CATEGORY DATA COMES FROM THE SAMPLED PRODUCTS ONLY. The category tree reflects where
   those few listings sit, not the brand's full category footprint.
4. NO SPEND OR PERFORMANCE DATA EXISTS. There is no ACoS, budget, impression share,
   conversion rate, or margin figure anywhere in this data. Never describe advertising as
   heavy, costly, unsustainable, over-reliant, or inefficient - the count of sponsored
   listings says an ad is running, nothing about how much is being spent or whether it pays.
5. THE AD SNAPSHOT IS ONE QUERY AT ONE MOMENT. Sponsored placements rotate per session and
   per query, so this is a sample of ad activity, not a full picture of it.

Write about what the data DOES show. If a genuine weakness is not supported by the evidence
below, write fewer bullets rather than inventing one.\
"""


def build_weakness_report(report, llm=None):
    """Produce 4-6 evidence-backed weakness bullets."""
    fallback = _fallback_weaknesses(report)

    if llm is None:
        log("weakness_agent", f"{len(fallback)} weakness bullets generated (rule-based)")
        return fallback

    top = report.top_product

    # Spelling out what Unknown means keeps the model from turning "no ads were seen" into
    # a confident "this brand does not advertise" bullet.
    ads_note = ""
    if report.running_ads is None:
        # Hedged speculation is the failure mode here: a previous run obeyed "don't say
        # they run no ads" and then wrote "may indicate a lack of investment in
        # advertising" - the same false claim wearing a hedge. The brand demonstrably was
        # advertising; the ad server just returned nothing to an automated session.
        ads_note = (
            "IMPORTANT - AD PRESENCE IS UNKNOWN, NOT ZERO. Amazon served no sponsored slots "
            "to this session for ANY brand, which means the measurement failed. It is NOT "
            "evidence about this brand. You must not:\n"
            "  - claim or imply the brand runs no ads, few ads, or has gaps in advertising;\n"
            "  - speculate about WHY none were seen (no 'may indicate a lack of investment', "
            "'suggests limited ad spend', 'possible under-investment' or any hedged variant);\n"
            "  - recommend increasing ad spend, since current spend is unmeasured.\n"
            "The only acceptable framing is that ad presence could not be measured on this "
            "run and needs re-checking. Prefer writing about a different weakness entirely.\n"
        )

    evidence = _evidence_pack(report)
    not_visited = [p for p in ALL_PORTALS if p not in report.portals_live]

    try:
        prompt = (
            "You are an e-commerce brand analyst. Write 4 to 6 weakness bullets for this brand's "
            "Amazon.in presence. Every bullet MUST cite specific evidence from the data below and "
            "state a concrete action. Do not invent any number or fact not present here.\n\n"
            + METHODOLOGY_CONSTRAINTS.format(max_products=len(report.products))
            + "\n\n--- COLLECTED DATA ---\n"
            f"Brand: {report.brand_name}\n"
            f"Primary category: {report.category} > {report.sub_category}\n"
            f"Portals confirmed live: {report.portals_live}\n"
            f"Portals NOT VISITED by this run (absence is unknown, not proven): {not_visited}\n"
            f"Listings sampled (capped by the scraper, not the brand's catalogue size): "
            f"{len(report.products)}\n"
            f"Sellers seen on those listings: {report.sellers}\n"
            f"Running sponsored ads: {report.running_ads_label} "
            f"({len(report.sponsored_products)} sponsored listings seen on page one)\n"
            f"{ads_note}"
            f"Listing quality score: {report.audit.score}/10\n"
            f"Audit detail: title words={report.audit.title_word_count}, "
            f"images={report.audit.image_count}, bullets={report.audit.has_bullets}, "
            f"description={report.audit.has_description}, A+={report.audit.has_aplus_content}, "
            f"stars={report.audit.star_rating}, ratings={report.audit.rating_count}\n"
            f"Top product title: {top.title if top else 'n/a'}\n"
            "\n--- DERIVED EVIDENCE (computed from the scraped pages; prefer these) ---\n"
            + ("\n".join(f"- {fact}" for fact in evidence) or "- none")
            + "\n\n--- NEUTRAL CONTEXT (background only - these are NOT weaknesses) ---\n"
            + ("\n".join(f"- {item}" for item in _neutral_context(report)) or "- none")
            + "\n\nPrioritise the DERIVED EVIDENCE above: those are concrete, verified problems. "
            "Weaker, more generic observations should only fill the remaining bullets. "
            "Never turn an item from NEUTRAL CONTEXT into a weakness."
        )
        result = llm.with_structured_output(WeaknessReport).invoke([("human", prompt)])
        bullets = [b.strip() for b in result.bullets if b and b.strip()]
        if len(bullets) < 4:
            warn("weakness_agent", f"LLM returned {len(bullets)} bullets; topping up from rule-based set")
            for b in fallback:
                if len(bullets) >= 4:
                    break
                if b not in bullets:
                    bullets.append(b)
        bullets = bullets[:6]
        log("weakness_agent", f"{len(bullets)} weakness bullets generated")
        return bullets
    except Exception as e:
        warn("weakness_agent", f"LLM weakness report failed, using rule-based bullets: {e}")
        log("weakness_agent", f"{len(fallback)} weakness bullets generated (rule-based)")
        return fallback
