"""
Authentication endpoints.

Uses Supabase Auth for registration and login.
Returns the Supabase session (access_token + refresh_token).
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from core.supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])


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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
