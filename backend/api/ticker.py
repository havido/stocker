from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.cache import get_cache
from core.database import DatabaseManager
from tasks import analyze_sentiment_task
from services.gemini_advisor import get_investment_advice
import yfinance as yf
import redis.asyncio as aioredis
import os
import asyncio
from typing import Any

router = APIRouter()


class AdviseRequest(BaseModel):
    sentiment_data: dict[str, Any]

class TickerRequest(BaseModel):
    ticker: str

@router.post("/ticker", status_code=status.HTTP_202_ACCEPTED)
async def process_ticker(request: TickerRequest):
    ticker = request.ticker
    cache = get_cache()

    # 1. Check cache
    cached = cache.get(ticker)
    if cached:
        return {"status": "hit", "data": cached}

    # 2. Trigger task
    task = await analyze_sentiment_task.kiq(ticker)

    return {"status": "processing", "task_id": task.task_id}

@router.get("/stream/{task_id}")
async def stream_status(task_id: str):
    async def event_generator():
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        client = await aioredis.from_url(redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(f"logs:{task_id}")
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    data = message["data"]
                    yield f"data: {data}\n\n"
                    if data == "DONE":
                        break
        finally:
            await pubsub.unsubscribe(f"logs:{task_id}")
            await client.aclose()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    db = DatabaseManager()
    result = db.get_analysis(task_id)

    if not result:
        return {"status": "pending"}

    return {"status": "completed", "result": result}

@router.get("/stock/{ticker}")
async def get_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        name = info.get("longName") or info.get("shortName") or ticker.upper()
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or current_price
        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        periods_map = {
            "1D": ("1d", "5m"),
            "1W": ("5d", "1h"),
            "1M": ("1mo", "1d"),
            "1Y": ("1y", "1wk"),
            "ALL": ("5y", "1mo"),
        }

        history = {}
        for period_key, (period, interval) in periods_map.items():
            hist = stock.history(period=period, interval=interval)
            fmt = "%H:%M" if period_key == "1D" else "%m/%d"
            history[period_key] = [
                {"time": idx.strftime(fmt), "price": round(float(row["Close"]), 2)}
                for idx, row in hist.iterrows()
            ]

        return {
            "ticker": ticker.upper(),
            "name": name,
            "price": round(float(current_price), 2),
            "change": round(float(change), 2),
            "changePercent": round(float(change_pct), 2),
            "history": history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/advise")
async def get_advice(request: AdviseRequest):
    """
    Accept sentiment analysis results and stock data,
    send them to Gemini, and return the investment recommendation.
    """
    try:
        result = get_investment_advice(request.sentiment_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

