import taskiq_redis
from taskiq import TaskiqEvents
import asyncio
from services.scraper import StockScraper
from services.sentiment import SentimentAnalyzer
from core.database import DatabaseManager

broker = taskiq_redis.ListQueueBroker("redis://redis:6379/0")

from taskiq import Context, TaskiqDepends

@broker.task
async def analyze_sentiment_task(ticker: str, context: Context = TaskiqDepends()):
    scraper = StockScraper()
    sentiment = SentimentAnalyzer()
    db = DatabaseManager()
    
    # 1. Scrape
    text = await scraper.fetch_data(ticker)
    
    # 2. Analyze
    score = sentiment.analyze(text)
    
    # 3. Save
    db.save_analysis(context.message.task_id, score)
    
    return {"ticker": ticker, "score": score}

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state):
    print("Worker started")
