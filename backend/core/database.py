"""
Database manager.

Handles persistence to Supabase (PostgreSQL) for analysis jobs,
and Redis Pub/Sub for ephemeral streaming logs.
"""

import redis
import json
import logging
import os

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._supabase = None

    @property
    def supabase(self):
        """Lazy-load Supabase client (avoids import overhead in lightweight contexts)."""
        if self._supabase is None:
            from core.supabase_client import get_supabase_admin
            self._supabase = get_supabase_admin()
        return self._supabase

    # ── Analysis job persistence ─────────────────────────────

    def save_analysis(self, task_id: str, ticker: str, data: dict):
        """
        Save completed analysis to Supabase and mark job as completed.
        Falls back to Redis-only if Supabase is unavailable.
        """
        try:
            self.supabase.table("analysis_jobs").upsert({
                "id": task_id,
                "ticker": ticker,
                "status": "completed",
                "result": data,
            }).execute()
        except Exception as e:
            logger.warning("Supabase write failed for %s, falling back to Redis: %s", task_id, e)
            self._redis.set(f"db:{task_id}", json.dumps(data))

    def update_job_status(self, task_id: str, status: str):
        """Update the status field of an analysis job."""
        try:
            self.supabase.table("analysis_jobs").update({
                "status": status,
            }).eq("id", task_id).execute()
        except Exception as e:
            logger.warning("Could not update status=%s for %s: %s", status, task_id, e)

    def get_analysis(self, task_id: str) -> dict | None:
        """Fetch analysis result by task_id."""
        # Try Supabase first
        try:
            result = (
                self.supabase.table("analysis_jobs")
                .select("result")
                .eq("id", task_id)
                .eq("status", "completed")
                .limit(1)
                .execute()
            )
            if result.data and result.data[0].get("result"):
                return result.data[0]["result"]
        except Exception as e:
            logger.warning("get_analysis Supabase lookup failed for %s: %s", task_id, e)

        # Fall back to Redis
        val = self._redis.get(f"db:{task_id}")
        if val:
            return json.loads(val)
        return None

    # ── Pub/Sub (ephemeral logs — stays on Redis) ────────────

    def publish_log(self, identifier: str, message: str):
        """Publish a log message to Redis Pub/Sub for SSE streaming."""
        self._redis.publish(f"logs:{identifier}", message)
