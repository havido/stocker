import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from broker import broker
from taskiq.kicker import AsyncKicker
from api.v1 import auth, analysis, stocks, watchlist

# Keep the old router for backward compatibility during migration
from api import ticker as ticker_legacy

logger = logging.getLogger(__name__)

# Popular tickers to pre-warm on startup
PREWARM_TICKERS = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]

# Pre-warming enqueues heavy ML jobs on every boot/deploy, so it's opt-in.
PREWARM_ON_STARTUP = os.environ.get("PREWARM_ON_STARTUP", "false").lower() == "true"

# CORS: comma-separated allowlist (e.g. the Vercel URL). Defaults to "*" for
# local dev. Auth is Bearer-token (not cookies), so credentials stay off — which
# also keeps a wildcard origin valid for browsers.
def _parse_origins(raw: str) -> list[str]:
    """Split a comma list, tolerating quotes/trailing slashes from dashboards/.env."""
    origins = []
    for part in raw.split(","):
        cleaned = part.strip().strip('"').strip("'").rstrip("/")
        if cleaned:
            origins.append(cleaned)
    return origins


_origins_env = os.environ.get("ALLOWED_ORIGINS", "*").strip().strip('"').strip("'")
ALLOWED_ORIGINS = ["*"] if _origins_env in ("", "*") else _parse_origins(_origins_env)

# Belt-and-suspenders: always allow Vercel deployments (production + preview) and
# localhost dev via regex, regardless of the explicit allowlist — so a wrong/empty
# ALLOWED_ORIGINS env var can't silently break the frontend with a CORS failure.
ALLOWED_ORIGIN_REGEX = r"https://([a-z0-9-]+\.)*vercel\.app|http://localhost:\d+"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: optionally pre-warm cache for popular tickers.
    # Use AsyncKicker to avoid importing tasks.py (heavy ML deps).
    if PREWARM_ON_STARTUP:
        kicker = AsyncKicker(task_name="tasks:analyze_sentiment_task", broker=broker, labels={})
        for t in PREWARM_TICKERS:
            try:
                from core.cache import get_cache
                cache = get_cache()
                if not cache.get(t):
                    await kicker.kiq(t)
                    logger.info("Pre-warming cache for $%s", t)
            except Exception as e:
                logger.warning("Pre-warm failed for %s: %s", t, e)
    yield

app = FastAPI(title="Stock Sentiment Analysis API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── v1 API routes ───────────────────────────────────────────
app.include_router(auth.router, prefix="/v1")
app.include_router(analysis.router, prefix="/v1")
app.include_router(stocks.router, prefix="/v1")
app.include_router(watchlist.router, prefix="/v1")

# ── Legacy routes (kept for backward compat during frontend migration) ──
app.include_router(ticker_legacy.router, prefix="/api")

@app.get("/")
@app.head("/")
def read_root():
    return {"message": "Welcome to Stock Sentiment Analysis API"}

@app.get("/health")
@app.head("/health")
def healthcheck():
    return {"status": "ok"}
