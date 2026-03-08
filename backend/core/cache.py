import redis
import json
import os

CACHE_TTL_SECONDS = 15 * 60  # 15 minutes

class CacheManager:
    def __init__(self):
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, ticker: str) -> dict | None:
        """Get cached sentiment result for a ticker. Returns None on miss."""
        val = self.client.get(f"cache:{ticker.upper()}")
        if val:
            return json.loads(val)
        return None

    def set(self, ticker: str, data: dict):
        """Cache a sentiment result with TTL."""
        self.client.setex(
            f"cache:{ticker.upper()}",
            CACHE_TTL_SECONDS,
            json.dumps(data),
        )

def get_cache():
    return CacheManager()
