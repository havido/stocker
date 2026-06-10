"""Tests for source collection (the 'sources used to grade this' feature)."""

from tasks import _collect_sources


def test_flattens_reddit_then_yahoo_preserving_order():
    reddit = [{"title": "R1", "url": "http://r/1"}, {"title": "R2", "url": "http://r/2"}]
    yahoo = [{"title": "Y1", "url": "http://y/1"}]
    out = _collect_sources(reddit, yahoo)
    assert [s["url"] for s in out] == ["http://r/1", "http://r/2", "http://y/1"]
    assert out[0]["source"] == "reddit"
    assert out[-1]["source"] == "yahoo"


def test_dedupes_by_url_and_drops_items_without_url():
    reddit = [
        {"title": "R1", "url": "http://r/1"},
        {"title": "dup", "url": "http://r/1"},   # duplicate URL
        {"title": "no url"},                       # missing URL
    ]
    out = _collect_sources(reddit, [])
    assert len(out) == 1
    assert out[0]["url"] == "http://r/1"


def test_truncates_long_titles_to_200_chars():
    out = _collect_sources([{"title": "x" * 500, "url": "http://r/1"}], [])
    assert len(out[0]["title"]) == 200


def test_respects_limit():
    reddit = [{"title": f"R{i}", "url": f"http://r/{i}"} for i in range(50)]
    out = _collect_sources(reddit, [], limit=10)
    assert len(out) == 10


def test_handles_empty_and_none():
    assert _collect_sources(None, None) == []
    assert _collect_sources([], []) == []
