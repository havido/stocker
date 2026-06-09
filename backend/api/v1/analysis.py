"""
Analysis endpoints (v1).

Handles the analysis job lifecycle:
  POST /v1/analysis/jobs        → cache-first, then enqueue
  GET  /v1/analysis/jobs/{id}/stream → SSE live updates
  GET  /v1/stocks/{ticker}/sentiment → fetch completed result
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import redis.asyncio as aioredis

from broker import broker
from taskiq.kicker import AsyncKicker
from core.cache import CacheManager
from core.supabase_client import get_supabase_admin
from core.validators import validate_ticker
from core.sentinels import SUCCESS_SENTINEL, FAILURE_SENTINEL

router = APIRouter(tags=["analysis"])

logger = logging.getLogger(__name__)

CACHE_FRESHNESS_MINUTES = 15


class AnalysisRequest(BaseModel):
    ticker: str


# ── POST /v1/analysis/jobs ──────────────────────────────────

@router.post("/analysis/jobs")
async def create_analysis_job(request: AnalysisRequest):
    """
    Cache-first analysis trigger.

    1. Check Redis cache → 200 (instant)
    2. Check Supabase for recent (<15 min) completed job → 200
    3. Else enqueue a new TaskIQ job → 202 Accepted
    """
    # Validate + normalize before doing any work. Rejects junk (bad shape) and
    # unknown symbols with a 400 so they never reach the worker.
    try:
        ticker = validate_ticker(request.ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 1. Redis cache check
    cache = CacheManager()
    cached = cache.get(ticker)
    if cached:
        return {"status": "hit", "data": cached}

    # 2. Supabase recent-job check
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=CACHE_FRESHNESS_MINUTES)).isoformat()
        sb = get_supabase_admin()
        recent = (
            sb.table("analysis_jobs")
            .select("id, result")
            .eq("ticker", ticker)
            .eq("status", "completed")
            .gte("updated_at", cutoff)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if recent.data and recent.data[0].get("result"):
            result = recent.data[0]["result"]
            # Re-populate cache so next hit is instant
            cache.set(ticker, result)
            return {"status": "hit", "data": result}
    except Exception as e:
        logger.warning("Supabase recent-job lookup failed for %s: %s", ticker, e)
        # Fall through to enqueue a fresh job.

    # 3. Enqueue new job
    kicker = AsyncKicker(task_name="tasks:analyze_sentiment_task", broker=broker, labels={})
    task = await kicker.kiq(ticker)

    # Create pending row in Supabase
    try:
        sb = get_supabase_admin()
        sb.table("analysis_jobs").upsert({
            "id": task.task_id,
            "ticker": ticker,
            "status": "pending",
        }).execute()
    except Exception as e:
        logger.warning("Could not create pending row for %s: %s", task.task_id, e)
        # Non-fatal — the worker will create/update the row when it runs.

    return {
        "status": "processing",
        "task_id": task.task_id,
    }


# ── GET /v1/analysis/jobs/{job_id}/stream ───────────────────

@router.get("/analysis/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    """SSE stream of live progress updates from the worker via Redis Pub/Sub."""

    async def event_generator():
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        client = await aioredis.from_url(redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(f"logs:{job_id}")

        try:
            # Two separate clocks: last real message (for the hard timeout) and
            # last heartbeat (for proxy keepalive). Keeping them separate means
            # the keepalive can't keep resetting the timeout and stall forever.
            last_msg_time = asyncio.get_event_loop().time()
            last_beat = last_msg_time
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )

                now = asyncio.get_event_loop().time()

                if message:
                    data = message["data"]
                    last_msg_time = now
                    last_beat = now
                    yield f"data: {data}\n\n"
                    # Either terminal sentinel ends the stream.
                    if data in (SUCCESS_SENTINEL, FAILURE_SENTINEL):
                        break
                else:
                    # Heartbeat every 15s to prevent proxy/ALB timeouts
                    if now - last_beat > 15:
                        yield ": keepalive\n\n"
                        last_beat = now

                    # Hard timeout: 120s with no real message → emit a terminal
                    # failure so the client shows an error instead of hanging.
                    if now - last_msg_time > 120:
                        yield 'data: {"step": "timeout", "message": "Analysis timed out after 120s"}\n\n'
                        yield f"data: {FAILURE_SENTINEL}\n\n"
                        break
        finally:
            await pubsub.unsubscribe(f"logs:{job_id}")
            await client.aclose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── GET /v1/analysis/jobs/{job_id} ──────────────────────────

@router.get("/analysis/jobs/{job_id}")
async def get_job_result(job_id: str):
    """
    Fetch a job's status and (when completed) its result, keyed by task_id.

    Replaces the legacy /api/status/{task_id} endpoint. Supabase first, with a
    Redis fallback for the case where the worker had to write results to Redis
    because Supabase was unavailable.
    """
    try:
        sb = get_supabase_admin()
        rows = (
            sb.table("analysis_jobs")
            .select("status, result")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        if rows.data:
            row = rows.data[0]
            status_val = row.get("status", "pending")
            result = row.get("result")
            if status_val == "completed" and result:
                return {"status": "completed", "result": result}
            return {"status": status_val}
    except Exception as e:
        logger.warning("get_job_result Supabase lookup failed for %s: %s", job_id, e)

    # Redis fallback — worker writes db:{task_id} when Supabase is down.
    raw = CacheManager().get_raw(f"db:{job_id}")
    if raw:
        return {"status": "completed", "result": raw}

    return {"status": "not_found"}


# ── GET /v1/stocks/{ticker}/sentiment ───────────────────────

@router.get("/stocks/{ticker}/sentiment")
async def get_sentiment(ticker: str):
    """Fetch the most recent completed sentiment result for a ticker."""
    ticker = ticker.upper().strip()

    # Try cache first
    cache = CacheManager()
    cached = cache.get(ticker)
    if cached:
        return {"status": "completed", "result": cached}

    # Try Supabase
    try:
        sb = get_supabase_admin()
        rows = (
            sb.table("analysis_jobs")
            .select("id, result, updated_at")
            .eq("ticker", ticker)
            .eq("status", "completed")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if rows.data and rows.data[0].get("result"):
            result = rows.data[0]["result"]
            cache.set(ticker, result)
            return {"status": "completed", "result": result}
    except Exception as e:
        logger.warning("get_sentiment Supabase lookup failed for %s: %s", ticker, e)

    return {"status": "not_found"}
