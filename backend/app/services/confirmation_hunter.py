"""
app/services/confirmation_hunter.py — Phase 9: Auto mandate detection (Agent 032).

Scans recent signal_records from three high-signal sources and attempts to
match mentions to known companies via EntityResolver (rapidfuzz fuzzy matching,
threshold 82.0).  Matched records generate mandate_confirmations with
is_auto_detected=True — a partner must review before they count in accuracy.

Sources hunted daily:
  - canlii_live scraper (litigation/regulatory signals)
  - law_firm_* scrapers (deal/case announcements)
  - SEDAR legal_contingency signal type (material disclosure)

EntityResolver already uses rapidfuzz token_sort + partial_ratio combined
scoring at threshold 82.0 — no additional fuzzy logic needed here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.entity_resolution import resolver
from app.services.mandate_confirmation import confirm_mandate

log = structlog.get_logger(__name__)

# Scrapers to hunt from (name prefix or exact match)
CANLII_SCRAPER = "canlii_live"
LAW_FIRM_PREFIX = "law_firm_%"
SEDAR_SIGNAL_TYPE = "legal_contingency"

# Only look at signals from the last N hours to avoid re-processing
LOOKBACK_HOURS = 26  # Slightly over 24h to handle timing gaps

# Minimum practice area hints bitmask weight to consider a signal actionable
# (signals with no practice area hints are too vague to auto-confirm)
MIN_SIGNAL_STRENGTH = 0.3

# Practice area to use when a signal's primary_practice_area is absent
FALLBACK_PRACTICE_AREA = "litigation_dispute_resolution"


async def hunt_from_canlii(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Hunt mandate confirmations from CanLII decision signals.

    CanLII signals indicate a company was party to a court decision —
    strong evidence of active litigation mandate.
    """
    signals = await _fetch_signals(
        db,
        scraper_name=CANLII_SCRAPER,
        extra_where="",
        hours=LOOKBACK_HOURS,
    )
    return await _resolve_and_confirm(db, signals, source="canlii")


