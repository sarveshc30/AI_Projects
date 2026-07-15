# file: screening/schemas.py
"""Request/response models for the live stock screening endpoint.

Kept separate from the project's top-level models.py, which is specifically
LLM structured-output schemas.
"""

from pydantic import BaseModel
from typing import Optional, Literal


class ScreenRequest(BaseModel):
    session_id: str


class SkippedMetric(BaseModel):
    metric: str
    reason: str
    scope: Literal["global", "near_unsupported"]


class FailedTicker(BaseModel):
    ticker: str
    reason: str


class ScreenedStock(BaseModel):
    ticker: str
    symbol: str
    company_name: str
    rank: int
    composite_score: float
    weight_pct: float
    filter_values: dict[str, Optional[float]]
    ranking_values: dict[str, Optional[float]]
    weight_metric_value: Optional[float] = None
    missing_metrics: list[str] = []


class ScreenResult(BaseModel):
    success: bool
    message: Optional[str] = None
    universe: str
    universe_total_tickers: int
    universe_screened_tickers: int
    universe_truncated: bool
    eligible_count: int
    selected_count: int
    requested_top_n: int
    weight_type: str
    weight_metric: Optional[str] = None
    results: list[ScreenedStock] = []
    skipped_metrics: list[SkippedMetric] = []
    failed_tickers: list[FailedTicker] = []
    data_quality_warning: Optional[str] = None
    fetched_at: str
