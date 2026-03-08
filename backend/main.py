from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from broker import broker
from taskiq.kicker import AsyncKicker
from api import ticker

# Popular tickers to pre-warm on startup
PREWARM_TICKERS = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: pre-warm cache for popular tickers
    # Use AsyncKicker to avoid importing tasks.py (heavy ML deps)
    kicker = AsyncKicker(task_name="tasks:analyze_sentiment_task", broker=broker, labels={})
    for t in PREWARM_TICKERS:
        try:
            from core.cache import get_cache
            cache = get_cache()
            if not cache.get(t):
                await kicker.kiq(t)
                print(f"Pre-warming cache for ${t}")
        except Exception as e:
            print(f"Pre-warm failed for {t}: {e}")
    yield

app = FastAPI(title="Stock Sentiment Analysis API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ticker.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to Stock Sentiment Analysis API"}

@app.get("/health")
def healthcheck():
    return {"status": "ok"}

