"""
Stock data endpoints (v1).

Serves historical price charts with Redis caching.
"""

import logging
import math

from fastapi import APIRouter, HTTPException
from core.cache import CacheManager
from core.validators import is_valid_shape
import yfinance as yf

router = APIRouter(tags=["stocks"])

logger = logging.getLogger(__name__)


def _finite(x, default: float = 0.0) -> float:
    """Coerce to a finite float. NaN/Inf are not JSON-serializable (Starlette
    renders with allow_nan=False) — rate-limited yfinance responses contain NaN,
    which would otherwise crash response serialization with an unhandled 500."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default

# Periods exposed to the client (matches the product spec). Each maps to a
# (yfinance period, interval) pair.
_PERIODS_MAP = {
    "1D": ("1d", "5m"),
    "1M": ("1mo", "1d"),
    "6M": ("6mo", "1d"),
    "YTD": ("ytd", "1d"),
    "1Y": ("1y", "1wk"),
    "5Y": ("5y", "1mo"),
    "10Y": ("10y", "1mo"),
}

# TTLs per period (seconds) — shorter ranges change more often.
_PERIOD_TTL = {
    "1D": 5 * 60,            # 5 minutes
    "1M": 60 * 60,           # 1 hour
    "6M": 6 * 60 * 60,       # 6 hours
    "YTD": 6 * 60 * 60,      # 6 hours
    "1Y": 24 * 60 * 60,      # 24 hours
    "5Y": 24 * 60 * 60,      # 24 hours
    "10Y": 24 * 60 * 60,     # 24 hours
}


def _label_fmt(period_key: str) -> str:
    """X-axis label format per period. Long ranges include the year."""
    if period_key == "1D":
        return "%H:%M"
    if period_key in ("5Y", "10Y"):
        return "%b %Y"
    return "%m/%d"

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

    # Wrap the whole body: any unexpected failure must become an HTTPException
    # (which keeps CORS headers) rather than an unhandled 500 — an unhandled 500
    # bypasses the CORS middleware and shows up in the browser as "failed to fetch".
    try:
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
                # auto_adjust=True → Close is split/dividend-adjusted, so multi-year
                # returns (e.g. post-split NVDA) are computed on a consistent basis.
                hist = stock.history(period=period, interval=interval, auto_adjust=True)
                fmt = _label_fmt(period_key)
                points = []
                for idx, row in hist.iterrows():
                    close = row["Close"]
                    # Rate-limited responses include NaN rows — skip them so the
                    # response stays JSON-serializable (no NaN/Inf).
                    if close is None or not math.isfinite(float(close)):
                        continue
                    points.append({"time": idx.strftime(fmt), "price": round(float(close), 2)})
                history[period_key] = points
                if points:
                    history_ok = True
                    cache.set_raw(cache_key, points, ttl=_PERIOD_TTL[period_key])
            except Exception as e:
                logger.warning("yfinance history %s failed for %s: %s", period_key, ticker, e)
                history[period_key] = []

        # Final NaN scrub — also cleans cached points from older builds. JSON
        # round-trips NaN as float('nan') (json.dumps writes the literal NaN,
        # json.loads reads it back), so cached series can carry NaN that crashes
        # the response renderer. Filter every point regardless of its source.
        for pk in list(history.keys()):
            history[pk] = [
                {"time": p.get("time"), "price": round(float(p["price"]), 2)}
                for p in (history.get(pk) or [])
                if isinstance(p, dict)
                and p.get("price") is not None
                and math.isfinite(float(p["price"]))
            ]
        history_ok = any(history.values())

        # Prices: prefer info, fall back to the 1D history endpoints.
        one_day = history.get("1D") or []
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        if not current_price and one_day:
            current_price = one_day[-1]["price"]
        if not prev_close and one_day:
            prev_close = one_day[0]["price"]

        # Nothing usable from any source → upstream is throttling us. 503 is retryable.
        if not history_ok and not current_price:
            raise HTTPException(
                status_code=503,
                detail=f"Market data for {ticker} is temporarily unavailable. Please try again shortly.",
            )

        # Sanitize every float so a NaN/Inf can never reach the JSON renderer.
        current_price = _finite(current_price)
        prev_close = _finite(prev_close, current_price)
        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0
        name = _company_name(ticker, info, cache)

        return {
            "ticker": ticker,
            "name": name,
            "price": round(_finite(current_price), 2),
            "change": round(_finite(change), 2),
            "changePercent": round(_finite(change_pct), 2),
            "history": history,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("chart endpoint failed for %s", ticker)
        raise HTTPException(
            status_code=503,
            detail=f"Market data for {ticker} is temporarily unavailable. Please try again shortly.",
        )
