from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from core.cache import get_cache
from core.database import DatabaseManager
from tasks import analyze_sentiment_task
import yfinance as yf

router = APIRouter()

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
