"""
app/routes/class_actions.py — Class action risk + firm matching endpoints.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.database import get_db
from app.models.class_action_score import ClassActionScore
from app.models.company import Company
from app.models.law_firm import LawFirm
from app.services.firm_matcher import match_firms_to_class_action, seed_law_firms

log = logging.getLogger(__name__)

router = APIRouter(prefix="/class-actions", tags=["class-actions"])


class CustomMatchRequest(BaseModel):
    company_id: int | None = None
    side: str = "both"
    top_n: int = Field(default=5, ge=1, le=20)
    predicted_type: str | None = None
    probability: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    time_horizon_days: int = Field(default=60, ge=7, le=365)
    contributing_signals: list[dict[str, Any]] = Field(default_factory=list)
    company_name: str | None = None
    company_province: str | None = None
    company_sector: str | None = None


async def _get_score_and_company(
    db: AsyncSession, company_id: int
) -> tuple[ClassActionScore, Company]:
    score_res = await db.execute(
        select(ClassActionScore).where(ClassActionScore.company_id == company_id)
    )
    score = score_res.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail=f"No class action score for company {company_id}")

    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    return score, company


@router.get("/risks", summary="Top class action risk companies")
async def get_top_risks(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT
                s.company_id,
                c.name AS company_name,
                c.sector,
                c.province,
                s.probability,
                s.predicted_type,
                s.time_horizon_days,
                s.confidence,
                s.scored_at
            FROM class_action_scores s
            JOIN companies c ON c.id = s.company_id
            ORDER BY s.probability DESC, s.confidence DESC NULLS LAST
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    rows = result.mappings().all()
    return [
        {
            "company_id": row["company_id"],
            "company_name": row["company_name"],
            "sector": row["sector"],
            "province": row["province"],
            "class_action_probability": round(float(row["probability"] or 0.0), 4),
            "predicted_type": row["predicted_type"],
            "time_horizon_days": row["time_horizon_days"],
            "confidence": round(float(row["confidence"] or 0.0), 4),
            "scored_at": row["scored_at"].isoformat() if row["scored_at"] else None,
        }
        for row in rows
    ]


@router.get("/risks/{company_id}", summary="Class action risk detail for one company")
async def get_risk_detail(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> dict[str, Any]:
    score, company = await _get_score_and_company(db, company_id)
    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "sector": company.sector,
            "province": company.province,
            "hq_city": company.hq_city,
        },
        "risk": {
            "class_action_probability": round(float(score.probability or 0.0), 4),
            "predicted_type": score.predicted_type,
            "time_horizon_days": score.time_horizon_days,
            "confidence": round(float(score.confidence or 0.0), 4),
            "contributing_signals": score.contributing_signals or [],
            "scored_at": score.scored_at.isoformat() if score.scored_at else None,
        },
    }


@router.get("/cases", summary="All tracked class action cases")
async def get_cases(
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                company_id,
                case_name,
                case_number,
                jurisdiction,
                court,
                status,
                case_type,
                plaintiff_firm,
                filing_date,
                certification_date,
                settlement_date,
                settlement_amount_cad,
                source_url,
                source_scraper,
                practice_areas,
                created_at
            FROM class_action_cases
            ORDER BY COALESCE(filing_date, created_at) DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    rows = result.mappings().all()
    return [
        {
            "id": row["id"],
            "company_id": row["company_id"],
            "case_name": row["case_name"],
            "case_number": row["case_number"],
            "jurisdiction": row["jurisdiction"],
            "court": row["court"],
            "status": row["status"],
            "case_type": row["case_type"],
            "plaintiff_firm": row["plaintiff_firm"],
            "filing_date": row["filing_date"].isoformat() if row["filing_date"] else None,
            "certification_date": (
                row["certification_date"].isoformat() if row["certification_date"] else None
            ),
            "settlement_date": row["settlement_date"].isoformat() if row["settlement_date"] else None,
            "settlement_amount_cad": (
                float(row["settlement_amount_cad"]) if row["settlement_amount_cad"] else None
            ),
            "source_url": row["source_url"],
            "source_scraper": row["source_scraper"],
            "practice_areas": row["practice_areas"] or [],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


@router.get("/cases/{case_id}", summary="Single class action case detail")
async def get_case_detail(
    case_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> dict[str, Any]:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM class_action_cases
            WHERE id = :case_id
            """
        ),
        {"case_id": case_id},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "case_name": row["case_name"],
        "case_number": row["case_number"],
        "jurisdiction": row["jurisdiction"],
        "court": row["court"],
        "status": row["status"],
        "case_type": row["case_type"],
        "plaintiff_firm": row["plaintiff_firm"],
        "filing_date": row["filing_date"].isoformat() if row["filing_date"] else None,
        "certification_date": row["certification_date"].isoformat() if row["certification_date"] else None,
        "settlement_date": row["settlement_date"].isoformat() if row["settlement_date"] else None,
        "settlement_amount_cad": (
            float(row["settlement_amount_cad"]) if row["settlement_amount_cad"] else None
        ),
        "source_url": row["source_url"],
        "source_scraper": row["source_scraper"],
        "practice_areas": row["practice_areas"] or [],
        "raw_payload": row["raw_payload"] or {},
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@router.get("/match/{company_id}", summary="Match firms to a company's class action risk")
async def match_company_firms(
    company_id: int,
    top_n: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> dict[str, Any]:
    score, company = await _get_score_and_company(db, company_id)
    plaintiff = await match_firms_to_class_action(
        db=db,
        class_action_score=score,
        company=company,
        side="plaintiff",
        top_n=top_n,
    )
    defence = await match_firms_to_class_action(
        db=db,
        class_action_score=score,
        company=company,
        side="defence",
        top_n=top_n,
    )
    return {
        "company_id": company.id,
        "company_name": company.name,
        "predicted_type": score.predicted_type,
        "class_action_probability": round(float(score.probability or 0.0), 4),
        "plaintiff_firms": [item.to_dict() for item in plaintiff],
        "defence_firms": [item.to_dict() for item in defence],
    }


@router.post("/match", summary="Custom class action firm match request")
async def custom_match(
    req: CustomMatchRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> dict[str, Any]:
    if req.side not in {"plaintiff", "defence", "both"}:
        raise HTTPException(status_code=422, detail="side must be one of: plaintiff, defence, both")

    if req.company_id is not None:
        score, company = await _get_score_and_company(db, req.company_id)
    else:
        score = ClassActionScore(
            company_id=0,
            probability=req.probability,
            predicted_type=req.predicted_type,
            time_horizon_days=req.time_horizon_days,
            confidence=req.confidence,
            contributing_signals=req.contributing_signals,
            scored_at=datetime.now(tz=UTC),
        )
        company = Company(
            name=req.company_name or "Custom Company",
            name_normalized=(req.company_name or "custom company").lower(),
            country="CA",
            province=req.company_province,
            sector=req.company_sector,
        )

    matches = await match_firms_to_class_action(
        db=db,
        class_action_score=score,
        company=company,
        side=req.side,
        top_n=req.top_n,
    )
    return {
        "company_name": company.name,
        "predicted_type": score.predicted_type,
        "class_action_probability": round(float(score.probability or 0.0), 4),
        "side": req.side,
        "matches": [item.to_dict() for item in matches],
    }


@router.get("/dashboard", summary="Class action radar summary stats")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> dict[str, Any]:
    inserted = await seed_law_firms(db)
    if inserted:
        log.info("class_actions: seeded law firms", inserted=inserted)

    result = await db.execute(
        text(
            """
            SELECT
                COUNT(*)::int AS total_scored,
                COUNT(*) FILTER (WHERE probability >= 0.70)::int AS high_risk,
                AVG(probability)::float AS avg_probability
            FROM class_action_scores
            """
        )
    )
    summary = result.mappings().first() or {}

    sectors = await db.execute(
        text(
            """
            SELECT
                COALESCE(c.sector, 'Unknown') AS sector,
                COUNT(*)::int AS risk_count,
                AVG(s.probability)::float AS avg_probability
            FROM class_action_scores s
            JOIN companies c ON c.id = s.company_id
            GROUP BY COALESCE(c.sector, 'Unknown')
            ORDER BY risk_count DESC, avg_probability DESC
            LIMIT 20
            """
        )
    )
    by_sector = sectors.mappings().all()

    cases = await db.execute(
        text(
            """
            SELECT
                COUNT(*)::int AS total_cases,
                COUNT(*) FILTER (
                    WHERE LOWER(status) IN ('filed', 'active', 'certified', 'pending')
                )::int AS active_cases
            FROM class_action_cases
            """
        )
    )
    cases_summary = cases.mappings().first() or {}

    law_firms_count = await db.scalar(select(func.count()).select_from(LawFirm))

    return {
        "total_risk_companies": int(summary.get("total_scored", 0) or 0),
        "high_risk_companies": int(summary.get("high_risk", 0) or 0),
        "average_probability": round(float(summary.get("avg_probability", 0.0) or 0.0), 4),
        "tracked_cases_total": int(cases_summary.get("total_cases", 0) or 0),
        "tracked_cases_active": int(cases_summary.get("active_cases", 0) or 0),
        "law_firms_indexed": int(law_firms_count or 0),
        "sector_heatmap": [
            {
                "sector": row["sector"],
                "risk_count": row["risk_count"],
                "avg_probability": round(float(row["avg_probability"] or 0.0), 4),
            }
            for row in by_sector
        ],
    }
