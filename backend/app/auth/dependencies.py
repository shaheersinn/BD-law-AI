"""
app/auth/dependencies.py — FastAPI authentication dependencies.

Usage in routes:
    @router.get("/scores")
    async def get_scores(
        current_user: User = Depends(require_auth),
        db: AsyncSession = Depends(get_db),
    ):
        ...

    @router.post("/users")
    async def create_user(
        admin: User = Depends(require_admin),
        db: AsyncSession = Depends(get_db),
    ):
        ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import decode_token, get_user_by_id
from app.database import get_db

# OAuth2 bearer token scheme
bearer_scheme = HTTPBearer(auto_error=True)


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency: Require any authenticated user.

    Validates JWT access token and returns the authenticated user.
    Raises 401 if token is missing, invalid, or expired.
    Raises 401 if user account is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def require_associate(
    current_user: User = Depends(require_auth),
) -> User:
    """Dependency: Require associate role or higher (admin, partner, associate)."""
    if current_user.role not in ("admin", "partner", "associate"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Associate access required",
        )
    return current_user


async def require_partner(
    current_user: User = Depends(require_auth),
) -> User:
    """Dependency: Require partner role or higher (admin, partner)."""
    if current_user.role not in ("admin", "partner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner access required",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(require_auth),
) -> User:
    """Dependency: Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
