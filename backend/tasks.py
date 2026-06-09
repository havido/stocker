"""
TaskIQ worker tasks.

This module is ONLY loaded by the Worker process.
The API server never imports this file — it uses AsyncKicker
to push tasks by name through the shared broker.
"""
import os
import sys

# Ensure submodules are importable from /app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from broker import broker  # re-export so `taskiq worker tasks:broker` works
from taskiq import TaskiqEvents, Context, TaskiqDepends
from core.database import DatabaseManager


@broker.task
async def analyze_sentiment_task(ticker: str, context: Context = TaskiqDepends()):
    # Lazy-import heavy modules so they only load when a task actually runs
    from services.sentiment import SentimentAnalyzer

    sentiment = SentimentAnalyzer()
    db = DatabaseManager()

    task_id = context.message.task_id

    def log_cb(msg):
        db.publish_log(task_id, msg)

    # Mark job as running
    db.update_job_status(task_id, "running")

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

    # 3. FinBERT Sentiment Analysis
    db.publish_log(task_id, f'{{"step": "sentiment", "message": "Starting FinBERT sentiment analysis..."}}')
    score = sentiment.analyze(text, log_callback=log_cb)

    # 4. Gemini AI Summary
    ai_summary = ""
    try:
        from services.gemini_summarizer import generate_summary
        ai_summary = generate_summary(
            ticker=ticker,
            sentiment_summary=score,
            sample_texts=text,
            log_callback=log_cb,
        )
    except Exception as e:
        db.publish_log(task_id, f'{{"step": "gemini", "message": "AI summary skipped: {e}"}}')

    # 5. Build final result
    score["ai_summary"] = ai_summary

    # 6. Save to Supabase (by task_id with ticker) AND Cache (by ticker with TTL)
    db.publish_log(task_id, f'{{"step": "saving", "message": "Analysis complete. Caching results..."}}')
    db.save_analysis(task_id, ticker, score)

    from core.cache import CacheManager
    cache = CacheManager()
    cache.set(ticker, score)

    db.publish_log(task_id, "DONE")

    return {"ticker": ticker, "score": score}


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state):
    print("Worker started")
