"""
app/routes/watchlist.py — Watchlist management + company search + bulk import.

The watchlist is the set of companies the scrapers actively monitor.
Every client is automatically on the watchlist. Prospects can be added manually
or imported in bulk via CSV.

Routes:
  GET  /api/watchlist                    → all watchlist entries
  POST /api/watchlist                    → add company to watchlist
  DELETE /api/watchlist/{id}             → remove from watchlist
  POST /api/watchlist/import             → bulk CSV import (clients + prospects)
  GET  /api/search?q=arctis&limit=10    → fuzzy company search across all entities
  POST /api/scrape/trigger               → manually trigger a scrape for one company
"""

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_partner, require_write
from app.auth.service import TokenClaims
from app.database import get_db
from app.models import Client, Prospect
from app.services.audit_log import AuditEventType, extract_request_meta, log_event
from app.services.entity_resolution import resolver

log = logging.getLogger(__name__)

router = APIRouter(tags=["watchlist"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class WatchlistEntry(BaseModel):
    id: int
    name: str
    entity_type: str       # "client" | "prospect"
    industry: Optional[str]
    region: Optional[str]
    is_active: bool


class AddToWatchlistRequest(BaseModel):
    name: str
    industry: Optional[str] = None
    region: Optional[str] = None


class CompanySearchResult(BaseModel):
    id: int
    name: str
    entity_type: str
    industry: Optional[str]
    churn_score: Optional[int]
    legal_urgency_score: Optional[int]
    match_score: float


class BulkImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


class ScrapeRequest(BaseModel):
    company_name: str
    sources: list[str] = ["SEDAR", "EDGAR", "JOBS"]   # which scrapers to run


# ── Watchlist CRUD ─────────────────────────────────────────────────────────────

@router.get("/watchlist", response_model=list[WatchlistEntry])
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_write),
):
    """All actively monitored companies (clients + prospects)."""
    clients = (
        await db.execute(
            select(Client)
            .where(Client.is_active == True)
            .order_by(Client.name)
        )
    ).scalars().all()

    prospects = (
        await db.execute(select(Prospect).order_by(Prospect.name))
    ).scalars().all()

    entries = [
        WatchlistEntry(id=c.id, name=c.name, entity_type="client",
                       industry=c.industry, region=c.region, is_active=True)
        for c in clients
    ] + [
        WatchlistEntry(id=p.id, name=p.name, entity_type="prospect",
                       industry=p.industry, region=p.region, is_active=True)
        for p in prospects
    ]
    return entries


@router.post("/watchlist", response_model=WatchlistEntry, status_code=201)
async def add_to_watchlist(
    req: AddToWatchlistRequest,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_partner),
    request: Request = None,
):
    """Add a company as a prospect on the watchlist."""
    # Check if already exists
    match = resolver.resolve(req.name)
    if match.matched:
        raise HTTPException(
            status_code=409,
            detail=f"Company already on watchlist as '{match.original_name}' (id={match.entity_id})",
        )

    prospect = Prospect(
        name=req.name,
        industry=req.industry,
        region=req.region,
        legal_urgency_score=0,
    )
    db.add(prospect)
    await db.commit()
    await db.refresh(prospect)

    # Update entity resolver
    resolver.add_entity(prospect.name, prospect.id, "prospect")

    await log_event(
        AuditEventType.data_export,
        user_id=claims.user_id,
        resource_type="prospect",
        resource_id=prospect.id,
        detail={"action": "watchlist_add", "name": req.name},
        **(extract_request_meta(request) if request else {}),
    )

    return WatchlistEntry(
        id=prospect.id, name=prospect.name, entity_type="prospect",
        industry=prospect.industry, region=prospect.region, is_active=True,
    )


@router.delete("/watchlist/{prospect_id}", status_code=204)
async def remove_from_watchlist(
    prospect_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_partner),
):
    """Remove a prospect from the watchlist. Cannot remove clients."""
    result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    prospect = result.scalars().first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    await db.delete(prospect)
    await db.commit()
    return None


# ── Bulk CSV import ─────────────────────────────────────────────────────────────

