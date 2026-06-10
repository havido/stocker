"""Tests for the Groq-backed AI summarizer (HTTP mocked — no real API calls)."""

from services import ai_summarizer as ai


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_returns_model_content(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        ai.requests,
        "post",
        lambda *a, **k: _FakeResp(
            {"choices": [{"message": {"content": "## Bull Case\n- strong demand"}}]}
        ),
    )
    out = ai.generate_summary("AAPL", {"positive": 5, "grade": "Buy"}, ["some source text"])
    assert "Bull Case" in out


def test_returns_empty_on_api_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    def boom(*a, **k):
        raise RuntimeError("429 quota exceeded")

    monkeypatch.setattr(ai.requests, "post", boom)
    assert ai.generate_summary("AAPL", {}, []) == ""


def test_returns_empty_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert ai.generate_summary("AAPL", {}, []) == ""
