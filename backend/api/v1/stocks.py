"""
Stock data endpoints (v1).

Serves historical price charts with Redis caching.
"""

from fastapi import APIRouter, HTTPException
from core.cache import CacheManager
import yfinance as yf

router = APIRouter(tags=["stocks"])

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


@router.get("/stocks/{ticker}/chart")
async def get_stock_chart(ticker: str):
    """
    Return historical price data for all periods.
    Caches each period independently with tiered TTLs.
    """
    ticker = ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    cache = CacheManager()

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        name = info.get("longName") or info.get("shortName") or ticker
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or current_price
        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        history = {}
        for period_key, (period, interval) in _PERIODS_MAP.items():
            cache_key = f"stock:{ticker}:{period_key}"
            cached = cache.get_raw(cache_key)

            if cached is not None:
                history[period_key] = cached
                continue

            hist = stock.history(period=period, interval=interval)
            fmt = "%H:%M" if period_key == "1D" else "%m/%d"
            points = [
                {"time": idx.strftime(fmt), "price": round(float(row["Close"]), 2)}
                for idx, row in hist.iterrows()
            ]
            history[period_key] = points
            cache.set_raw(cache_key, points, ttl=_PERIOD_TTL[period_key])

        return {
            "ticker": ticker,
            "name": name,
            "price": round(float(current_price), 2),
            "change": round(float(change), 2),
            "changePercent": round(float(change_pct), 2),
            "history": history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
