"""
app/models/law_firm.py — Law firm metadata for class action matching.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LawFirm(Base):
    __tablename__ = "law_firms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    tier: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="1=Bay Street, 2=National, 3=Regional, 4=Boutique"
    )
    hq_province: Mapped[str | None] = mapped_column(String(10), nullable=True)
    offices: Mapped[list[dict] | None] = mapped_column(
        JSONB, nullable=True, comment="[{city, province}]"
    )
    practice_strengths: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="{practice_area: strength_score}"
    )
    class_action_track_record: Mapped[list[dict] | None] = mapped_column(
        JSONB, nullable=True, comment="[{case_type, count, avg_settlement}]"
    )
    jurisdictions: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True, comment="Provinces where licensed"
    )
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_plaintiff_firm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_defence_firm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lawyer_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    class_action_lawyers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
