"""
app/routes/signals.py — Phase 7 signal feed endpoints.

Endpoints:
    GET /api/v1/signals              List recent signals (all companies)
    GET /api/v1/signals/{company_id} Recent signals for a specific company
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.database import get_db

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/signals", tags=["signals"])


@router.get("/", summary="List recent signals across all companies")
async def list_signals(
    limit: int = Query(default=50, ge=1, le=200),
    signal_type: str | None = Query(default=None),
    category: str | None = Query(default=None, description="Filter by signal_type prefix, e.g. 'geo'"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """
    Return recent signals across all companies.
    Supports optional signal_type exact filter and category prefix filter.
    """
    try:
        base_sql = """
            SELECT
                source_id,
                signal_type,
                signal_text,
                signal_value,
                confidence_score,
                published_at,
                scraped_at,
                practice_area_hints,
                source_url,
                raw_company_name
            FROM signal_records
            WHERE scraped_at >= NOW() - INTERVAL '90 days'
        """
        params: dict[str, Any] = {"limit": limit}

        if signal_type:
            base_sql += " AND signal_type = :signal_type"
            params["signal_type"] = signal_type
        elif category:
            base_sql += " AND signal_type LIKE :category_prefix"
            params["category_prefix"] = f"{category}_%"

        base_sql += " ORDER BY scraped_at DESC LIMIT :limit"

        result = await db.execute(text(base_sql), params)
        rows = result.mappings().all()
    except Exception as exc:
        log.exception("signals: DB error listing signals")
        raise HTTPException(status_code=500, detail="Database error") from exc

    return [
        {
            "source_id": row["source_id"],
            "signal_type": row["signal_type"],
            "signal_text": row["signal_text"],
            "signal_value": row["signal_value"],
            "confidence_score": row["confidence_score"],
            "published_at": (row["published_at"].isoformat() if row["published_at"] else None),
            "scraped_at": (row["scraped_at"].isoformat() if row["scraped_at"] else None),
            "practice_area_hints": row["practice_area_hints"],
            "source_url": row["source_url"],
            "raw_company_name": row["raw_company_name"],
        }
        for row in rows
    ]


@router.get("/{company_id}", summary="Recent signals for a company (last 90 days)")
async def get_company_signals(
    company_id: int,
    limit: int = Query(default=100, ge=1, le=200),
    signal_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """
    Return signals for a company from the last 90 days.
    Optionally filter by signal_type.
    """
    try:
        base_sql = """
            SELECT
                source_id,
                signal_type,
                signal_text,
                signal_value,
                confidence_score,
                published_at,
                scraped_at,
                practice_area_hints,
                source_url
            FROM signal_records
            WHERE company_id = :company_id
              AND scraped_at >= NOW() - INTERVAL '90 days'
        """
        params: dict[str, Any] = {"company_id": company_id, "limit": limit}

        if signal_type:
            base_sql += " AND signal_type = :signal_type"
            params["signal_type"] = signal_type

        base_sql += " ORDER BY scraped_at DESC LIMIT :limit"

        result = await db.execute(text(base_sql), params)
        rows = result.mappings().all()
    except Exception as exc:
        log.exception("signals: DB error fetching signals for company %d", company_id)
        raise HTTPException(status_code=500, detail="Database error") from exc

    return [
        {
            "source_id": row["source_id"],
            "signal_type": row["signal_type"],
            "signal_text": row["signal_text"],
            "signal_value": row["signal_value"],
            "confidence_score": row["confidence_score"],
            "published_at": (row["published_at"].isoformat() if row["published_at"] else None),
            "scraped_at": (row["scraped_at"].isoformat() if row["scraped_at"] else None),
            "practice_area_hints": row["practice_area_hints"],
            "source_url": row["source_url"],
        }
        for row in rows
    ]
