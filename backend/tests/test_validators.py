"""Unit tests for ticker validation.

Shape checks are pure (no I/O). Existence checks hit yfinance + Redis, so they
are mocked here — the validator's *logic* is what we verify, not yfinance.
"""

import pytest

from core import validators


# ── Shape validation (pure) ──────────────────────────────────

@pytest.mark.parametrize("symbol", ["A", "AAPL", "TSLA", "GOOGL", "BRK.B", "BRK-B"])
def test_valid_shapes_accepted(symbol):
    assert validators.is_valid_shape(symbol) is True


@pytest.mark.parametrize(
    "symbol",
    [
        "",            # empty
        "ASDFGH",      # 6 letters — too long for a base symbol
        "AA PL",       # space
        "AA!",         # punctuation
        "123",         # digits
        "aapl",        # lowercase (caller must normalize first)
    ],
)
def test_invalid_shapes_rejected(symbol):
    assert validators.is_valid_shape(symbol) is False


# ── validate_ticker (normalize + shape + existence) ──────────

def test_validate_ticker_normalizes_and_accepts_known(monkeypatch):
    monkeypatch.setattr(validators, "ticker_exists", lambda t: True)
    assert validators.validate_ticker("  aapl ") == "AAPL"


def test_validate_ticker_rejects_empty():
    with pytest.raises(ValueError, match="required"):
        validators.validate_ticker("   ")


def test_validate_ticker_rejects_bad_shape_without_network(monkeypatch):
    # Existence check must never run for a malformed symbol.
    called = {"hit": False}

    def _boom(_t):
        called["hit"] = True
        return True

    monkeypatch.setattr(validators, "ticker_exists", _boom)
    with pytest.raises(ValueError, match="not a valid ticker"):
        validators.validate_ticker("ASDFGH")
    assert called["hit"] is False


def test_validate_ticker_rejects_unknown_symbol(monkeypatch):
    monkeypatch.setattr(validators, "ticker_exists", lambda t: False)
    with pytest.raises(ValueError, match="not a recognized ticker"):
        validators.validate_ticker("ZZZZ")
