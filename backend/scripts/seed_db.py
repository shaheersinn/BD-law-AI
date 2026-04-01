"""
scripts/seed_db.py — Seed database with required initial data.

Creates:
  - Admin user — defaults: email `admin`, password `admin` (`ADMIN_EMAIL` / `ADMIN_PASSWORD`)
  - Demo partner user (development only) — defaults: `partner` / `partner` (`DEMO_PARTNER_*`)
  - Optional dashboard demo intel (companies, signal_records, scoring_results, triggers)
    when `SEED_DEMO_DASHBOARD` is not false and DB has no `demo.oracle.local` companies yet.

Usage:
  python -m scripts.seed_db
  python -m scripts.seed_db --skip-if-seeded
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta

log = logging.getLogger(__name__)

_DEMO_DOMAIN = "demo.oracle.local"


async def seed_companies(db: object) -> None:
    """Seed Canadian watchlist companies when the companies table is empty."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(db, AsyncSession)

    from app.models.company import Company, CompanyStatus

    result = await db.execute(select(Company).limit(1))
    if result.scalars().first() is not None:
        log.info("Companies already present — skipping canonical company seed")
        return

    companies = [
        ("Shopify Inc.", "SHOP", "TSX", "Technology", "ON"),
        ("Royal Bank of Canada", "RY", "TSX", "Banking", "ON"),
        ("TD Bank Group", "TD", "TSX", "Banking", "ON"),
        ("Brookfield Asset Management", "BAM", "TSX", "Finance", "ON"),
        ("Canadian Natural Resources", "CNQ", "TSX", "Energy", "AB"),
        ("Suncor Energy Inc.", "SU", "TSX", "Energy", "AB"),
        ("Barrick Gold Corporation", "ABX", "TSX", "Mining", "ON"),
        ("Loblaw Companies Ltd.", "L", "TSX", "Retail", "ON"),
        ("BCE Inc.", "BCE", "TSX", "Telecommunications", "QC"),
        ("Manulife Financial Corp.", "MFC", "TSX", "Insurance", "ON"),
        ("Alimentation Couche-Tard", "ATD", "TSX", "Retail", "QC"),
        ("Agnico Eagle Mines", "AEM", "TSX", "Mining", "ON"),
        ("Magna International Inc.", "MG", "TSX", "Manufacturing", "ON"),
        ("Celestica Inc.", "CLS", "TSX", "Technology", "ON"),
        ("Nuvei Corporation", "NVEI", "TSX", "Technology", "QC"),
        ("Ritchie Bros. Auctioneers", "RBA", "TSX", "Services", "BC"),
        ("Kinross Gold Corporation", "K", "TSX", "Mining", "ON"),
        ("Hydro One Limited", "H", "TSX", "Utilities", "ON"),
        ("Open Text Corporation", "OTEX", "TSX", "Technology", "ON"),
        ("Teck Resources Limited", "TECK", "TSX", "Mining", "BC"),
    ]

    for name, ticker, exchange, sector, province in companies:
        co = Company(
            name=name,
            name_normalized=name.lower(),
            ticker=ticker,
            exchange=exchange,
            sector=sector,
            province=province,
            country="CA",
            status=CompanyStatus.active,
            is_publicly_listed=True,
            priority_tier=1,
        )
        db.add(co)

    await db.commit()
    log.info("Seeded %d canonical companies", len(companies))

# Must stay in sync with app.ml.bayesian_engine.PRACTICE_AREAS (avoid importing ML stack in seed).
_DEMO_PA_SLUGS: tuple[str, ...] = (
    "ma",
    "litigation",
    "regulatory",
    "employment",
    "insolvency",
    "securities",
    "competition",
    "privacy",
    "environmental",
    "tax",
    "real_estate",
    "banking",
    "ip",
    "immigration",
    "infrastructure",
    "wills_estates",
    "admin_public",
    "arbitration",
    "class_actions",
    "construction_disputes",
    "defamation",
    "financial_regulatory",
    "franchise",
    "health_sciences",
    "insurance",
    "intl_trade",
    "mining",
    "municipal_land",
    "nfp_charity",
    "pension_benefits",
    "product_liability",
    "sports_entertainment",
    "tech_fintech",
    "data_privacy_tech",
)


