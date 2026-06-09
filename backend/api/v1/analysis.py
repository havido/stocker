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
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import redis.asyncio as aioredis

from broker import broker
from taskiq.kicker import AsyncKicker
from core.cache import CacheManager
from core.supabase_client import get_supabase_admin

router = APIRouter(tags=["analysis"])

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
    ticker = request.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

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
    except Exception:
        pass  # Supabase down → fall through to enqueue

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
    except Exception:
        pass  # Non-fatal — the worker will create it if needed

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
            last_msg_time = asyncio.get_event_loop().time()
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )

                now = asyncio.get_event_loop().time()

                if message:
                    data = message["data"]
                    last_msg_time = now
                    yield f"data: {data}\n\n"
                    if data == "DONE":
                        break
                else:
                    # Heartbeat every 15s to prevent proxy/ALB timeouts
                    if now - last_msg_time > 15:
                        yield ": keepalive\n\n"
                        last_msg_time = now

                    # Hard timeout: 120s with no DONE
                    if now - last_msg_time > 120:
                        yield 'data: {"step": "timeout", "message": "Analysis timed out"}\n\n'
                        break
        finally:
            await pubsub.unsubscribe(f"logs:{job_id}")
            await client.aclose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
    except Exception:
        pass

    return {"status": "not_found"}