async def hunt_from_law_firm_blogs(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Hunt mandate confirmations from law firm deal/case announcement signals.

    Law firm blog posts naming a client confirm a mandate has been engaged.
    """
    signals = await _fetch_signals(
        db,
        scraper_name=LAW_FIRM_PREFIX,
        extra_where="",
        hours=LOOKBACK_HOURS,
        name_like=True,
    )
    return await _resolve_and_confirm(db, signals, source="law_firm_blog")


async def hunt_from_sedar(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Hunt mandate confirmations from SEDAR legal contingency disclosures.

    When a public company discloses a legal contingency in a material change
    report it is a reliable indicator of active litigation or regulatory matter.
    """
    signals = await _fetch_signals(
        db,
        scraper_name=None,
        extra_where=f"AND signal_type = '{SEDAR_SIGNAL_TYPE}'",
        hours=LOOKBACK_HOURS,
    )
    return await _resolve_and_confirm(db, signals, source="sedar_legal_contingency")


async def run(db: AsyncSession) -> dict[str, int]:
    """
    Run all three hunters. Called by Agent 032 Celery task daily.

    Returns:
        {auto_confirmed, matched, unmatched}
    """
    # Ensure the resolver index is populated; rebuild if empty
    if not resolver._index:
        try:
            loaded = await resolver.rebuild(db)
            log.info("entity resolver rebuilt for confirmation hunter", entities=loaded)
        except Exception:
            log.exception("entity resolver rebuild failed — hunter aborting")
            return {"auto_confirmed": 0, "matched": 0, "unmatched": 0}

    results: list[dict[str, Any]] = []
    for hunt_fn in (hunt_from_canlii, hunt_from_law_firm_blogs, hunt_from_sedar):
        try:
            batch = await hunt_fn(db)
            results.extend(batch)
        except Exception:
            log.exception("hunter batch failed", hunter=hunt_fn.__name__)

    confirmed = [r for r in results if r.get("confirmed")]
    unmatched = [r for r in results if not r.get("confirmed")]

    log.info(
        "confirmation hunter complete",
        auto_confirmed=len(confirmed),
        unmatched=len(unmatched),
    )
    return {
        "auto_confirmed": len(confirmed),
        "matched": len(confirmed),
        "unmatched": len(unmatched),
    }


# ── Private helpers ────────────────────────────────────────────────────────────


_SQL_BY_EXACT_SCRAPER = text("""
    SELECT id, raw_entity_name, primary_practice_area,
           signal_strength, scraped_at, source_url, title
    FROM signal_records
    WHERE scraped_at >= :since
      AND signal_strength >= :min_strength
      AND raw_entity_name IS NOT NULL
      AND raw_entity_name != ''
      AND scraper_name = :scraper_name
    ORDER BY scraped_at DESC
    LIMIT 200
""")

_SQL_BY_SCRAPER_PREFIX = text("""
    SELECT id, raw_entity_name, primary_practice_area,
           signal_strength, scraped_at, source_url, title
    FROM signal_records
    WHERE scraped_at >= :since
      AND signal_strength >= :min_strength
      AND raw_entity_name IS NOT NULL
      AND raw_entity_name != ''
      AND scraper_name LIKE :scraper_name
    ORDER BY scraped_at DESC
    LIMIT 200
""")

_SQL_BY_SIGNAL_TYPE = text("""
    SELECT id, raw_entity_name, primary_practice_area,
           signal_strength, scraped_at, source_url, title
    FROM signal_records
    WHERE scraped_at >= :since
      AND signal_strength >= :min_strength
      AND raw_entity_name IS NOT NULL
      AND raw_entity_name != ''
      AND signal_type = :signal_type
    ORDER BY scraped_at DESC
    LIMIT 200
""")


async def _fetch_signals(
    db: AsyncSession,
    scraper_name: str | None,
    extra_where: str,
    hours: int,
    name_like: bool = False,
) -> list[dict[str, Any]]:
    """Fetch recent signal_records from the specified scraper."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    params: dict[str, Any] = {
        "since": since,
        "min_strength": MIN_SIGNAL_STRENGTH,
    }

    if extra_where and "signal_type" in extra_where:
        # Use the signal_type query (SEDAR legal_contingency path)
        params["signal_type"] = SEDAR_SIGNAL_TYPE
        query = _SQL_BY_SIGNAL_TYPE
    elif scraper_name is not None:
        params["scraper_name"] = scraper_name
        query = _SQL_BY_SCRAPER_PREFIX if name_like else _SQL_BY_EXACT_SCRAPER
    else:
        # No filter — fall back to exact scraper query with empty name (no results)
        return []

    try:
        result = await db.execute(query, params)
        rows = result.fetchall()
    except Exception:
        log.exception("signal fetch failed", scraper_name=scraper_name)
        return []

    return [
        {
            "signal_id": r[0],
            "raw_entity_name": r[1],
            "primary_practice_area": r[2] or FALLBACK_PRACTICE_AREA,
            "signal_strength": float(r[3]) if r[3] else 0.0,
            "scraped_at": r[4],
            "source_url": r[5],
            "title": r[6],
        }
        for r in rows
    ]


async def _resolve_and_confirm(
    db: AsyncSession,
    signals: list[dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    """
    For each signal, attempt entity resolution and create a confirmation.
    Returns list of result dicts with 'confirmed' bool.
    """
    results: list[dict[str, Any]] = []

    for sig in signals:
        raw_name: str = sig["raw_entity_name"]

        # Fuzzy match via EntityResolver (rapidfuzz, threshold 82.0)
        match = resolver.resolve(raw_name)

        if not match.matched:
            results.append({"signal_id": sig["signal_id"], "confirmed": False, "reason": "no_match"})
            continue

        practice_area = sig["primary_practice_area"] or FALLBACK_PRACTICE_AREA
        scraped_at: datetime = sig["scraped_at"]
        if scraped_at.tzinfo is None:
            scraped_at = scraped_at.replace(tzinfo=UTC)

        # Use scraped_at as the confirmed_at timestamp for auto-detections
        try:
            confirmation = await confirm_mandate(
                db=db,
                company_id=match.entity_id,  # type: ignore[arg-type]
                practice_area=practice_area,
                confirmed_at=scraped_at,
                source=source,
                evidence_url=sig.get("source_url"),
                is_auto_detected=True,
            )
            results.append({
                "signal_id": sig["signal_id"],
                "confirmed": True,
                "confirmation_id": confirmation.get("confirmation_id"),
                "matched_entity_id": match.entity_id,
                "match_score": match.score,
            })
        except Exception:
            log.exception(
                "auto-confirm failed",
                signal_id=sig["signal_id"],
                entity_id=match.entity_id,
            )
            results.append({"signal_id": sig["signal_id"], "confirmed": False, "reason": "db_error"})

    return results