async def _seed_demo_dashboard(db: object) -> None:
    """Fill ConstructLex dashboard APIs when the DB has no demo intel rows yet."""
    from sqlalchemy import func, select, text
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(db, AsyncSession)

    if os.getenv("SEED_DEMO_DASHBOARD", "true").strip().lower() in ("0", "false", "no"):
        log.info("SEED_DEMO_DASHBOARD disabled — skipping demo dashboard data")
        return

    from app.models.company import Company, CompanyStatus, SignalRecord
    from app.models.trigger import Trigger

    existing_demo = (
        await db.execute(
            select(func.count()).select_from(Company).where(Company.domain == _DEMO_DOMAIN)
        )
    ).scalar_one()
    if int(existing_demo) > 0:
        log.info("Demo dashboard companies already present — skipping")
        return

    def _scores_for_company(seed: int, top_pa: str, top_30d: float) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for i, pa in enumerate(_DEMO_PA_SLUGS):
            if pa == top_pa:
                out[pa] = {
                    "30d": top_30d,
                    "60d": min(0.95, top_30d + 0.05),
                    "90d": min(0.97, top_30d + 0.1),
                }
            else:
                base = 0.08 + (seed * 0.01 + i * 0.002) % 0.15
                out[pa] = {
                    "30d": round(base, 4),
                    "60d": round(base + 0.02, 4),
                    "90d": round(base + 0.04, 4),
                }
        return out

    demos: list[tuple[str, str, str, str, float, str, float]] = [
        # name, ticker, sector, top_practice_slug, top_30d, trend_hint, velocity
        ("Northwind Trading Inc.", "NWT", "Industrials", "litigation", 0.82, "Litigation/Dispute Resolution", 3.2),
        ("Blue Maple Capital Corp.", "BMC", "Financials", "securities", 0.76, "Securities/Capital Markets", 2.1),
        ("Hudson Bay Petrochemicals Ltd.", "HBP", "Energy", "environmental", 0.71, "Environmental/Indigenous/Energy", -0.8),
        ("Laurier Software Group Inc.", "LSG", "Technology", "privacy", 0.88, "Privacy/Cybersecurity", 2.9),
        ("Prairie Rail Holdings", "PRH", "Transportation", "employment", 0.64, "Employment/Labour", 1.4),
    ]

    now = datetime.now(UTC)
    company_rows: list[Company] = []
    for name, ticker, sector, _tp, _ts, _hint, _v in demos:
        c = Company(
            name=name,
            name_normalized=name.lower(),
            ticker=ticker,
            exchange="TSX",
            sector=sector,
            industry=sector,
            country="CA",
            domain=_DEMO_DOMAIN,
            status=CompanyStatus.active,
            is_publicly_listed=True,
        )
        db.add(c)
        company_rows.append(c)

    await db.flush()

    practice_hints_for_signals = [
        "Regulatory/Compliance",
        "M&A/Corporate",
        "Class Actions",
        "Competition/Antitrust",
        "Insolvency/Restructuring",
    ]

    for idx, c in enumerate(company_rows):
        for j in range(3):
            db.add(
                SignalRecord(
                    company_id=c.id,
                    source_id="demo_seed",
                    signal_type="news_mention",
                    signal_text=f"Demo signal {j + 1} for {c.name}",
                    practice_area_hints=practice_hints_for_signals[(idx + j) % len(practice_hints_for_signals)],
                    scraped_at=now - timedelta(hours=6 * j + idx),
                    confidence_score=0.85,
                )
            )

    for idx, (_name, _ticker, _sector, top_pa, top_30d, _hint, velocity) in enumerate(demos):
        c = company_rows[idx]
        scores = _scores_for_company(idx, top_pa, top_30d)
        await db.execute(
            text("""
                INSERT INTO scoring_results
                (company_id, scored_at, scores, velocity_score, anomaly_score,
                 confidence_low, confidence_high, model_versions, top_signals)
                VALUES
                (:company_id, :scored_at, CAST(:scores AS jsonb), :velocity, :anomaly,
                 0.4, 0.95, CAST(:mv AS jsonb), CAST(:ts AS jsonb))
            """),
            {
                "company_id": c.id,
                "scored_at": now - timedelta(minutes=30 + idx * 5),
                "scores": json.dumps(scores),
                "velocity": velocity,
                "anomaly": 0.12 + idx * 0.01,
                "mv": json.dumps({top_pa: "demo"}),
                "ts": json.dumps([]),
            },
        )

    sources = ("demo", "demo_feed", "demo_regulatory")
    for h in range(24):
        if h % 3 != 0:
            continue
        urgency = 55 + (h % 5) * 9
        db.add(
            Trigger(
                source=sources[h % len(sources)],
                trigger_type="demo_watch",
                company_name=demos[h % len(demos)][0],
                title=f"Demo trigger event {h // 3 + 1}",
                description="Seeded for dashboard KPIs — safe to delete in production.",
                url="https://example.com/demo",
                urgency=min(urgency, 94),
                practice_area=demos[h % len(demos)][3],
                practice_confidence=72,
                filed_at=now - timedelta(hours=h + 1),
                detected_at=now - timedelta(hours=h),
                actioned=False,
            )
        )

    await db.commit()
    try:
        from app.cache.client import cache

        await cache.delete("triggers:v1:stats")
        await cache.delete("trends:practice_areas:v1")
        for lim in (5, 10, 15, 20, 50, 100):
            await cache.delete(f"top_velocity:{lim}")
    except Exception as exc:
        log.warning("Could not clear dashboard cache keys after demo seed: %s", exc)
    log.info("Demo dashboard data seeded (%d companies, signals, scores, triggers)", len(demos))


