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

        def history(self, period, interval):
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
