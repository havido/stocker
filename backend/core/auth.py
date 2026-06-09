"""
JWT authentication dependency for FastAPI.

Validates the Supabase-issued JWT from the `Authorization: Bearer <token>` header.
Uses the Supabase client's `auth.get_user()` for validation, which also confirms
the token hasn't been revoked.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from core.supabase_client import get_supabase

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """
    FastAPI dependency that extracts and validates the JWT.

    Returns the Supabase user dict on success.
    Raises 401 if missing/invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = credentials.credentials
    try:
        supabase = get_supabase()
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if user is None:
            raise ValueError("No user returned")
        return {
            "id": user.id,
            "email": user.email,
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict | None:
    """Like get_current_user but returns None instead of 401 for unauthenticated."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
