"""
Watchlist endpoints (v1).

All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from core.auth import get_current_user
from core.supabase_client import get_supabase_admin

router = APIRouter(tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    ticker: str


@router.get("/users/watchlist")
async def get_watchlist(user: dict = Depends(get_current_user)):
    """Get the authenticated user's watchlist."""
    sb = get_supabase_admin()
    result = (
        sb.table("watchlist_items")
        .select("ticker, added_at")
        .eq("user_id", user["id"])
        .order("added_at", desc=True)
        .execute()
    )
    return {"items": result.data or []}


@router.post("/users/watchlist", status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(body: WatchlistAddRequest, user: dict = Depends(get_current_user)):
    """Add a ticker to the user's watchlist. Duplicate tickers are ignored."""
    ticker = body.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    sb = get_supabase_admin()
    try:
        sb.table("watchlist_items").upsert(
            {"user_id": user["id"], "ticker": ticker},
            on_conflict="user_id,ticker",
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ticker": ticker, "status": "added"}


@router.delete("/users/watchlist/{ticker}", status_code=status.HTTP_200_OK)
async def remove_from_watchlist(ticker: str, user: dict = Depends(get_current_user)):
    """Remove a ticker from the user's watchlist."""
    ticker = ticker.upper().strip()
    sb = get_supabase_admin()
    sb.table("watchlist_items").delete().eq("user_id", user["id"]).eq("ticker", ticker).execute()
    return {"ticker": ticker, "status": "removed"}
