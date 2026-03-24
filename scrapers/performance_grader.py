"""
app/scrapers/performance_grader.py — Scraper Performance Grader.

Assigns an A–F grade to each scraper based on four dimensions:
  1. Reliability    — success rate over last 30 days (weight: 35%)
  2. Yield          — avg records per successful run (weight: 30%)
  3. Signal Quality — avg confidence_score of records produced (weight: 20%)
  4. Freshness      — how recently the scraper ran successfully (weight: 15%)

Grade thresholds:
  A  ≥ 90   — Production grade. Keep as-is.
  B  ≥ 75   — Good. Monitor.
  C  ≥ 60   — Degraded. Investigate alternative sources.
  D  ≥ 40   — Poor. Redundancy chain must be active.
  F  < 40   — Dead. Replace or remove.

Used by:
  - Agent 009 (Scraper Grader) — scheduled weekly
  - Phase 1C redundancy chains — to decide which fallback to activate
  - Phase 1B health dashboard — to display grade badges
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import select, func, and_

log = structlog.get_logger(__name__)


@dataclass
class ScraperGrade:
    source_id: str
    source_name: str
    grade: str                   # A / B / C / D / F
    score: float                 # 0–100
    reliability_score: float     # 0–100
    yield_score: float           # 0–100
    quality_score: float         # 0–100
    freshness_score: float       # 0–100
    total_runs: int
    success_rate: float
    avg_records_per_run: float
    avg_confidence: float
    last_success_at: datetime | None
    hours_since_success: float
    recommendation: str
    graded_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


def _letter_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _recommendation(grade: str, source_id: str) -> str:
    recs = {
        "A": "Production grade. No action required.",
        "B": "Good. Monitor for degradation over next 14 days.",
        "C": f"Degraded. Activate redundancy chain for {source_id}. "
             "Investigate rate limiting or structural changes.",
        "D": f"Poor. Redundancy chain must be active now. "
             f"Begin alternative source discovery for {source_id}.",
        "F": f"Dead. {source_id} is not delivering signal. "
             "Replace with alternative or remove from pipeline.",
    }
    return recs[grade]


class ScraperPerformanceGrader:
    """
    Computes A–F performance grades for all registered scrapers.
    Reads from scraper_health and signal_records tables.
    """

    # Scoring weights (must sum to 1.0)
    W_RELIABILITY = 0.35
    W_YIELD       = 0.30
    W_QUALITY     = 0.20
    W_FRESHNESS   = 0.15

    # Yield benchmarks (records per run for 100 score)
    YIELD_BENCHMARKS: dict[str, float] = {
        "corporate_": 50.0,
        "legal_":     20.0,
        "regulatory_": 10.0,
        "jobs_":      100.0,
        "market_":    30.0,
        "news_":      40.0,
        "social_":    25.0,
        "geo_":       15.0,
        "lawblog_":    8.0,
    }
    DEFAULT_YIELD_BENCHMARK = 20.0

    # Freshness thresholds (hours) — after this, freshness score degrades
    FRESHNESS_OK_HOURS:     dict[str, float] = {
        "market_": 2.0,
        "news_":   4.0,
        "social_": 4.0,
        "corporate_": 12.0,
        "regulatory_": 12.0,
        "jobs_":    8.0,
        "geo_":    24.0,
        "legal_":  24.0,
        "lawblog_": 8.0,
    }
    DEFAULT_FRESHNESS_OK = 12.0

    def __init__(self, db: Any, lookback_days: int = 30) -> None:
        self._db = db
        self._lookback_days = lookback_days
        self._cutoff = datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)

    async def grade_all(self) -> list[ScraperGrade]:
        """Grade all scrapers and return sorted list (worst first)."""
        from app.scrapers.registry import ScraperRegistry
        from app.models.scraper_health import ScraperHealth

        grades: list[ScraperGrade] = []

        result = await self._db.execute(select(ScraperHealth))
        health_rows = {h.source_id: h for h in result.scalars().all()}

        for source_id in ScraperRegistry.all_ids():
            health = health_rows.get(source_id)
            grade = await self._grade_scraper(source_id, health)
            grades.append(grade)

        grades.sort(key=lambda g: g.score)
        return grades

    async def grade_one(self, source_id: str) -> ScraperGrade:
        from app.models.scraper_health import ScraperHealth
        result = await self._db.execute(
            select(ScraperHealth).where(ScraperHealth.source_id == source_id)
        )
        health = result.scalar_one_or_none()
        return await self._grade_scraper(source_id, health)

    async def _grade_scraper(self, source_id: str, health: Any) -> ScraperGrade:
        from app.scrapers.registry import ScraperRegistry

        try:
            scraper_cls = ScraperRegistry.get_class(source_id)
            source_name = scraper_cls.source_name
        except KeyError:
            source_name = source_id

        if not health:
            return ScraperGrade(
                source_id=source_id,
                source_name=source_name,
                grade="F",
                score=0.0,
                reliability_score=0.0,
                yield_score=0.0,
                quality_score=0.0,
                freshness_score=0.0,
                total_runs=0,
                success_rate=0.0,
                avg_records_per_run=0.0,
                avg_confidence=0.0,
                last_success_at=None,
                hours_since_success=9999.0,
                recommendation=_recommendation("F", source_id),
            )

        # ── Reliability score ──────────────────────────────────────────────────
        success_rate = (
            health.total_successes / max(health.total_runs, 1)
        )
        reliability_score = success_rate * 100.0

        # ── Yield score ────────────────────────────────────────────────────────
        benchmark = self.DEFAULT_YIELD_BENCHMARK
        for prefix, bench in self.YIELD_BENCHMARKS.items():
            if source_id.startswith(prefix):
                benchmark = bench
                break
        avg_records = health.avg_records_per_run
        yield_score = min(100.0, (avg_records / benchmark) * 100.0) if benchmark > 0 else 0.0

        # ── Quality score ──────────────────────────────────────────────────────
        avg_confidence = await self._get_avg_confidence(source_id)
        quality_score = avg_confidence * 100.0

        # ── Freshness score ────────────────────────────────────────────────────
        ok_hours = self.DEFAULT_FRESHNESS_OK
        for prefix, hours in self.FRESHNESS_OK_HOURS.items():
            if source_id.startswith(prefix):
                ok_hours = hours
                break

        last_success = health.last_success_at
        if last_success:
            if last_success.tzinfo is None:
                last_success = last_success.replace(tzinfo=timezone.utc)
            hours_since = (datetime.now(tz=timezone.utc) - last_success).total_seconds() / 3600
        else:
            hours_since = 9999.0

        if hours_since <= ok_hours:
            freshness_score = 100.0
        elif hours_since <= ok_hours * 3:
            freshness_score = max(0.0, 100.0 - ((hours_since - ok_hours) / (ok_hours * 2)) * 100.0)
        else:
            freshness_score = 0.0

        # ── Composite score ────────────────────────────────────────────────────
        composite = (
            self.W_RELIABILITY * reliability_score
            + self.W_YIELD * yield_score
            + self.W_QUALITY * quality_score
            + self.W_FRESHNESS * freshness_score
        )

        grade = _letter_grade(composite)

        return ScraperGrade(
            source_id=source_id,
            source_name=source_name,
            grade=grade,
            score=round(composite, 1),
            reliability_score=round(reliability_score, 1),
            yield_score=round(yield_score, 1),
            quality_score=round(quality_score, 1),
            freshness_score=round(freshness_score, 1),
            total_runs=health.total_runs,
            success_rate=round(success_rate, 3),
            avg_records_per_run=round(avg_records, 1),
            avg_confidence=round(avg_confidence, 3),
            last_success_at=last_success,
            hours_since_success=round(hours_since, 1),
            recommendation=_recommendation(grade, source_id),
        )

    async def _get_avg_confidence(self, source_id: str) -> float:
        from app.models.signal import SignalRecord
        try:
            result = await self._db.execute(
                select(func.avg(SignalRecord.confidence_score)).where(
                    and_(
                        SignalRecord.source_id == source_id,
                        SignalRecord.scraped_at >= self._cutoff,
                    )
                )
            )
            val = result.scalar()
            return float(val) if val is not None else 0.8
        except Exception:
            return 0.8

    async def get_summary(self) -> dict[str, Any]:
        """Return fleet-level grade distribution summary."""
        grades = await self.grade_all()
        dist: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for g in grades:
            dist[g.grade] += 1
        critical = [g for g in grades if g.grade in ("D", "F")]
        return {
            "total_scrapers": len(grades),
            "grade_distribution": dist,
            "fleet_avg_score": round(sum(g.score for g in grades) / max(len(grades), 1), 1),
            "critical_count": len(critical),
            "critical_scrapers": [
                {"source_id": g.source_id, "grade": g.grade, "score": g.score}
                for g in critical
            ],
            "graded_at": datetime.now(tz=timezone.utc).isoformat(),
        }
