"""
app/auth/models.py — User and authentication ORM models.

Roles:
  - admin: Full access — user management, system config
  - partner: Full BD intelligence access — scores, signals, watchlist
  - associate: Read-only BD intelligence
  - readonly: View only — no watchlist management

Security:
  - Passwords stored as bcrypt hashes only (never plaintext)
  - Account lockout after max_login_attempts failures
  - Refresh tokens stored hashed (like passwords)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Role type for type safety
UserRole = Literal["admin", "partner", "associate", "readonly"]


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Authentication
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, default="readonly")

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Security tracking
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Refresh token (hashed — treated like a password)
    hashed_refresh_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.now(UTC) < self.locked_until

    @property
    def can_access_scores(self) -> bool:
        """Check if user can view practice area scores."""
        return self.role in ("admin", "partner", "associate", "readonly")

    @property
    def can_manage_watchlist(self) -> bool:
        """Check if user can add/remove companies from watchlist."""
        return self.role in ("admin", "partner", "associate")

    @property
    def can_manage_users(self) -> bool:
        """Check if user can create/modify other users."""
        return self.role == "admin"

    @property
    def user_id(self) -> int:
        """Alias for id — used by route handlers via TokenClaims."""
        return self.id

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    @property
    def partner_id(self) -> int | None:
        """Partner ID — stub returns None; override when partner table is linked."""
        return None
