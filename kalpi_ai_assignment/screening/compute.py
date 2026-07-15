# file: screening/compute.py
"""Hand-rolled technical indicator and fundamental-ratio formulas.

No pandas-ta / TA-Lib: TA-Lib needs a C extension that won't build on
Vercel's Python image, and pandas-ta is unmaintained and breaks on modern
numpy. These ~13 indicator shapes are standard and small enough to keep
fully auditable here.

Every function returns a single float for "as of latest bar" metrics, or
None if there isn't enough history / data to compute it for this ticker.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from screening.data_fetch import TickerBundle

TRADING_DAYS = {"1M": 21, "3M": 63, "6M": 126, "12M": 252, "1Y": 252}


def _f(x) -> Optional[float]:
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return x


def _close(bundle: TickerBundle) -> Optional[pd.Series]:
    if bundle.ohlcv is None or "Close" not in bundle.ohlcv:
        return None
    s = bundle.ohlcv["Close"].dropna()
    return s if len(s) > 0 else None


def _ohlcv_cols(bundle: TickerBundle):
    df = bundle.ohlcv
    if df is None:
        return None, None, None, None
    try:
        return df["High"], df["Low"], df["Close"], df["Volume"]
    except KeyError:
        return None, None, None, None


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------

def sma(bundle: TickerBundle, n: int) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < n:
        return None
    return _f(c.rolling(n).mean().iloc[-1])


def ema(bundle: TickerBundle, n: int) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < n:
        return None
    return _f(c.ewm(span=n, adjust=False).mean().iloc[-1])


def wma(bundle: TickerBundle, n: int) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < n:
        return None
    weights = np.arange(1, n + 1)
    window = c.tail(n).to_numpy()
    return _f(np.dot(window, weights) / weights.sum())


def rsi(bundle: TickerBundle, n: int = 14) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < n + 1:
        return None
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    last_loss = avg_loss.iloc[-1]
    if last_loss == 0:
        return 100.0
    rs = avg_gain.iloc[-1] / last_loss
    return _f(100 - 100 / (1 + rs))


def _macd_lines(c: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = c.ewm(span=fast, adjust=False).mean()
    ema_slow = c.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def macd(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 35:
        return None
    macd_line, _ = _macd_lines(c)
    return _f(macd_line.iloc[-1])


def macd_signal(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 35:
        return None
    _, signal_line = _macd_lines(c)
    return _f(signal_line.iloc[-1])


def macd_histogram(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 35:
        return None
    macd_line, signal_line = _macd_lines(c)
    return _f((macd_line - signal_line).iloc[-1])


def _bollinger(c: pd.Series, n=20, k=2):
    mid = c.rolling(n).mean()
    std = c.rolling(n).std()
    return mid + k * std, mid, mid - k * std


def bollinger_upper(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 20:
        return None
    upper, _, _ = _bollinger(c)
    return _f(upper.iloc[-1])


def bollinger_middle(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 20:
        return None
    _, mid, _ = _bollinger(c)
    return _f(mid.iloc[-1])


def bollinger_lower(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 20:
        return None
    _, _, lower = _bollinger(c)
    return _f(lower.iloc[-1])


def atr(bundle: TickerBundle, n: int = 14) -> Optional[float]:
    h, l, c, _ = _ohlcv_cols(bundle)
    if h is None or len(c) < n + 1:
        return None
    prev_close = c.shift()
    tr = pd.concat([h - l, (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    return _f(tr.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])


def adx(bundle: TickerBundle, n: int = 14) -> Optional[float]:
    h, l, c, _ = _ohlcv_cols(bundle)
    if h is None or len(c) < 2 * n:
        return None
    up_move = h.diff()
    down_move = -l.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    prev_close = c.shift()
    tr = pd.concat([h - l, (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    atr_s = tr.ewm(alpha=1 / n, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=h.index).ewm(alpha=1 / n, adjust=False).mean() / atr_s
    minus_di = 100 * pd.Series(minus_dm, index=h.index).ewm(alpha=1 / n, adjust=False).mean() / atr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return _f(dx.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])


def cci(bundle: TickerBundle, n: int = 14) -> Optional[float]:
    h, l, c, _ = _ohlcv_cols(bundle)
    if h is None or len(c) < n:
        return None
    tp = (h + l + c) / 3
    sma_tp = tp.rolling(n).mean()
    mad = tp.rolling(n).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    last_mad = mad.iloc[-1]
    if not last_mad:
        return None
    return _f((tp.iloc[-1] - sma_tp.iloc[-1]) / (0.015 * last_mad))


def mfi(bundle: TickerBundle, n: int = 14) -> Optional[float]:
    h, l, c, v = _ohlcv_cols(bundle)
    if h is None or len(c) < n + 1:
        return None
    tp = (h + l + c) / 3
    raw_mf = tp * v
    pos_mf = raw_mf.where(tp > tp.shift(), 0.0)
    neg_mf = raw_mf.where(tp < tp.shift(), 0.0)
    pos_sum = pos_mf.rolling(n).sum().iloc[-1]
    neg_sum = neg_mf.rolling(n).sum().iloc[-1]
    if not neg_sum:
        return 100.0
    return _f(100 - 100 / (1 + pos_sum / neg_sum))


def _stochastic(h, l, c, n=14, d=3):
    lowest_low = l.rolling(n).min()
    highest_high = h.rolling(n).max()
    rng = highest_high - lowest_low
    k = 100 * (c - lowest_low) / rng.replace(0, np.nan)
    d_line = k.rolling(d).mean()
    return k, d_line


def stochastic_slow_k(bundle: TickerBundle) -> Optional[float]:
    h, l, c, _ = _ohlcv_cols(bundle)
    if h is None or len(c) < 16:
        return None
    k, _ = _stochastic(h, l, c)
    return _f(k.iloc[-1])


def stochastic_slow_d(bundle: TickerBundle) -> Optional[float]:
    h, l, c, _ = _ohlcv_cols(bundle)
    if h is None or len(c) < 16:
        return None
    _, d_line = _stochastic(h, l, c)
    return _f(d_line.iloc[-1])


def williams_r(bundle: TickerBundle, n: int = 14) -> Optional[float]:
    h, l, c, _ = _ohlcv_cols(bundle)
    if h is None or len(c) < n:
        return None
    highest_high = h.rolling(n).max()
    lowest_low = l.rolling(n).min()
    rng = (highest_high - lowest_low).iloc[-1]
    if not rng:
        return None
    return _f(-100 * (highest_high.iloc[-1] - c.iloc[-1]) / rng)


def obv(bundle: TickerBundle) -> Optional[float]:
    _, _, c, v = _ohlcv_cols(bundle)
    if c is None or len(c) < 2:
        return None
    direction = np.sign(c.diff()).fillna(0)
    return _f((direction * v).cumsum().iloc[-1])


def ppo(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 26:
        return None
    ema_fast = c.ewm(span=12, adjust=False).mean().iloc[-1]
    ema_slow = c.ewm(span=26, adjust=False).mean().iloc[-1]
    if not ema_slow:
        return None
    return _f((ema_fast - ema_slow) / ema_slow * 100)


def momentum_10(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 11:
        return None
    return _f(c.iloc[-1] - c.iloc[-11])


# ---------------------------------------------------------------------------
# Price / volume passthroughs
# ---------------------------------------------------------------------------

def close_price(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    return _f(c.iloc[-1]) if c is not None else None


def high_price(bundle: TickerBundle) -> Optional[float]:
    df = bundle.ohlcv
    if df is None or "High" not in df:
        return None
    return _f(df["High"].dropna().iloc[-1]) if len(df["High"].dropna()) else None


def low_price(bundle: TickerBundle) -> Optional[float]:
    df = bundle.ohlcv
    if df is None or "Low" not in df:
        return None
    return _f(df["Low"].dropna().iloc[-1]) if len(df["Low"].dropna()) else None


def open_price(bundle: TickerBundle) -> Optional[float]:
    df = bundle.ohlcv
    if df is None or "Open" not in df:
        return None
    return _f(df["Open"].dropna().iloc[-1]) if len(df["Open"].dropna()) else None


def volume(bundle: TickerBundle) -> Optional[float]:
    df = bundle.ohlcv
    if df is None or "Volume" not in df:
        return None
    return _f(df["Volume"].dropna().iloc[-1]) if len(df["Volume"].dropna()) else None


# ---------------------------------------------------------------------------
# Momentum / volatility factor metrics
# ---------------------------------------------------------------------------

def momentum_return(bundle: TickerBundle, days: int) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < days + 1:
        return None
    base = c.iloc[-(days + 1)]
    if not base:
        return None
    return _f((c.iloc[-1] / base - 1) * 100)


def momentum_return_ex(bundle: TickerBundle, total_days: int, ex_days: int) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < total_days + 1:
        return None
    end = c.iloc[-(ex_days + 1)]
    start = c.iloc[-(total_days + 1)]
    if not start:
        return None
    return _f((end / start - 1) * 100)


def volatility(bundle: TickerBundle, window: int) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < window + 1:
        return None
    daily_ret = c.pct_change().dropna().tail(window)
    if len(daily_ret) < window // 2:
        return None
    return _f(daily_ret.std() * math.sqrt(252) * 100)


def _beta_value(bundle: TickerBundle, window: int = 252) -> Optional[float]:
    c = _close(bundle)
    if c is None or bundle.index_ohlcv is None or "Close" not in bundle.index_ohlcv:
        return None
    idx_c = bundle.index_ohlcv["Close"].dropna()
    joined = pd.concat([c, idx_c], axis=1, join="inner").dropna()
    joined.columns = ["stock", "index"]
    if len(joined) < min(window, 60):
        return None
    joined = joined.tail(window)
    stock_ret = joined["stock"].pct_change().dropna()
    index_ret = joined["index"].pct_change().dropna()
    aligned = pd.concat([stock_ret, index_ret], axis=1).dropna()
    if len(aligned) < 30:
        return None
    var = aligned.iloc[:, 1].var()
    if not var:
        return None
    cov = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
    return _f(cov / var)


def beta_1y(bundle: TickerBundle) -> Optional[float]:
    return _beta_value(bundle, window=252)


def idiosyncratic_return_1d(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    b = _beta_value(bundle)
    if c is None or b is None or bundle.index_ohlcv is None or len(c) < 2:
        return None
    idx_c = bundle.index_ohlcv["Close"].dropna()
    if len(idx_c) < 2:
        return None
    stock_ret = c.iloc[-1] / c.iloc[-2] - 1
    index_ret = idx_c.iloc[-1] / idx_c.iloc[-2] - 1
    return _f((stock_ret - b * index_ret) * 100)


def price_to_52w_high(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 30:
        return None
    high_52w = c.tail(252).max()
    if not high_52w:
        return None
    return _f(c.iloc[-1] / high_52w)


def return_1d(bundle: TickerBundle) -> Optional[float]:
    c = _close(bundle)
    if c is None or len(c) < 2:
        return None
    prev = c.iloc[-2]
    if not prev:
        return None
    return _f((c.iloc[-1] / prev - 1) * 100)


# ---------------------------------------------------------------------------
# Fundamental: .info passthroughs
# ---------------------------------------------------------------------------

def _info_get(bundle: TickerBundle, *keys) -> Optional[float]:
    if not bundle.info:
        return None
    for k in keys:
        if k in bundle.info and bundle.info[k] is not None:
            return _f(bundle.info[k])
    return None


def pe_ratio(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "trailingPE", "forwardPE")


def pb_ratio(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "priceToBook")


def ps_ratio(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "priceToSalesTrailing12Months")


def market_cap(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "marketCap")


def dividend_yield(bundle: TickerBundle) -> Optional[float]:
    v = _info_get(bundle, "dividendYield")
    return v


def dividend_per_share(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "lastDividendValue", "trailingAnnualDividendRate")


def dividend_payout_ratio(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "payoutRatio")


def enterprise_value(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "enterpriseValue")


def ev_ebitda(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "enterpriseToEbitda")


def ev_sales(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "enterpriseToRevenue")


def peg_ratio(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "trailingPegRatio", "pegRatio")


def bps_fy_end(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "bookValue")


def shares_outstanding(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "sharesOutstanding")


def current_ratio(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "currentRatio")


def quick_ratio(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "quickRatio")


def debt_to_equity(bundle: TickerBundle) -> Optional[float]:
    v = _info_get(bundle, "debtToEquity")
    return _f(v / 100) if v is not None else None


def roe(bundle: TickerBundle) -> Optional[float]:
    v = _info_get(bundle, "returnOnEquity")
    return _f(v * 100) if v is not None else None


def roa(bundle: TickerBundle) -> Optional[float]:
    v = _info_get(bundle, "returnOnAssets")
    return _f(v * 100) if v is not None else None


def eps_ttm(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "trailingEps")


def book_to_market(bundle: TickerBundle) -> Optional[float]:
    pb = pb_ratio(bundle)
    if not pb:
        return None
    return _f(1 / pb)


def earnings_yield(bundle: TickerBundle) -> Optional[float]:
    pe = pe_ratio(bundle)
    if not pe:
        return None
    return _f(100 / pe)


def free_cash_flow_fy(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "freeCashflow")


def fcf_yield(bundle: TickerBundle) -> Optional[float]:
    fcf = free_cash_flow_fy(bundle)
    mc = market_cap(bundle)
    if not fcf or not mc:
        return None
    return _f(fcf / mc * 100)


def operating_cf_fy(bundle: TickerBundle) -> Optional[float]:
    return _info_get(bundle, "operatingCashflow")


def operating_cf_yield(bundle: TickerBundle) -> Optional[float]:
    ocf = operating_cf_fy(bundle)
    mc = market_cap(bundle)
    if not ocf or not mc:
        return None
    return _f(ocf / mc * 100)


def ebitda_yield(bundle: TickerBundle) -> Optional[float]:
    ebitda = _info_get(bundle, "ebitda")
    ev = enterprise_value(bundle)
    if not ebitda or not ev:
        return None
    return _f(ebitda / ev * 100)


def _ebit_fy_value(bundle: TickerBundle) -> Optional[float]:
    return _income_fy(bundle, "EBIT", 0)


def ev_ebit(bundle: TickerBundle) -> Optional[float]:
    ebit = _ebit_fy_value(bundle)
    ev = enterprise_value(bundle)
    if not ebit or not ev:
        return None
    return _f(ev / ebit)


def ebit_yield(bundle: TickerBundle) -> Optional[float]:
    ebit = _ebit_fy_value(bundle)
    ev = enterprise_value(bundle)
    if not ebit or not ev:
        return None
    return _f(ebit / ev * 100)


def p_fcf(bundle: TickerBundle) -> Optional[float]:
    mc = market_cap(bundle)
    fcf = free_cash_flow_fy(bundle)
    if not mc or not fcf:
        return None
    return _f(mc / fcf)


def graham_number(bundle: TickerBundle) -> Optional[float]:
    eps = eps_ttm(bundle)
    bvps = bps_fy_end(bundle)
    if not eps or not bvps or eps <= 0 or bvps <= 0:
        return None
    return _f(math.sqrt(22.5 * eps * bvps))


# ---------------------------------------------------------------------------
# Fundamental: financial-statement line items
# ---------------------------------------------------------------------------

_INCOME_ALIASES = {
    "Net Revenue": ["Total Revenue", "TotalRevenue", "Operating Revenue"],
    "Gross Profit": ["Gross Profit", "GrossProfit"],
    "EBITDA": ["EBITDA", "Normalized EBITDA"],
    "EBIT": ["EBIT", "Operating Income", "OperatingIncome"],
    "Operating Profit": ["Operating Income", "OperatingIncome"],
    "PBT": ["Pretax Income", "PretaxIncome"],
    "Profit after Tax": ["Net Income", "NetIncome", "Net Income Common Stockholders"],
    "Interest Expense": ["Interest Expense", "InterestExpense", "Interest Expense Non Operating"],
    "Depreciation": ["Reconciled Depreciation", "Depreciation And Amortization In Income Statement",
                      "Depreciation Amortization Depletion Income Statement"],
    "Income Tax": ["Tax Provision", "TaxProvision"],
    "Other Income": ["Other Income Expense", "Other Non Operating Income Expenses"],
    "EPS": ["Diluted EPS", "Basic EPS"],
    "Extraordinary Items": ["Special Income Charges", "Unusual Items", "Gain On Sale Of Business"],
}

_BALANCE_ALIASES = {
    "Total Assets": ["Total Assets"],
    "Current Assets": ["Current Assets"],
    "Current Liabilities": ["Current Liabilities"],
    "Total Debt": ["Total Debt"],
    "Cash and Cash Eq": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
    "Common Equity": ["Common Stock Equity", "Stockholders Equity"],
    "Inventories": ["Inventory"],
    "Receivables": ["Receivables", "Accounts Receivable"],
    "Trade Payables": ["Accounts Payable", "Payables"],
    "Total Liabilities": ["Total Liabilities Net Minority Interest"],
    "Equity Capital": ["Common Stock", "Common Stock Equity"],
}

_CASHFLOW_ALIASES = {
    "Operating CF": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    "Investing CF": ["Investing Cash Flow", "Cash Flow From Continuing Investing Activities"],
    "Financing CF": ["Financing Cash Flow", "Cash Flow From Continuing Financing Activities"],
    "Free Cash Flow": ["Free Cash Flow"],
    "Capex": ["Capital Expenditure"],
}


def _stmt_row(df: Optional[pd.DataFrame], aliases: list[str], col_idx: int) -> Optional[float]:
    if df is None or df.empty or col_idx >= df.shape[1]:
        return None
    for alias in aliases:
        if alias in df.index:
            val = df.loc[alias].iloc[col_idx]
            return _f(val)
    return None


def _income_q(bundle: TickerBundle, concept: str, col_idx: int) -> Optional[float]:
    return _stmt_row(bundle.quarterly_financials, _INCOME_ALIASES.get(concept, []), col_idx)


def _income_fy(bundle: TickerBundle, concept: str, col_idx: int) -> Optional[float]:
    return _stmt_row(bundle.financials, _INCOME_ALIASES.get(concept, []), col_idx)


def _growth(curr: Optional[float], prev: Optional[float]) -> Optional[float]:
    if curr is None or prev is None or prev == 0:
        return None
    return _f((curr - prev) / abs(prev) * 100)


def _margin(numerator_concept: str, bundle: TickerBundle, period: str, col_idx: int = 0) -> Optional[float]:
    getter = _income_q if period == "Q" else _income_fy
    num = getter(bundle, numerator_concept, col_idx)
    rev = getter(bundle, "Net Revenue", col_idx)
    if num is None or not rev:
        return None
    return _f(num / rev * 100)


def stmt_period_value(bundle: TickerBundle, concept: str, period: str, col_idx: int) -> Optional[float]:
    """concept: key in _INCOME_ALIASES/_BALANCE_ALIASES/_CASHFLOW_ALIASES.
    period: 'Q' or 'FY'. col_idx: 0 = most recent, 1 = previous, etc."""
    if concept in _INCOME_ALIASES:
        df = bundle.quarterly_financials if period == "Q" else bundle.financials
        return _stmt_row(df, _INCOME_ALIASES[concept], col_idx)
    if concept in _BALANCE_ALIASES:
        df = bundle.quarterly_balance_sheet if period == "Q" else bundle.balance_sheet
        return _stmt_row(df, _BALANCE_ALIASES[concept], col_idx)
    if concept in _CASHFLOW_ALIASES:
        df = bundle.quarterly_cashflow if period == "Q" else bundle.cashflow
        return _stmt_row(df, _CASHFLOW_ALIASES[concept], col_idx)
    return None


def stmt_growth(bundle: TickerBundle, concept: str, period: str, curr_idx: int, prev_idx: int) -> Optional[float]:
    curr = stmt_period_value(bundle, concept, period, curr_idx)
    prev = stmt_period_value(bundle, concept, period, prev_idx)
    return _growth(curr, prev)


def stmt_margin(bundle: TickerBundle, concept: str, period: str, col_idx: int = 0) -> Optional[float]:
    num = stmt_period_value(bundle, concept, period, col_idx)
    rev = stmt_period_value(bundle, "Net Revenue", period, col_idx)
    if num is None or not rev:
        return None
    return _f(num / rev * 100)


def stmt_ttm_sum(bundle: TickerBundle, concept: str) -> Optional[float]:
    """Sum of the last 4 quarterly columns for a flow item (revenue, profit, EBITDA, ...)."""
    df = None
    if concept in _INCOME_ALIASES:
        df = bundle.quarterly_financials
        aliases = _INCOME_ALIASES[concept]
    elif concept in _CASHFLOW_ALIASES:
        df = bundle.quarterly_cashflow
        aliases = _CASHFLOW_ALIASES[concept]
    else:
        return None
    if df is None or df.empty or df.shape[1] < 4:
        return None
    for alias in aliases:
        if alias in df.index:
            vals = df.loc[alias].iloc[0:4]
            if vals.isnull().any():
                return None
            return _f(vals.sum())
    return None


def stmt_ttm_margin(bundle: TickerBundle, concept: str) -> Optional[float]:
    num = stmt_ttm_sum(bundle, concept)
    rev = stmt_ttm_sum(bundle, "Net Revenue")
    if num is None or not rev:
        return None
    return _f(num / rev * 100)


def debt_to_ebitda_fy(bundle: TickerBundle) -> Optional[float]:
    debt = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Total Debt"], 0)
    ebitda = _income_fy(bundle, "EBITDA", 0)
    if not debt or not ebitda:
        return None
    return _f(debt / ebitda)


def debt_to_assets_fy(bundle: TickerBundle) -> Optional[float]:
    debt = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Total Debt"], 0)
    assets = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Total Assets"], 0)
    if not debt or not assets:
        return None
    return _f(debt / assets)


def interest_coverage_ratio_fy(bundle: TickerBundle) -> Optional[float]:
    ebit = _ebit_fy_value(bundle)
    interest = _income_fy(bundle, "Interest Expense", 0)
    if not ebit or not interest:
        return None
    return _f(ebit / abs(interest))


def roce_fy(bundle: TickerBundle) -> Optional[float]:
    ebit = _ebit_fy_value(bundle)
    assets = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Total Assets"], 0)
    curr_liab = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Current Liabilities"], 0)
    if not ebit or not assets:
        return None
    capital_employed = assets - (curr_liab or 0)
    if not capital_employed:
        return None
    return _f(ebit / capital_employed * 100)


def roic_fy(bundle: TickerBundle) -> Optional[float]:
    ni = _income_fy(bundle, "Profit after Tax", 0)
    debt = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Total Debt"], 0)
    equity = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Common Equity"], 0)
    if ni is None or debt is None or not equity:
        return None
    invested_capital = debt + equity
    if not invested_capital:
        return None
    return _f(ni / invested_capital * 100)


def asset_turnover_fy(bundle: TickerBundle) -> Optional[float]:
    revenue = _income_fy(bundle, "Net Revenue", 0)
    assets = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Total Assets"], 0)
    if not revenue or not assets:
        return None
    return _f(revenue / assets)


def inventory_turnover(bundle: TickerBundle) -> Optional[float]:
    revenue = _income_fy(bundle, "Net Revenue", 0)
    inv = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Inventories"], 0)
    if not revenue or not inv:
        return None
    return _f(revenue / inv)


def inventory_days(bundle: TickerBundle) -> Optional[float]:
    turns = inventory_turnover(bundle)
    if not turns:
        return None
    return _f(365 / turns)


def receivable_turnover(bundle: TickerBundle) -> Optional[float]:
    revenue = _income_fy(bundle, "Net Revenue", 0)
    recv = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Receivables"], 0)
    if not revenue or not recv:
        return None
    return _f(revenue / recv)


def receivables_days(bundle: TickerBundle) -> Optional[float]:
    turns = receivable_turnover(bundle)
    if not turns:
        return None
    return _f(365 / turns)


def payables_days(bundle: TickerBundle) -> Optional[float]:
    revenue = _income_fy(bundle, "Net Revenue", 0)
    payables = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Trade Payables"], 0)
    if not revenue or not payables:
        return None
    return _f(365 * payables / revenue)


def cash_ratio_fy(bundle: TickerBundle) -> Optional[float]:
    cash = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Cash and Cash Eq"], 0)
    curr_liab = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Current Liabilities"], 0)
    if not cash or not curr_liab:
        return None
    return _f(cash / curr_liab)


def cf_accrual_ratio(bundle: TickerBundle) -> Optional[float]:
    ni = _income_fy(bundle, "Profit after Tax", 0)
    ocf = _stmt_row(bundle.cashflow, _CASHFLOW_ALIASES["Operating CF"], 0)
    total_assets = _stmt_row(bundle.balance_sheet, _BALANCE_ALIASES["Total Assets"], 0)
    if ni is None or ocf is None or not total_assets:
        return None
    return _f((ni - ocf) / total_assets)


def piotroski_f_score(bundle: TickerBundle) -> Optional[float]:
    """Standard 9-signal Piotroski F-Score. Returns None if fewer than 2 years
    of statements are available (needed for the YoY comparison signals)."""
    bs, fin, cf = bundle.balance_sheet, bundle.financials, bundle.cashflow
    if bs is None or fin is None or cf is None:
        return None
    if bs.shape[1] < 2 or fin.shape[1] < 2 or cf.shape[1] < 2:
        return None

    score = 0
    ni = _income_fy(bundle, "Profit after Tax", 0)
    ni_prev = _income_fy(bundle, "Profit after Tax", 1)
    total_assets = _stmt_row(bs, _BALANCE_ALIASES["Total Assets"], 0)
    total_assets_prev = _stmt_row(bs, _BALANCE_ALIASES["Total Assets"], 1)
    ocf = _stmt_row(cf, _CASHFLOW_ALIASES["Operating CF"], 0)
    total_debt = _stmt_row(bs, _BALANCE_ALIASES["Total Debt"], 0)
    total_debt_prev = _stmt_row(bs, _BALANCE_ALIASES["Total Debt"], 1)
    current_assets = _stmt_row(bs, _BALANCE_ALIASES["Current Assets"], 0)
    current_liab = _stmt_row(bs, _BALANCE_ALIASES["Current Liabilities"], 0)
    current_assets_prev = _stmt_row(bs, _BALANCE_ALIASES["Current Assets"], 1)
    current_liab_prev = _stmt_row(bs, _BALANCE_ALIASES["Current Liabilities"], 1)
    gross_profit = _income_fy(bundle, "Gross Profit", 0)
    gross_profit_prev = _income_fy(bundle, "Gross Profit", 1)
    revenue = _income_fy(bundle, "Net Revenue", 0)
    revenue_prev = _income_fy(bundle, "Net Revenue", 1)
    shares = _info_get(bundle, "sharesOutstanding")

    if ni is not None and ni > 0:
        score += 1
    if ocf is not None and ocf > 0:
        score += 1
    if ni is not None and ni_prev is not None and total_assets and total_assets_prev:
        roa_curr, roa_prev = ni / total_assets, ni_prev / total_assets_prev
        if roa_curr > roa_prev:
            score += 1
    if ocf is not None and ni is not None and ocf > ni:
        score += 1
    if total_debt is not None and total_debt_prev is not None and total_assets and total_assets_prev:
        if (total_debt / total_assets) < (total_debt_prev / total_assets_prev):
            score += 1
    if current_assets and current_liab and current_assets_prev and current_liab_prev:
        cr_curr = current_assets / current_liab
        cr_prev = current_assets_prev / current_liab_prev
        if cr_curr > cr_prev:
            score += 1
    if shares is not None:
        score += 1  # no share-count history available to compare; neutral credit
    if gross_profit is not None and gross_profit_prev is not None and revenue and revenue_prev:
        gm_curr, gm_prev = gross_profit / revenue, gross_profit_prev / revenue_prev
        if gm_curr > gm_prev:
            score += 1
    if revenue is not None and revenue_prev and total_assets and total_assets_prev:
        at_curr = revenue / total_assets
        at_prev = revenue_prev / total_assets_prev
        if at_curr > at_prev:
            score += 1

    return float(score)


def beneish_m_score(bundle: TickerBundle) -> Optional[float]:
    """Simplified Beneish M-Score using the subset of the 8 variables computable
    from yfinance's standard statements (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA)."""
    bs, fin, cf = bundle.balance_sheet, bundle.financials, bundle.cashflow
    if bs is None or fin is None or bs.shape[1] < 2 or fin.shape[1] < 2:
        return None

    revenue = _income_fy(bundle, "Net Revenue", 0)
    revenue_prev = _income_fy(bundle, "Net Revenue", 1)
    receivables = _stmt_row(bs, _BALANCE_ALIASES["Receivables"], 0)
    receivables_prev = _stmt_row(bs, _BALANCE_ALIASES["Receivables"], 1)
    gross_profit = _income_fy(bundle, "Gross Profit", 0)
    gross_profit_prev = _income_fy(bundle, "Gross Profit", 1)
    total_assets = _stmt_row(bs, _BALANCE_ALIASES["Total Assets"], 0)
    total_assets_prev = _stmt_row(bs, _BALANCE_ALIASES["Total Assets"], 1)
    current_assets = _stmt_row(bs, _BALANCE_ALIASES["Current Assets"], 0)
    total_debt = _stmt_row(bs, _BALANCE_ALIASES["Total Debt"], 0)
    total_debt_prev = _stmt_row(bs, _BALANCE_ALIASES["Total Debt"], 1)
    ni = _income_fy(bundle, "Profit after Tax", 0)
    ocf = _stmt_row(cf, _CASHFLOW_ALIASES["Operating CF"], 0) if cf is not None else None

    required = [revenue, revenue_prev, receivables, receivables_prev, gross_profit,
                gross_profit_prev, total_assets, total_assets_prev, total_debt,
                total_debt_prev, ni, ocf]
    if any(v is None for v in required) or not revenue_prev or not total_assets_prev or not gross_profit or not total_assets:
        return None

    dsri = (receivables / revenue) / (receivables_prev / revenue_prev)
    gmi = (gross_profit_prev / revenue_prev) / (gross_profit / revenue)
    sgi = revenue / revenue_prev
    lvgi = (total_debt / total_assets) / (total_debt_prev / total_assets_prev)
    tata = (ni - ocf) / total_assets
    # AQI/DEPI/SGAI need line items (PP&E, depreciation, SG&A) too inconsistently
    # named across issuers to trust; held at neutral (1.0 / 0.0) rather than guessed.
    aqi, depi, sgai = 1.0, 1.0, 0.0

    m_score = (-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
               + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)
    return _f(m_score)
