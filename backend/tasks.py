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
    
    task_id = context.message.task_id

    def log_cb(msg):
        db.publish_log(task_id, msg)

    # 1. Scrape Reddit
    db.publish_log(task_id, f'{{"step": "reddit", "message": "Scraping Reddit for {ticker}..."}}')
    from services.reddit_scraper import scrape_reddit
    reddit_posts = scrape_reddit(ticker, log_callback=log_cb)
    
    # 2. Scrape Yahoo
    db.publish_log(task_id, f'{{"step": "yahoo", "message": "Scraping Yahoo Finance for {ticker}..."}}')
    from services.yahoo_scraper import scrape_yahoo
    yahoo_articles = scrape_yahoo(ticker, log_callback=log_cb)
    
    # Collect texts
    texts = []
    for post in reddit_posts:
        combined = f"{post.get('title', '')}. {post.get('selftext', '')}".strip()
        if combined:
            texts.append(combined)
        texts.extend([c for c in post.get("comments", []) if c.strip()])
        
    for article in yahoo_articles:
        combined = f"{article.get('title', '')}. {article.get('body', '')}".strip()
        if combined:
            texts.append(combined)
            
    text = [t for t in texts if t]
    
    # 3. Analyze
    db.publish_log(task_id, f'{{"step": "sentiment", "message": "Starting FinBERT sentiment analysis..."}}')
    score = sentiment.analyze(text, log_callback=log_cb)
    
    # 4. Save
    db.publish_log(task_id, f'{{"step": "saving", "message": "Analysis complete. Sending to UI..."}}')
    db.save_analysis(task_id, score)
    db.publish_log(task_id, "DONE")
    
    return {"ticker": ticker, "score": score}

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state):
    print("Worker started")
