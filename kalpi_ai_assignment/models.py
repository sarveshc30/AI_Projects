# file: models.py
"""Pydantic models for Kalpi Strategy Builder LLM outputs."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional

# Constants needed for validation
universes_constant = ["All Universe", "Nifty 500", 'Nifty 200', "Nifty 100", "Nifty 50", "Nifty Next 50", "Nifty Total Market",
             "Nifty Midcap 150", "Nifty Midcap 100", "Nifty Midcap 50", "Nifty Smallcap 250", "Nifty Smallcap 100",
             "Nifty Smallcap 50", "Nifty Microcap 250", "NIFTY MIDSMALLCAP 400", "Nifty LargeMidcap 250", "NIFTY FNO"]

# ============================================================================
# 1. CLARIFICATION NODE OUTPUT
# ============================================================================

class ClarificationOutput(BaseModel):
    """LLM decides if user input is sufficiently detailed."""
    decision: Literal["sufficient", "clarify"] = Field(
        ...,
        description="'sufficient' if input has enough detail, 'clarify' if more context needed"
    )
    question: Optional[str] = Field(
        None,
        description="Clarifying question to ask the user (null if decision is 'sufficient')"
    )
    
    @field_validator('question')
    def question_required_if_clarify(cls, v, info):
        if info.data.get('decision') == 'clarify' and not v:
            raise ValueError("'question' must be provided if decision is 'clarify'")
        if info.data.get('decision') == 'sufficient' and v:
            raise ValueError("'question' must be null if decision is 'sufficient'")
        return v


# ============================================================================
# 2. ENRICHMENT NODE OUTPUT (from take_input)
# ============================================================================

class EnrichedStrategyInput(BaseModel):
    """User input enriched into a structured strategy breakdown."""
    core_thesis: str = Field(
        ...,
        description="The market pattern or inefficiency this strategy exploits (1-2 sentences)"
    )
    target_stocks: str = Field(
        ...,
        description="Company characteristics: size, sector, liquidity, growth vs value (1-2 sentences)"
    )
    entry_criteria: str = Field(
        ...,
        description="Specific conditions stocks must meet; be quantitative (e.g., 'RSI 14 above 55', 'P/E below 20')"
    )
    ranking_logic: str = Field(
        ...,
        description="What separates best picks from merely eligible ones; list in priority order"
    )
    risk_profile: Literal["aggressive", "balanced", "conservative"] = Field(
        ...,
        description="Risk tolerance and volatility expectations"
    )
    holding_intent: Literal["short-term", "medium-term", "long-term"] = Field(
        ...,
        description="Holding period: short-term (days-weeks), medium (months), long (years+)"
    )


# ============================================================================
# 3. UNIVERSE NODE OUTPUT
# ============================================================================

class UniverseOutput(BaseModel):
    """LLM selects the stock universe."""
    universe: str = Field(
        ...,
        description="Exact universe name from the provided list (e.g., 'Nifty 50', 'Nifty 500')"
    )
    reasoning: str = Field(
        ...,
        description="1-2 sentences explaining why this universe fits the strategy"
    )
    
    @field_validator('universe')
    def validate_universe(cls, v):
        """Ensure universe is in the constants list."""
        if v not in universes_constant:
            # Case-insensitive recovery check
            for u in universes_constant:
                if u.lower() == v.lower():
                    return u
            raise ValueError(
                f"Universe '{v}' not in available universes. "
                f"Valid options: {universes_constant}"
            )
        return v


# ============================================================================
# 4. FILTER NODE OUTPUTS
# ============================================================================

class FilterMetricsSelectionOutput(BaseModel):
    """LLM selects which metrics to use as hard filters."""
    metrics: List[str] = Field(
        ...,
        description="3-8 metric names to use as filtration thresholds (exact names from list)"
    )
    reasoning: str = Field(
        ...,
        description="2-3 sentences explaining why these metrics are filtration candidates for the strategy"
    )
    
    @field_validator('metrics')
    def validate_metric_count(cls, v):
        if len(v) < 3 or len(v) > 8:
            raise ValueError(f"Must select 3-8 metrics; got {len(v)}")
        return v


class FilterConditionItem(BaseModel):
    """A single filter condition (metric threshold or metric-to-metric comparison)."""
    metric: str = Field(..., description="The metric being filtered")
    operator: Literal["<", ">", "<=", ">=", "=="] = Field(..., description="Comparison operator")
    compare_type: Literal["value", "metric"] = Field(..., description="Comparing to a static value or another metric")
    value: Optional[float] = Field(None, description="Static threshold value (required if compare_type='value')")
    compare_metric: Optional[str] = Field(None, description="Metric to compare against (required if compare_type='metric')")
    
    @field_validator('value', 'compare_metric')
    def validate_comparison(cls, v, info):
        compare_type = info.data.get('compare_type')
        if compare_type == 'value' and info.field_name == 'value':
            if v is None:
                raise ValueError("'value' must be provided if compare_type='value'")
        if compare_type == 'metric' and info.field_name == 'compare_metric':
            if not v:
                raise ValueError("'compare_metric' must be provided if compare_type='metric'")
        return v


class FilterConditionsOutput(BaseModel):
    """LLM assigns operators and thresholds to filter metrics."""
    filters: List[FilterConditionItem] = Field(
        ...,
        description="Array of filter conditions to apply"
    )


# ============================================================================
# 5. RANKING NODE OUTPUT
# ============================================================================

class RankingMetricsOutput(BaseModel):
    """LLM selects metrics for ranking/scoring stocks."""
    metrics: List[str] = Field(
        ...,
        description="2-8 metrics to rank stocks (exact names from list)"
    )
    reasoning: str = Field(
        ...,
        description="2-3 sentences explaining why these metrics rank stock quality for this strategy"
    )
    
    @field_validator('metrics')
    def validate_ranking_count(cls, v):
        if len(v) < 2 or len(v) > 8:
            raise ValueError(f"Must select 2-8 ranking metrics; got {len(v)}")
        return v


# ============================================================================
# 6. WEIGHTAGE NODE OUTPUTS
# ============================================================================

class WeightageDecisionOutput(BaseModel):
    """LLM decides how many stocks and how to weight them."""
    num_stocks: int = Field(
        ...,
        description="Number of top-ranked stocks to include in the portfolio",
        gt=0,
        le=500
    )
    weightage: Literal["equal", "metric"] = Field(
        ...,
        description="Weighting scheme: equal weight or based on a metric"
    )


class MetricWeightOutput(BaseModel):
    """LLM selects the metric to use for portfolio weighting."""
    metric: str = Field(
        ...,
        description="Metric to weight by (exact name from available metrics list)"
    )
    inverse: bool = Field(
        False,
        description="True if inverse relationship (lower metric value -> higher weight)"
    )


# ============================================================================
# 7. MODIFICATION NODE OUTPUT
# ============================================================================

class ModificationSectionsOutput(BaseModel):
    """LLM identifies which sections of the strategy need modification."""
    sections: List[Literal["universe", "filters", "ranking_metrics", "weight_metrics", "top_n"]] = Field(
        ...,
        description="List of strategy sections to modify"
    )


# ============================================================================
# 8. FINAL STRATEGY SERIALIZATION
# ============================================================================

class FinalStrategy(BaseModel):
    """The complete, approved strategy ready for export or execution."""
    universe: str
    filters: List[FilterConditionItem]
    ranking_metrics: List[str]
    weight_type: Literal["equal", "metric"]
    weight_metric: Optional[str] = None
    weight_metric_inverse: Optional[bool] = None
    top_n: int
    
    # Audit trail
    reasoning_universe: str
    reasoning_filters: str
    reasoning_ranking: str
    reasoning_weightage: str
    original_user_input: str
    enriched_input: str
    
    def to_json(self, filepath: str):
        """Serialize to JSON file."""
        import json
        with open(filepath, 'w') as f:
            f.write(self.model_dump_json(indent=2))
    
    @classmethod
    def from_json(cls, filepath: str):
        """Load from JSON file."""
        import json
        with open(filepath, 'r') as f:
            return cls(**json.load(f))
