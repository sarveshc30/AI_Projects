# file: screening/metric_registry.py
"""Maps every metric name in kalpi_strategy_builder.metrics_constant to how
(or whether) it can be computed from live yfinance data.

Three-pass construction:
  1. Explicit entries for everything confidently computable.
  2. Explicit unsupported entries for the structurally-impossible bucket
     (multi-year CAGRs/averages beyond ~4y of annual history, proprietary
     Kalpi-only scores with no public formula).
  3. An audit pass over the full metrics_constant list: anything still
     unmapped is auto-marked unsupported with reason "not yet mapped" so
     every metric has an explicit, queryable answer -- nothing silently
     falls through.

Note on naming: the catalog uses "Sales" as the display name for revenue in
growth/historical variants (e.g. "Sales growth YoY", "Sales Prev Q") but
"Net Revenue" for current-period absolute values (e.g. "Net Revenue Q").
Both refer to the same underlying line item, so they share the "Net Revenue"
concept in _INCOME_ALIASES.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Callable, Literal, Optional

from kalpi_strategy_builder import metrics_constant
from screening import compute as c
from screening.data_fetch import TickerBundle

Category = Literal[
    "price_volume", "technical", "momentum_volatility",
    "fundamental_point", "fundamental_growth", "fundamental_ratio",
    "composite", "fundamental_multi_year",
]


@dataclass
class MetricSpec:
    name: str
    supported: bool
    category: Category
    compute_fn: Optional[Callable[[TickerBundle], Optional[float]]] = None
    lower_is_better: bool = False
    unsupported_reason: Optional[str] = None


METRIC_REGISTRY: dict[str, MetricSpec] = {}


def _reg(name: str, category: Category, fn: Callable[[TickerBundle], Optional[float]],
         lower_is_better: bool = False) -> None:
    METRIC_REGISTRY[name] = MetricSpec(
        name=name, supported=True, category=category, compute_fn=fn, lower_is_better=lower_is_better
    )


def _unsupported(name: str, category: Category, reason: str) -> None:
    METRIC_REGISTRY[name] = MetricSpec(
        name=name, supported=False, category=category, unsupported_reason=reason
    )


# ---------------------------------------------------------------------------
# Pass 1a: price / volume + technical indicators
# ---------------------------------------------------------------------------

_reg("Close Price", "price_volume", c.close_price)
_reg("High Price", "price_volume", c.high_price)
_reg("Low Price", "price_volume", c.low_price)
_reg("Open Price", "price_volume", c.open_price)
_reg("Volume", "price_volume", c.volume)

_reg("ADX 14", "technical", c.adx)
_reg("ATR 14", "technical", c.atr)
_reg("Bollinger Bands Lower", "technical", c.bollinger_lower)
_reg("Bollinger Bands Middle", "technical", c.bollinger_middle)
_reg("Bollinger Bands Upper", "technical", c.bollinger_upper)
_reg("CCI 14", "technical", c.cci)
_reg("MACD", "technical", c.macd)
_reg("MACD Histogram", "technical", c.macd_histogram)
_reg("MACD Signal", "technical", c.macd_signal)
_reg("MFI 14", "technical", c.mfi)
_reg("Momentum 10", "technical", c.momentum_10)
_reg("OBV", "technical", c.obv)
_reg("PPO", "technical", c.ppo)
_reg("RSI 14", "technical", c.rsi, lower_is_better=False)
_reg("Stochastic Slow D", "technical", c.stochastic_slow_d)
_reg("Stochastic Slow K", "technical", c.stochastic_slow_k)
_reg("Williams %R 14", "technical", c.williams_r)

for _n in (5, 10, 15, 20, 50, 100, 200):
    _reg(f"EMA {_n}", "technical", partial(c.ema, n=_n))
    _reg(f"SMA {_n}", "technical", partial(c.sma, n=_n))
    _reg(f"WMA {_n}", "technical", partial(c.wma, n=_n))

# ---------------------------------------------------------------------------
# Pass 1b: momentum / volatility factor metrics
# ---------------------------------------------------------------------------

_reg("Beta 1Y", "momentum_volatility", c.beta_1y)
_reg("Idiosyncratic return 1D", "momentum_volatility", c.idiosyncratic_return_1d)
_reg("Momentum 1M", "momentum_volatility", partial(c.momentum_return, days=21))
_reg("Momentum 3M", "momentum_volatility", partial(c.momentum_return, days=63))
_reg("Momentum 6M", "momentum_volatility", partial(c.momentum_return, days=126))
_reg("Momentum 12M", "momentum_volatility", partial(c.momentum_return, days=252))
_reg("Momentum 3M ex 1M", "momentum_volatility", partial(c.momentum_return_ex, total_days=63, ex_days=21))
_reg("Momentum 6M ex 1M", "momentum_volatility", partial(c.momentum_return_ex, total_days=126, ex_days=21))
_reg("Momentum 12M ex 1M", "momentum_volatility", partial(c.momentum_return_ex, total_days=252, ex_days=21))
_reg("Volatility 1M", "momentum_volatility", partial(c.volatility, window=21), lower_is_better=True)
_reg("Volatility 3M", "momentum_volatility", partial(c.volatility, window=63), lower_is_better=True)
_reg("Volatility 1Y", "momentum_volatility", partial(c.volatility, window=252), lower_is_better=True)
_reg("Price / 52W High", "momentum_volatility", c.price_to_52w_high)
_reg("Return 1D", "momentum_volatility", c.return_1d)

_unsupported("Momentum Score", "momentum_volatility",
             "No standardized public formula; this is a proprietary Kalpi composite score")
_unsupported("Volatility Score", "momentum_volatility",
             "No standardized public formula; this is a proprietary Kalpi composite score")

# ---------------------------------------------------------------------------
# Pass 1c: valuation / fundamental ratios (mostly from yfinance .info)
# ---------------------------------------------------------------------------

_reg("PE", "fundamental_ratio", c.pe_ratio, lower_is_better=True)
_reg("PB", "fundamental_ratio", c.pb_ratio, lower_is_better=True)
_reg("PS", "fundamental_ratio", c.ps_ratio, lower_is_better=True)
_reg("P/FCF", "fundamental_ratio", c.p_fcf, lower_is_better=True)
_reg("PEG Ratio TTM", "fundamental_ratio", c.peg_ratio, lower_is_better=True)
_reg("Market Cap", "fundamental_ratio", c.market_cap)
_reg("Enterprise value", "fundamental_ratio", c.enterprise_value)
_reg("EV EBIT", "fundamental_ratio", c.ev_ebit, lower_is_better=True)
_reg("EV EBITDA", "fundamental_ratio", c.ev_ebitda, lower_is_better=True)
_reg("EV Sales", "fundamental_ratio", c.ev_sales, lower_is_better=True)
_reg("Dividend yield", "fundamental_ratio", c.dividend_yield)
_reg("Dividend per Share", "fundamental_ratio", c.dividend_per_share)
_reg("Dividend Payout Ratio", "fundamental_ratio", c.dividend_payout_ratio)
_reg("Earnings yield", "fundamental_ratio", c.earnings_yield)
_reg("EBIT yield", "fundamental_ratio", c.ebit_yield)
_reg("EBITDA yield", "fundamental_ratio", c.ebitda_yield)
_reg("FCF yield", "fundamental_ratio", c.fcf_yield)
_reg("Operating CF yield", "fundamental_ratio", c.operating_cf_yield)
_reg("Book to Market", "fundamental_ratio", c.book_to_market)
_reg("Graham Number", "fundamental_ratio", c.graham_number)
_reg("BPS FY End", "fundamental_ratio", c.bps_fy_end)
_reg("Shares outstanding FY End", "fundamental_ratio", c.shares_outstanding)
_reg("Current ratio FY", "fundamental_ratio", c.current_ratio)
_reg("Quick ratio FY", "fundamental_ratio", c.quick_ratio)
_reg("Cash ratio FY", "fundamental_ratio", c.cash_ratio_fy)
_reg("Debt to Equity FY", "fundamental_ratio", c.debt_to_equity, lower_is_better=True)
_reg("Debt to EBITDA FY", "fundamental_ratio", c.debt_to_ebitda_fy, lower_is_better=True)
_reg("Debt to Assets FY", "fundamental_ratio", c.debt_to_assets_fy, lower_is_better=True)
_reg("Interest Coverage Ratio FY", "fundamental_ratio", c.interest_coverage_ratio_fy)
_reg("ROA FY", "fundamental_ratio", c.roa)
_reg("ROE FY", "fundamental_ratio", c.roe)
_reg("ROCE FY", "fundamental_ratio", c.roce_fy)
_reg("ROIC FY", "fundamental_ratio", c.roic_fy)
_reg("Asset Turnover FY", "fundamental_ratio", c.asset_turnover_fy)
_reg("Inventory Turnover", "fundamental_ratio", c.inventory_turnover)
_reg("Inventory Days", "fundamental_ratio", c.inventory_days, lower_is_better=True)
_reg("Receivable Turnover", "fundamental_ratio", c.receivable_turnover)
_reg("Receivables Days", "fundamental_ratio", c.receivables_days, lower_is_better=True)
_reg("Payables Days", "fundamental_ratio", c.payables_days)
_reg("EPS TTM", "fundamental_ratio", c.eps_ttm)

_unsupported("Shareholder Yield TTM", "fundamental_ratio",
             "Requires buyback/share-repurchase history not reliably available from yfinance")
_unsupported("Montier C-Score", "composite",
             "No standardized public formula; this is a proprietary composite score")

# ---------------------------------------------------------------------------
# Pass 1d: composite scores
# ---------------------------------------------------------------------------

_reg("Piotroski F-Score", "composite", c.piotroski_f_score)
_reg("Beneish M-Score", "composite", c.beneish_m_score, lower_is_better=True)
_reg("CF Accrual Ratio", "composite", c.cf_accrual_ratio, lower_is_better=True)

# ---------------------------------------------------------------------------
# Pass 1e: quarterly / annual statement line items, margins, and growth --
# generated for the concepts we have reliable statement aliases for.
# ---------------------------------------------------------------------------

# metric-catalog concept name -> (compute concept key in compute.py's alias tables, display prefix)
_Q_CONCEPTS = {
    "EBITDA": "EBITDA",
    "EPS": "EPS",
    "Gross Profit": "Gross Profit",
    "Profit after Tax": "Profit after Tax",
    "Operating Profit": "Operating Profit",
    "PBT": "PBT",
    "Net Revenue": "Net Revenue",
    "EBIT": "EBIT",
    "Interest Expense": "Interest Expense",
    "Depreciation": "Depreciation",
    "Income Tax": "Income Tax",
    "Other Income": "Other Income",
    "Extraordinary Items": "Extraordinary Items",
    "Equity Capital": "Equity Capital",
}

for _catalog_name, _concept in _Q_CONCEPTS.items():
    _reg(f"{_catalog_name} Q", "fundamental_point", partial(c.stmt_period_value, concept=_concept, period="Q", col_idx=0))
    _reg(f"{_catalog_name} FY", "fundamental_point", partial(c.stmt_period_value, concept=_concept, period="FY", col_idx=0))
    _reg(f"{_catalog_name} growth QoQ", "fundamental_growth",
         partial(c.stmt_growth, concept=_concept, period="Q", curr_idx=0, prev_idx=1))
    _reg(f"{_catalog_name} growth YoY", "fundamental_growth",
         partial(c.stmt_growth, concept=_concept, period="Q", curr_idx=0, prev_idx=4))
    _reg(f"{_catalog_name} FY growth 1Y", "fundamental_growth",
         partial(c.stmt_growth, concept=_concept, period="FY", curr_idx=0, prev_idx=1))

# "Sales"/"Profit"/"EBIT"/"Operating Profit"/"PBT"/"Interest Expense" growth variants that use a
# different display name than the absolute-value metric for the same underlying concept.
_GROWTH_ALIAS_CONCEPTS = {
    "Sales": "Net Revenue",
    "Profit": "Profit after Tax",
    "Operating Profit": "Operating Profit",
    "PBT": "PBT",
    "EBIT": "EBIT",
    "Interest Expense": "Interest Expense",
    "Depreciation": "Depreciation",
}
for _catalog_name, _concept in _GROWTH_ALIAS_CONCEPTS.items():
    _reg(f"{_catalog_name} growth QoQ", "fundamental_growth",
         partial(c.stmt_growth, concept=_concept, period="Q", curr_idx=0, prev_idx=1))
    _reg(f"{_catalog_name} growth YoY", "fundamental_growth",
         partial(c.stmt_growth, concept=_concept, period="Q", curr_idx=0, prev_idx=4))
    _reg(f"{_catalog_name} Growth QoQ", "fundamental_growth",
         partial(c.stmt_growth, concept=_concept, period="Q", curr_idx=0, prev_idx=1))
    _reg(f"{_catalog_name} Growth YoY", "fundamental_growth",
         partial(c.stmt_growth, concept=_concept, period="Q", curr_idx=0, prev_idx=4))
    _reg(f"{_catalog_name} FY growth 1Y", "fundamental_growth",
         partial(c.stmt_growth, concept=_concept, period="FY", curr_idx=0, prev_idx=1))

# "Prev Q" / "Prev YQ" / "2Q Back" / "3Q Back" quarterly point-in-time variants
_PREV_CONCEPT_DISPLAY = {
    "Sales": "Net Revenue", "EPS": "EPS", "EBITDA": "EBITDA", "Net Profit": "Profit after Tax",
    "EBIT": "EBIT", "Interest Exp": "Interest Expense", "Depreciation": "Depreciation",
    "Tax": "Income Tax", "Other Income": "Other Income", "Equity Capital": "Common Equity",
    "PBT": "PBT", "Operating Profit": "Operating Profit",
}
for _catalog_name, _concept in _PREV_CONCEPT_DISPLAY.items():
    _reg(f"{_catalog_name} Prev Q", "fundamental_point", partial(c.stmt_period_value, concept=_concept, period="Q", col_idx=1))
    _reg(f"{_catalog_name} Prev YQ", "fundamental_point", partial(c.stmt_period_value, concept=_concept, period="Q", col_idx=4))
    _reg(f"{_catalog_name} 2Q Back", "fundamental_point", partial(c.stmt_period_value, concept=_concept, period="Q", col_idx=2))
    _reg(f"{_catalog_name} 3Q Back", "fundamental_point", partial(c.stmt_period_value, concept=_concept, period="Q", col_idx=3))

# margins
_reg("Net profit margin Q", "fundamental_ratio", partial(c.stmt_margin, concept="Profit after Tax", period="Q"))
_reg("Net profit margin FY", "fundamental_ratio", partial(c.stmt_margin, concept="Profit after Tax", period="FY"))
_reg("Operating Margin Q", "fundamental_ratio", partial(c.stmt_margin, concept="Operating Profit", period="Q"))
_reg("Operating margin FY", "fundamental_ratio", partial(c.stmt_margin, concept="Operating Profit", period="FY"))
_reg("Gross Margin Q", "fundamental_ratio", partial(c.stmt_margin, concept="Gross Profit", period="Q"))
_reg("Gross margin FY", "fundamental_ratio", partial(c.stmt_margin, concept="Gross Profit", period="FY"))
_reg("EBITDA margin Q", "fundamental_ratio", partial(c.stmt_margin, concept="EBITDA", period="Q"))
_reg("EBITDA margin FY", "fundamental_ratio", partial(c.stmt_margin, concept="EBITDA", period="FY"))
_reg("OPM Prev Q", "fundamental_ratio", partial(c.stmt_margin, concept="Operating Profit", period="Q", col_idx=1))
_reg("OPM Prev YQ", "fundamental_ratio", partial(c.stmt_margin, concept="Operating Profit", period="Q", col_idx=4))
_reg("NPM Prev Q", "fundamental_ratio", partial(c.stmt_margin, concept="Profit after Tax", period="Q", col_idx=1))
_reg("NPM Prev YQ", "fundamental_ratio", partial(c.stmt_margin, concept="Profit after Tax", period="Q", col_idx=4))

# TTM (trailing-twelve-month) flow items and margins
_TTM_CONCEPTS = {"Sales": "Net Revenue", "Net Profit": "Profit after Tax", "EBITDA": "EBITDA", "EBIT": "EBIT"}
for _catalog_name, _concept in _TTM_CONCEPTS.items():
    _reg(f"{_catalog_name} TTM", "fundamental_point", partial(c.stmt_ttm_sum, concept=_concept))
_reg("Operating CF TTM", "fundamental_point", partial(c.stmt_ttm_sum, concept="Operating CF"))
_reg("Free CF TTM", "fundamental_point", partial(c.stmt_ttm_sum, concept="Free Cash Flow"))
_reg("Gross Margin TTM", "fundamental_ratio", partial(c.stmt_ttm_margin, concept="Gross Profit"))
_reg("EBITDA Margin TTM", "fundamental_ratio", partial(c.stmt_ttm_margin, concept="EBITDA"))
_reg("Operating Margin TTM", "fundamental_ratio", partial(c.stmt_ttm_margin, concept="Operating Profit"))
_reg("Net Margin TTM", "fundamental_ratio", partial(c.stmt_ttm_margin, concept="Profit after Tax"))

# ---------------------------------------------------------------------------
# Pass 2: explicit unsupported -- structurally out of reach with free yfinance
# data (needs 5-10y of statement history yfinance doesn't retain).
# ---------------------------------------------------------------------------

_MULTI_YEAR_UNSUPPORTED_REASON = "Needs 5-10 years of financial-statement history; yfinance retains only ~4 years"
for _m in metrics_constant:
    if any(tag in _m for tag in (
        "3Y Avg", "5Y Avg", "7Y Avg", "10Y Avg", "3Y CAGR", "5Y CAGR", "7Y CAGR", "10Y CAGR",
        "3Y Back", "5Y Back", "7Y Back", "10Y Back", "3Y Cumulative", "5Y Cumulative",
        "7Y Cumulative", "10Y Cumulative",
    )):
        _unsupported(_m, "fundamental_multi_year", _MULTI_YEAR_UNSUPPORTED_REASON)

# ---------------------------------------------------------------------------
# Pass 3: audit -- anything in metrics_constant still unmapped is explicitly
# marked unsupported so every metric has a queryable answer.
# ---------------------------------------------------------------------------

for _m in metrics_constant:
    if _m not in METRIC_REGISTRY:
        _unsupported(_m, "fundamental_multi_year", "not yet mapped")


def get_metric_spec(name: str) -> Optional[MetricSpec]:
    return METRIC_REGISTRY.get(name)


def list_unsupported() -> list[MetricSpec]:
    return [m for m in METRIC_REGISTRY.values() if not m.supported]


def list_supported() -> list[MetricSpec]:
    return [m for m in METRIC_REGISTRY.values() if m.supported]
