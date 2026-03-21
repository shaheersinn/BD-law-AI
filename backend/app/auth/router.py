"""
app/auth/router.py — Authentication endpoints.

POST /api/auth/login           → access + refresh tokens
POST /api/auth/refresh         → new access token from refresh token
POST /api/auth/logout          → revoke refresh token (server-side blacklist via Redis)
GET  /api/auth/me              → current user profile
PUT  /api/auth/me/password     → change own password
POST /api/auth/users           → create user (admin only)
GET  /api/auth/users           → list users (admin only)
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_auth
from app.auth.models import User, UserRole
from app.auth.service import (
    ALGORITHM,
    TokenClaims,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_email,
    hash_password,
    verify_password,
)
from app.cache.client import cache
from app.config import get_settings
from app.database import get_db

log = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12)


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2)
    password: str = Field(min_length=12)
    role: UserRole = UserRole.associate
    partner_id: int | None = None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login: datetime | None
    partner_id: int | None

    model_config = {"from_attributes": True}


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email + password.
    Returns access token (8h) and refresh token (30d).
    """
    user = await authenticate_user(req.email, req.password, db)
    if not user:
        # Uniform error — don't reveal whether email exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    log.info("Login success", user_id=user.id, email=user.email, ip=request.client.host if request.client else "unknown")

    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        role=user.role.value,
        full_name=user.full_name,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    try:
        payload = jwt.decode(req.refresh_token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    # Check blacklist
    if await cache.get(f"revoked_refresh:{req.refresh_token[:16]}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user),
        role=user.role.value,
        full_name=user.full_name,
    )


@router.post("/logout", status_code=204)
async def logout(req: RefreshRequest):
    """Blacklist the refresh token (server-side invalidation)."""
    # Store first 16 chars as key — enough for deduplication, not full token
    await cache.set(f"revoked_refresh:{req.refresh_token[:16]}", "1", ttl=60 * 60 * 24 * 31)
    return None


@router.get("/me", response_model=UserOut)
async def get_me(
    claims: TokenClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == claims.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)


@router.put("/me/password", status_code=204)
async def change_password(
    req: ChangePasswordRequest,
    claims: TokenClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == claims.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = hash_password(req.new_password)
    await db.commit()
    log.info("Password changed", user_id=user.id)
    return None


@router.post("/users", response_model=UserOut, status_code=201)
async def create_new_user(
    req: CreateUserRequest,
    claims: TokenClaims = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user account. Admin only."""
    existing = await get_user_by_email(req.email, db)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await create_user(
        email=req.email,
        full_name=req.full_name,
        password=req.password,
        role=req.role,
        db=db,
        partner_id=req.partner_id,
    )
    log.info("User created", created_by=claims.user_id, new_user=user.id, role=user.role)
    return UserOut.model_validate(user)


@router.get("/users", response_model=list[UserOut])
async def list_users(
    claims: TokenClaims = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Admin only."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserOut.model_validate(u) for u in result.scalars().all()]
