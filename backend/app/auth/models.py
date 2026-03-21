"""
app/auth/models.py — User authentication model.

Roles:
  admin    — full access, user management, model admin
  partner  — access to all intelligence + their own coaching data
  associate — limited view, only assigned matters + BD tools
  readonly  — dashboard view only, no AI generation
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    admin     = "admin"
    partner   = "partner"
    associate = "associate"
    readonly  = "readonly"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.associate)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    partner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # FK to partners

    # Session management
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
