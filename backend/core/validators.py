"""
Ticker validation.

Two layers:
  1. is_valid_shape() — a pure, cheap regex pre-filter (rejects obvious junk).
  2. ticker_exists()  — a network existence check via yfinance, cached in Redis
                        so we don't pay the lookup on every request.

validate_ticker() composes both and returns the normalized symbol or raises
ValueError with a user-facing message.
"""

import logging
import re

from core.cache import CacheManager

logger = logging.getLogger(__name__)

# 1–5 letters, optional class/exchange suffix (e.g. BRK.B, BRK-B).
_TICKER_SHAPE = re.compile(r"^[A-Z]{1,5}([.\-][A-Z]{1,2})?$")

# Cache existence results so repeat lookups are instant. Positives live longer
# than negatives so a transient yfinance hiccup can't block a real ticker for a
# full day.
_VALID_TTL = 24 * 60 * 60   # 24h for "exists"
_INVALID_TTL = 60 * 60      # 1h for "does not exist"


def is_valid_shape(ticker: str) -> bool:
    """True if the symbol looks like a ticker. Pure — no I/O."""
    return bool(_TICKER_SHAPE.match(ticker))


def ticker_exists(ticker: str) -> bool:
    """
    Confirm a ticker resolves to a real instrument via yfinance.

    Result is cached in Redis (key `tickervalid:{TICKER}`). yfinance is imported
    lazily so this module stays importable in lightweight contexts.
    """
    cache = CacheManager()
    cache_key = f"tickervalid:{ticker}"

    cached = cache.get_raw(cache_key)
    if cached is not None:
        return bool(cached)

    exists = False
    try:
        import yfinance as yf

        last_price = yf.Ticker(ticker).fast_info.last_price
        exists = last_price is not None
    except Exception as e:
        # Network/parse failure → treat as "not found" but cache only briefly.
        logger.warning("ticker_exists(%s) lookup failed: %s", ticker, e)
        exists = False

    cache.set_raw(cache_key, 1 if exists else 0, ttl=_VALID_TTL if exists else _INVALID_TTL)
    return exists


def validate_ticker(ticker: str) -> str:
    """
    Normalize and validate a ticker.

    Returns the clean uppercase symbol, or raises ValueError with a message
    suitable for returning to the client.
    """
    clean = ticker.upper().strip()
    if not clean:
        raise ValueError("Ticker is required")
    if not is_valid_shape(clean):
        raise ValueError(f"'{ticker.strip()}' is not a valid ticker symbol")
    if not ticker_exists(clean):
        raise ValueError(f"'{clean}' is not a recognized ticker")
    return clean
