"""
app/auth/service.py — Authentication business logic.

Handles:
  - Password hashing (bcrypt with cost factor 12)
  - JWT access and refresh token creation and verification
  - Account lockout logic
  - User authentication

Security notes:
  - bcrypt cost factor 12 is the industry standard for 2024
  - Access tokens expire in 30 minutes (configurable)
  - Refresh tokens expire in 7 days (configurable)
  - Refresh tokens are stored as hashed values (treated like passwords)
  - Tokens carry user_id and role claims only — no sensitive data
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models import User
from app.config import get_settings

settings = get_settings()

# bcrypt with cost factor 12 — standard for production authentication
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Token type literals
TokenType = Literal["access", "refresh"]


# ── Password Utilities ─────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)  # type: ignore[no-any-return]


def verify_password(plaintext: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return pwd_context.verify(plaintext, hashed)  # type: ignore[no-any-return]


# ── JWT Token Utilities ────────────────────────────────────────────────────────


def create_access_token(user_id: int, role: str) -> str:
    """
    Create a signed JWT access token.

    Payload claims:
      - sub: user ID (string) — "subject"
      - role: user role
      - type: "access"
      - exp: expiry timestamp
      - iat: issued-at timestamp
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)  # type: ignore[no-any-return]


def create_refresh_token(user_id: int) -> str:
    """
    Create a signed JWT refresh token.

    Refresh tokens have a longer expiry and carry fewer claims.
    They are stored hashed in the database to prevent theft.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.refresh_token_expire_days)

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)  # type: ignore[no-any-return]


def decode_token(token: str, expected_type: TokenType) -> dict:  # type: ignore[type-arg]
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string
        expected_type: "access" or "refresh"

    Returns:
        Token payload dict

    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )

    if payload.get("type") != expected_type:
        raise JWTError(f"Expected {expected_type} token, got {payload.get('type')}")

    return payload  # type: ignore[no-any-return]


# ── User Authentication ────────────────────────────────────────────────────────


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch user by email address."""
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Fetch user by primary key."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """
    Authenticate a user by email and password.

    Handles:
      - Account lockout (returns None if locked)
      - Failed attempt tracking
      - Lockout after max attempts
      - Successful login resets failed attempts

    Returns:
        User if authentication succeeds, None otherwise.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        # Perform a dummy password hash to prevent timing attacks
        pwd_context.hash("dummy_password_to_prevent_timing_attack")
        return None

    # Check if account is locked
    if user.is_locked:
        return None

    # Verify password
    if not verify_password(password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= settings.max_login_attempts:
            user.locked_until = datetime.now(UTC) + timedelta(
                minutes=settings.lockout_duration_minutes
            )

        await db.commit()
        return None

    # Successful login — reset security counters
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    await db.commit()

    return user


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    role: str = "readonly",
) -> User:
    """
    Create a new user account.

    Args:
        db: Database session
        email: User email (normalized to lowercase)
        password: Plaintext password (hashed before storage)
        full_name: Display name
        role: User role (default: readonly)

    Returns:
        Created User object
    """
    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=True,
        is_verified=True,  # Admin-created users are pre-verified
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
