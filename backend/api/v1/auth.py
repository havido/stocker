"""
Authentication endpoints.

Uses Supabase Auth for registration and login.
Returns the Supabase session (access_token + refresh_token).
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from core.supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

_AUTH_UNAVAILABLE = "Authentication service is temporarily unavailable. Please try again."


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: AuthRequest):
    """Register a new user with email + password."""
    try:
        supabase = get_supabase()
        result = supabase.auth.sign_up({"email": body.email, "password": body.password})

        if result.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed — check email format or try a different email.",
            )

        session = result.session
        if session is None:
            # Supabase may require email confirmation before issuing a session.
            # Return a 201 with a placeholder so the frontend knows to prompt.
            return AuthResponse(
                access_token="",
                refresh_token="",
                user_id=result.user.id,
                email=result.user.email or body.email,
            )

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user_id=result.user.id,
            email=result.user.email or body.email,
        )
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        # Network/TLS failure reaching Supabase — not the user's fault.
        logger.warning("register transport error for %s: %s", body.email, e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AUTH_UNAVAILABLE)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=AuthResponse)
async def login(body: AuthRequest):
    """Log in with email + password. Returns JWT tokens."""
    try:
        supabase = get_supabase()
        result = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )

        if result.user is None or result.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        return AuthResponse(
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
            user_id=result.user.id,
            email=result.user.email or body.email,
        )
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        # Network/TLS failure reaching Supabase — surface as 503, not a bogus
        # "invalid password", so the user knows to retry rather than reset.
        logger.warning("login transport error for %s: %s", body.email, e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AUTH_UNAVAILABLE)
    except Exception as e:
        # An unconfirmed email is not a credential error — tell the user to
        # confirm instead of sending them to reset a password that's fine.
        if getattr(e, "code", None) == "email_not_confirmed":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please confirm your email address first — check your inbox for the confirmation link.",
            )
        logger.info("login failed for %s: %s", body.email, e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