@router.post("/watchlist/import", response_model=BulkImportResult)
async def bulk_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_partner),
    request: Request = None,
):
    """
    Import companies from CSV. Expected columns:
      name (required), industry, region, legal_urgency_score, predicted_need

    Skips rows where the company already exists (fuzzy matched at 82%).
    Returns count of imported and skipped rows.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    text = content.decode("utf-8-sig")   # strip BOM if present

    imported = 0
    skipped = 0
    errors: list[str] = []

    try:
        reader = csv.DictReader(io.StringIO(text))
        if "name" not in (reader.fieldnames or []):
            raise HTTPException(status_code=400, detail="CSV must have a 'name' column")

        for i, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            if not name:
                errors.append(f"Row {i}: empty name — skipped")
                continue

            # Check existing
            match = resolver.resolve(name)
            if match.matched:
                skipped += 1
                continue

            try:
                prospect = Prospect(
                    name=name,
                    industry=(row.get("industry") or "").strip() or None,
                    region=(row.get("region") or "").strip() or None,
                    predicted_need=(row.get("predicted_need") or "").strip() or None,
                    legal_urgency_score=int(row.get("legal_urgency_score") or 0),
                )
                db.add(prospect)
                await db.flush()
                resolver.add_entity(prospect.name, prospect.id, "prospect")
                imported += 1
            except Exception as e:
                errors.append(f"Row {i} ({name!r}): {e}")

        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV parse error: {e}")

    await log_event(
        AuditEventType.data_export,
        user_id=claims.user_id,
        detail={"action": "bulk_import", "imported": imported, "skipped": skipped, "errors": len(errors)},
        **(extract_request_meta(request) if request else {}),
    )

    return BulkImportResult(imported=imported, skipped=skipped, errors=errors[:20])


# ── Company search ─────────────────────────────────────────────────────────────

@router.get("/search", response_model=list[CompanySearchResult])
async def search_companies(
    q: str = Query(min_length=2, description="Company name search query"),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_write),
):
    """
    Fuzzy search across all clients and prospects.
    Returns entities ranked by match score with key intelligence fields.
    """
    from rapidfuzz import process, fuzz
    from app.services.entity_resolution import normalise

    q_norm = normalise(q)

    clients = (await db.execute(select(Client).where(Client.is_active == True))).scalars().all()
    prospects = (await db.execute(select(Prospect))).scalars().all()

    candidates = []
    for c in clients:
        norm = normalise(c.name)
        score = fuzz.token_sort_ratio(q_norm, norm)
        if score >= 40:
            candidates.append(CompanySearchResult(
                id=c.id, name=c.name, entity_type="client",
                industry=c.industry, churn_score=c.churn_score,
                legal_urgency_score=None, match_score=score,
            ))

    for p in prospects:
        norm = normalise(p.name)
        score = fuzz.token_sort_ratio(q_norm, norm)
        if score >= 40:
            candidates.append(CompanySearchResult(
                id=p.id, name=p.name, entity_type="prospect",
                industry=p.industry, churn_score=None,
                legal_urgency_score=p.legal_urgency_score, match_score=score,
            ))

    candidates.sort(key=lambda x: x.match_score, reverse=True)
    return candidates[:limit]


# ── On-demand scrape trigger ────────────────────────────────────────────────────

@router.post("/scrape/trigger")
async def trigger_scrape(
    req: ScrapeRequest,
    claims: TokenClaims = Depends(require_partner),
    request: Request = None,
):
    """
    Manually trigger scrapers for a specific company.
    Enqueues Celery tasks — returns immediately, results appear in trigger feed.
    """
    from app.tasks.celery_app import celery_app

    enqueued = []

    if "SEDAR" in req.sources:
        celery_app.send_task("app.tasks.celery_app.scrape_sedar")
        enqueued.append("SEDAR")

    if "EDGAR" in req.sources:
        celery_app.send_task("app.tasks.celery_app.scrape_edgar")
        enqueued.append("EDGAR")

    if "JOBS" in req.sources:
        celery_app.send_task("app.tasks.celery_app.scrape_jobs")
        enqueued.append("JOBS")

    if "CANLII" in req.sources:
        celery_app.send_task("app.tasks.celery_app.scrape_canlii")
        enqueued.append("CANLII")

    await log_event(
        AuditEventType.scrape_trigger,
        user_id=claims.user_id,
        detail={"company": req.company_name, "sources": enqueued},
        **(extract_request_meta(request) if request else {}),
    )

    return {
        "status": "enqueued",
        "company": req.company_name,
        "sources": enqueued,
        "message": "Scrape tasks enqueued. Results will appear in the Live Triggers feed within 2–5 minutes.",
    }
