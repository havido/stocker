"""
Redis cache layer.

Provides both typed sentiment caching (get/set by ticker)
and generic raw caching (get_raw/set_raw for arbitrary JSON).
"""

import redis
import json
import os

CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


class CacheManager:
    def __init__(self):
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    # ── Sentiment cache (keyed by ticker) ────────────────────

    def get(self, ticker: str) -> dict | None:
        """Get cached sentiment result for a ticker. Returns None on miss."""
        val = self.client.get(f"cache:{ticker.upper()}")
        if val:
            return json.loads(val)
        return None

    def set(self, ticker: str, data: dict, ttl: int = CACHE_TTL_SECONDS):
        """Cache a sentiment result with TTL."""
        self.client.setex(
            f"cache:{ticker.upper()}",
            ttl,
            json.dumps(data),
        )

    # ── Generic cache (arbitrary key) ────────────────────────

    def get_raw(self, key: str) -> any:
        """Get a cached value by arbitrary key. Returns None on miss."""
        val = self.client.get(key)
        if val:
            return json.loads(val)
        return None

    def set_raw(self, key: str, data, ttl: int = CACHE_TTL_SECONDS):
        """Cache any JSON-serializable value with TTL."""
        self.client.setex(key, ttl, json.dumps(data))


def get_cache():
    return CacheManager()
