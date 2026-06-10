"""
Regression test for the chart endpoint's NaN-serialization crash.

Rate-limited yfinance responses return price history containing NaN. Those NaN
floats reached the response dict and crashed Starlette's JSON renderer
(allow_nan=False) with an unhandled 500 — which bypassed CORS and showed in the
browser as "failed to fetch". The endpoint must drop NaN and stay serializable.
"""

import asyncio
import json
import math

import pandas as pd

from api.v1 import stocks


def test_periods_match_spec():
    assert list(stocks._PERIODS_MAP.keys()) == ["1D", "1M", "6M", "YTD", "1Y", "5Y", "10Y"]
    # Every period must have a TTL.
    assert set(stocks._PERIOD_TTL.keys()) == set(stocks._PERIODS_MAP.keys())


def test_label_fmt_is_year_aware_for_long_ranges():
    assert stocks._label_fmt("1D") == "%H:%M"
    assert stocks._label_fmt("1M") == "%m/%d"
    assert "%Y" in stocks._label_fmt("5Y")
    assert "%Y" in stocks._label_fmt("10Y")


def test_endpoint_returns_all_spec_periods(monkeypatch):
    class FakeStock:
        @property
        def info(self):
            return {"longName": "Apple Inc.", "currentPrice": 200.0, "previousClose": 198.0}

        def history(self, period, interval, **kwargs):
            idx = pd.to_datetime(["2026-06-09", "2026-06-10"])
            return pd.DataFrame({"Close": [198.0, 200.0]}, index=idx)

    class FakeCache:
        def get_raw(self, k):
            return None

        def set_raw(self, k, v, ttl=None):
            pass

    monkeypatch.setattr(stocks.yf, "Ticker", lambda t: FakeStock())
    monkeypatch.setattr(stocks, "CacheManager", lambda: FakeCache())

    result = asyncio.run(stocks.get_stock_chart("AAPL"))
    assert list(result["history"].keys()) == ["1D", "1M", "6M", "YTD", "1Y", "5Y", "10Y"]
    assert all(len(v) == 2 for v in result["history"].values())


def test_finite_coerces_nan_inf_none():
    assert stocks._finite(float("nan")) == 0.0
    assert stocks._finite(float("inf")) == 0.0
    assert stocks._finite(None) == 0.0
    assert stocks._finite("notnum", 5.0) == 5.0
    assert stocks._finite(3.14) == 3.14


def test_chart_output_is_json_serializable_despite_nan_history(monkeypatch):
    class FakeStock:
        @property
        def info(self):
            raise RuntimeError("Too Many Requests. Rate limited.")

        def history(self, period, interval, **kwargs):
            idx = pd.to_datetime(
                ["2026-06-10 09:30", "2026-06-10 09:35", "2026-06-10 09:40"]
            )
            return pd.DataFrame({"Close": [100.0, float("nan"), 102.5]}, index=idx)

    class FakeCache:
        def get_raw(self, k):
            return None

        def set_raw(self, k, v, ttl=None):
            pass

    monkeypatch.setattr(stocks.yf, "Ticker", lambda t: FakeStock())
    monkeypatch.setattr(stocks.yf, "Search", lambda t: type("S", (), {"quotes": []})())
    monkeypatch.setattr(stocks, "CacheManager", lambda: FakeCache())

    result = asyncio.run(stocks.get_stock_chart("AAPL"))

    # Must serialize with allow_nan=False (exactly how Starlette renders it).
    json.dumps(result, allow_nan=False)

    # The NaN row is dropped → 2 valid points; prices are finite.
    assert len(result["history"]["1D"]) == 2
    assert all(math.isfinite(p["price"]) for p in result["history"]["1D"])
    assert math.isfinite(result["price"])


def test_cached_nan_points_are_scrubbed(monkeypatch):
    """A cache hit returning NaN-laden points (from an older build) must still
    produce a JSON-serializable response."""

    class FakeStock:
        @property
        def info(self):
            raise RuntimeError("Too Many Requests")

        def history(self, period, interval, **kwargs):
            return pd.DataFrame({"Close": []})

    # Only the price-series keys (stock:*) hold cached points; an older build
    # cached NaN into them. Name/other keys behave normally.
    class NaNCache:
        def get_raw(self, k):
            if k.startswith("stock:"):
                return [
                    {"time": "09:30", "price": 100.0},
                    {"time": "09:35", "price": float("nan")},
                ]
            return None

        def set_raw(self, k, v, ttl=None):
            pass

    monkeypatch.setattr(stocks.yf, "Ticker", lambda t: FakeStock())
    monkeypatch.setattr(stocks.yf, "Search", lambda t: type("S", (), {"quotes": []})())
    monkeypatch.setattr(stocks, "CacheManager", lambda: NaNCache())

    result = asyncio.run(stocks.get_stock_chart("AAPL"))
    json.dumps(result, allow_nan=False)  # must not raise
    assert all(math.isfinite(p["price"]) for pts in result["history"].values() for p in pts)
