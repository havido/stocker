"""
Stock data endpoints (v1).

Serves historical price charts with Redis caching.
"""

import logging

from fastapi import APIRouter, HTTPException
from core.cache import CacheManager
from core.validators import is_valid_shape
import yfinance as yf

router = APIRouter(tags=["stocks"])

logger = logging.getLogger(__name__)

# TTLs per period (seconds)
_PERIOD_TTL = {
    "1D": 5 * 60,       # 5 minutes
    "1W": 60 * 60,      # 1 hour
    "1M": 60 * 60,      # 1 hour
    "1Y": 24 * 60 * 60, # 24 hours
    "ALL": 24 * 60 * 60,
}

_PERIODS_MAP = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "1h"),
    "1M": ("1mo", "1d"),
    "1Y": ("1y", "1wk"),
    "ALL": ("5y", "1mo"),
}

_NAME_TTL = 7 * 24 * 60 * 60  # company names rarely change — cache a week


def _company_name(ticker: str, info: dict, cache: CacheManager) -> str:
    """
    Resolve a human-readable company name resiliently.

    .info is rate-limited and often empty, which would leave us showing the
    ticker twice ("TSLA TSLA"). So: try .info, then a cached value, then the
    Yahoo search endpoint (far less throttled), caching any real name we find.
    """
    name = info.get("longName") or info.get("shortName")
    if name and name != ticker:
        cache.set_raw(f"stockname:{ticker}", name, ttl=_NAME_TTL)
        return name

    cached = cache.get_raw(f"stockname:{ticker}")
    if cached:
        return cached

    try:
        for q in (yf.Search(ticker).quotes or []):
            if q.get("symbol", "").upper() == ticker:
                nm = q.get("longname") or q.get("shortname")
                if nm:
                    cache.set_raw(f"stockname:{ticker}", nm, ttl=_NAME_TTL)
                    return nm
    except Exception as e:
        logger.warning("company-name lookup via search failed for %s: %s", ticker, e)

    return ticker


@router.get("/stocks/{ticker}/chart")
async def get_stock_chart(ticker: str):
    """
    Return historical price data for all periods.
    Caches each period independently with tiered TTLs.
    """
    ticker = ticker.upper().strip()
    if not is_valid_shape(ticker):
        raise HTTPException(status_code=400, detail=f"'{ticker}' is not a valid ticker symbol")

    cache = CacheManager()
    stock = yf.Ticker(ticker)

    # yfinance's .info is the most rate-limited call and frequently throws under
    # Yahoo throttling. Treat it as best-effort metadata — we can still build a
    # usable chart from price history alone.
    info = {}
    try:
        info = stock.info or {}
    except Exception as e:
        logger.warning("yfinance .info failed for %s: %s", ticker, e)

    history = {}
    history_ok = False
    for period_key, (period, interval) in _PERIODS_MAP.items():
        cache_key = f"stock:{ticker}:{period_key}"
        cached = cache.get_raw(cache_key)
        if cached is not None:
            history[period_key] = cached
            history_ok = history_ok or len(cached) > 0
            continue

        try:
            hist = stock.history(period=period, interval=interval)
            fmt = "%H:%M" if period_key == "1D" else "%m/%d"
            points = [
                {"time": idx.strftime(fmt), "price": round(float(row["Close"]), 2)}
                for idx, row in hist.iterrows()
            ]
            history[period_key] = points
            if points:
                history_ok = True
                cache.set_raw(cache_key, points, ttl=_PERIOD_TTL[period_key])
        except Exception as e:
            logger.warning("yfinance history %s failed for %s: %s", period_key, ticker, e)
            history[period_key] = []

    # Prices: prefer info, fall back to the 1D history endpoints.
    one_day = history.get("1D") or []
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
    if not current_price and one_day:
        current_price = one_day[-1]["price"]
    if not prev_close and one_day:
        prev_close = one_day[0]["price"]

    # Nothing usable from any source → upstream is throttling us. 503 is retryable
    # and lets the client show "temporarily unavailable" instead of a hard error.
    if not history_ok and not current_price:
        raise HTTPException(
            status_code=503,
            detail=f"Market data for {ticker} is temporarily unavailable. Please try again shortly.",
        )

    current_price = current_price or 0.0
    prev_close = prev_close or current_price
    change = current_price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0
    name = _company_name(ticker, info, cache)

    return {
        "ticker": ticker,
        "name": name,
        "price": round(float(current_price), 2),
        "change": round(float(change), 2),
        "changePercent": round(float(change_pct), 2),
        "history": history,
    }