async def seed(skip_if_seeded: bool = False) -> None:
    from sqlalchemy.future import select

    from app.auth.models import User
    from app.auth.service import create_user, get_user_by_email
    from app.config import get_settings
    from app.database import AsyncSessionLocal, check_db_connection

    if not await check_db_connection():
        log.error("Cannot connect to PostgreSQL — aborting seed")
        sys.exit(1)

    settings = get_settings()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        existing_users = result.scalars().all()

        if existing_users and skip_if_seeded:
            log.info("Users already exist — skipping user seed (--skip-if-seeded)")
        else:
            admin_email = os.getenv("ADMIN_EMAIL", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "admin")
            admin_name = os.getenv("ADMIN_NAME", "ORACLE Administrator")

            existing_admin = await get_user_by_email(db, admin_email)
            if existing_admin is None:
                admin = await create_user(db, admin_email, admin_password, admin_name, role="admin")
                log.info("Admin created: %s (id=%d)", admin.email, admin.id)
            else:
                log.info("Admin already exists: %s", admin_email)

            if settings.is_development:
                demo_email = os.getenv("DEMO_PARTNER_EMAIL", "partner")
                demo_password = os.getenv("DEMO_PARTNER_PASSWORD", "partner")
                existing = await get_user_by_email(db, demo_email)
                if existing is None:
                    partner = await create_user(
                        db, demo_email, demo_password, "Demo Partner", role="partner"
                    )
                    log.info("Demo partner created: %s (id=%d)", partner.email, partner.id)
            await db.commit()

        try:
            await seed_companies(db)
        except Exception:
            log.exception("Canonical company seed failed (non-fatal)")

        if settings.is_development or os.getenv("SEED_DEMO_DASHBOARD", "").lower() in ("1", "true", "yes"):
            try:
                await _seed_demo_dashboard(db)
            except Exception:
                log.exception("Demo dashboard seed failed (non-fatal)")
        else:
            log.info("Skipping demo dashboard seed (production — set SEED_DEMO_DASHBOARD=1 to enable)")

        log.info("Seed complete")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-if-seeded", action="store_true")
    args = parser.parse_args()
    asyncio.run(seed(skip_if_seeded=args.skip_if_seeded))


if __name__ == "__main__":
    main()
