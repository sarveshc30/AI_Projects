"""Pydantic schemas for every structured value the pipeline produces.

Keeping these in one place is what lets the LLM steps return validated objects
(via `with_structured_output`) instead of free-form text, and gives the Excel/Markdown
writers a stable contract to read from.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Assessment = Literal["GOOD", "MODERATE", "BAD"]
YesNo = Literal["YES", "NO"]


class ProductRecord(BaseModel):
    """One scraped Amazon product detail page."""

    url: str
    title: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    category_hierarchy: Optional[str] = None
    # The full breadcrumb as an ordered list, e.g.
    # ["Beauty", "Skin Care", "Face", "Creams & Moisturisers", "Moisturizers"].
    # category/sub_category above are just the first and last crumb; the tree is built
    # from these complete paths so the intermediate levels aren't lost.
    category_path: list[str] = Field(default_factory=list)
    rating_count: int = 0
    star_rating: Optional[float] = None
    seller_name: Optional[str] = None
    image_count: int = 0
    bullet_count: int = 0
    description_length: int = 0
    has_aplus_content: bool = False
    has_specifications: bool = False
    is_sponsored: bool = False


class BrandDiscovery(BaseModel):
    """Result of step 1 - is the brand on Amazon, and what does it sell?"""

    found_on_amazon: bool = False
    matched_brand: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None


class CategoryVerdict(BaseModel):
    """LLM-normalised category/sub-category for the brand as a whole."""

    category: str = Field(description="Top-level category, e.g. 'Beauty'")
    sub_category: str = Field(description="Specific sub-category, e.g. 'Face Wash'")


class CategoryNode(BaseModel):
    """One node in the brand's category tree, built from product breadcrumb paths.

    `product_count` is the number of scraped products whose breadcrumb passes through
    this node, so parents always total at least the sum of their children.
    """

    name: str
    product_count: int = 0
    children: list["CategoryNode"] = Field(default_factory=list)


class ListingQualityAudit(BaseModel):
    """The 5-dimension listing audit for the brand's top-rated product."""

    title_quality: Assessment = "BAD"
    title_includes_brand: YesNo = "NO"
    title_includes_subcategory: YesNo = "NO"
    title_word_count: int = 0

    visual_quality: Assessment = "BAD"
    image_count: int = 0

    content_richness: Assessment = "BAD"
    has_bullets: YesNo = "NO"
    has_description: YesNo = "NO"
    has_specifications: YesNo = "NO"
    has_aplus_content: YesNo = "NO"

    data_accuracy: Assessment = "BAD"
    pack_size_stated: YesNo = "NO"
    ingredients_listed: YesNo = "NO"

    social_proof: Assessment = "BAD"
    star_rating: Optional[float] = None
    rating_count: int = 0

    score: int = Field(default=0, ge=0, le=10)
    remark: str = ""


class WeaknessReport(BaseModel):
    """4-6 evidence-backed bullets."""

    bullets: list[str] = Field(default_factory=list)


class BrandReport(BaseModel):
    """Everything collected for one brand - the single object the writers consume."""

    brand_name: str
    found_on_amazon: bool = False
    category: str = ""
    sub_category: str = ""
    # Full breadcrumb hierarchy across every scraped product, not just the flat
    # category/sub_category pair the Excel schema asks for.
    category_tree: list[CategoryNode] = Field(default_factory=list)
    portals_live: list[str] = Field(default_factory=list)
    products: list[ProductRecord] = Field(default_factory=list)
    sellers: list[str] = Field(default_factory=list)
    # Tri-state on purpose. Amazon fills sponsored slots client-side and frequently
    # serves none at all to an automated session, so "we saw no ads" and "this brand runs
    # no ads" are different claims. None means not observable - recording it as False
    # would assert a fact the run never established.
    running_ads: Optional[bool] = None
    sponsored_products: list[str] = Field(default_factory=list)
    # True when the SERP carried ad scaffolding (sp_atf slots, /sspa/click redirects) but
    # none of the filled tiles belonged to this brand - i.e. ads were servable and the
    # brand simply wasn't running any. That makes a confident "No" defensible.
    ad_slots_served: bool = False
    audit: ListingQualityAudit = Field(default_factory=ListingQualityAudit)
    weaknesses: list[str] = Field(default_factory=list)

    @property
    def running_ads_label(self):
        """Yes / No / Unknown, for the Excel cell and the Markdown report."""
        if self.running_ads is None:
            return "Unknown"
        return "Yes" if self.running_ads else "No"

    @property
    def check_ratings_urls(self):
        """Product URLs with more than 100 customer ratings (the 'Check Ratings' column)."""
        return [p.url for p in self.products if p.rating_count > 100]

    @property
    def top_product(self):
        """Highest rating count, which is what the audit runs against."""
        return max(self.products, key=lambda p: p.rating_count, default=None)
