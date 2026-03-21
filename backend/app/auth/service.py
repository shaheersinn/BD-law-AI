"""
app/auth/service.py — Authentication service.

Provides:
  - Password hashing (bcrypt via passlib)
  - JWT access + refresh token issuance
  - Token verification and claims extraction
  - Account lockout after repeated failures
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token lifetimes
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8    # 8 hours — full working day
REFRESH_TOKEN_EXPIRE_DAYS   = 30
ALGORITHM = "HS256"

# Account lockout
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


# ── Password helpers ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Token issuance ─────────────────────────────────────────────────────────────

def _encode(data: dict, expire_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expire_delta
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user: User) -> str:
    return _encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "partner_id": user.partner_id,
            "type": "access",
        },
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user: User) -> str:
    return _encode(
        {"sub": str(user.id), "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


# ── Token verification ─────────────────────────────────────────────────────────

class TokenClaims:
    def __init__(self, sub: int, email: str, role: UserRole, partner_id: Optional[int]):
        self.user_id   = sub
        self.email     = email
        self.role      = role
        self.partner_id = partner_id

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin

    @property
    def is_partner_or_above(self) -> bool:
        return self.role in (UserRole.admin, UserRole.partner)

    def can_write(self) -> bool:
        return self.role in (UserRole.admin, UserRole.partner, UserRole.associate)


def decode_token(token: str) -> TokenClaims:
    """Decode and validate a JWT. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return TokenClaims(
        sub=int(payload["sub"]),
        email=payload["email"],
        role=UserRole(payload["role"]),
        partner_id=payload.get("partner_id"),
    )


# ── Database helpers ───────────────────────────────────────────────────────────

async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalars().first()


async def authenticate_user(
    email: str, password: str, db: AsyncSession
) -> Optional[User]:
    """
    Verify credentials. Handles account lockout.
    Returns the User on success, None on failure.
    Updates failed_login_count on failure.
    """
    user = await get_user_by_email(email, db)
    if not user or not user.is_active:
        return None

    # Check lockout
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        log.warning("Login attempt on locked account: %s", email)
        return None

    if not verify_password(password, user.hashed_password):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
            log.warning("Account locked after %d failures: %s", MAX_FAILED_ATTEMPTS, email)
        await db.commit()
        return None

    # Success — reset counters
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    return user


async def create_user(
    email: str,
    full_name: str,
    password: str,
    role: UserRole,
    db: AsyncSession,
    partner_id: Optional[int] = None,
) -> User:
    user = User(
        email=email.lower(),
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        partner_id=partner_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
