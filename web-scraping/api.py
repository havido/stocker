"""
Stocker REST API — FastAPI wrapper around the sentiment analysis pipeline.

Start the server:
    uvicorn api:app --reload

Endpoints:
    GET /sentiment/{ticker}   — Run (or fetch cached) sentiment analysis
    GET /health               — Health check
    GET /docs                 — Auto-generated interactive docs (Swagger UI)
"""

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware

from main import analyze_ticker, CACHE_AVAILABLE

app = FastAPI(
    title="Stocker Sentiment API",
    description="Scrapes Reddit & Yahoo Finance and runs FinBERT sentiment analysis on a given stock ticker.",
    version="0.1.0",
)

# Allow any frontend (e.g. a React app on localhost:3000) to call this API.
# Tighten origins before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Quick liveness check — also reports whether Redis is connected."""
    return {"status": "ok", "cache": "connected" if CACHE_AVAILABLE else "unavailable"}


@app.get("/sentiment/{ticker}")
def get_sentiment(
    ticker: str = Path(
        ...,
        description="Stock ticker symbol, e.g. AAPL or NVDA",
        min_length=1,
        max_length=10,
    )
):
    """
    Return sentiment analysis for a given ticker.

    - **Cache hit**: responds in ~10 ms (result was cached in Redis within the last hour).
    - **Cache miss**: runs the full scrape + FinBERT pipeline (~1–2 min), then caches the result.
    """
    try:
        result = analyze_ticker(ticker.upper())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
