from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from core.cache import get_cache
from core.database import DatabaseManager
from tasks import analyze_sentiment_task

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
