"""
app/models/company.py — Company entity + company_aliases + signal_records ORM models.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompanyStatus(enum.StrEnum):
    active = "active"
    inactive = "inactive"
    acquired = "acquired"
    bankrupt = "bankrupt"
    merged = "merged"
    private = "private"


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    sedar_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    cik: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    lei: Mapped[str | None] = mapped_column(String(20), nullable=True)
    business_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cusip: Mapped[str | None] = mapped_column(String(9), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    sic_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    naics_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(200), nullable=True)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str] = mapped_column(String(10), nullable=False, default="CA")
    hq_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_cap_cad: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_cad: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiscal_year_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(CompanyStatus), nullable=False, default=CompanyStatus.active
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_publicly_listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_crown_corporation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_foreign_private_issuer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    priority_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scrape_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    aliases: Mapped[list[CompanyAlias]] = relationship("CompanyAlias", back_populates="company")
    signals: Mapped[list[SignalRecord]] = relationship("SignalRecord", back_populates="company")
    __table_args__ = (Index("ix_companies_ticker_exchange", "ticker", "exchange"),)


class CompanyAlias(Base):
    __tablename__ = "company_aliases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(500), nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(String(50), nullable=False, default="name")
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    company: Mapped[Company] = relationship("Company", back_populates="aliases")


class SignalRecord(Base):
    __tablename__ = "signal_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), nullable=True, index=True
    )
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    raw_company_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_company_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signal_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    signal_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    mongo_doc_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_negative_label: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )
    ttl_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    practice_area_hints: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[Company | None] = relationship("Company", back_populates="signals")
    __table_args__ = (
        Index("ix_signal_source_scraped", "source_id", "scraped_at"),
        Index("ix_signal_company_type", "company_id", "signal_type"),
    )
