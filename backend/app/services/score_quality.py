"""
app/services/score_quality.py — Phase 12: Score quality reviewer.

Pulls last 30 days from prediction_accuracy_log (Phase 9), computes per-practice-area
precision/recall/lead-time, identifies the 5 worst performers, checks training data
volume, and stores results in score_quality_reports.

Also writes a human-readable markdown report to backend/reports/score_quality_{date}.md.

Called by Celery task agents.compute_usage_report (Agent 033) immediately after
the weekly usage report.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

# Minimum positive samples for a practice area to be considered "reliable"
MIN_POSITIVES_THRESHOLD = 50

# Report output directory (relative to backend/)
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"

# 34 ORACLE practice areas (matches bayesian_engine.py PRACTICE_AREAS)
PRACTICE_AREAS: list[str] = [
    "MA_Corporate",
    "Litigation_Dispute",
    "Regulatory_Compliance",
    "Employment_Labour",
    "Insolvency_Restructuring",
    "Securities_Capital",
    "Competition_Antitrust",
    "Privacy_Cybersecurity",
    "Environmental_Indigenous",
    "Tax",
    "Real_Estate_Construction",
    "Banking_Finance",
    "Intellectual_Property",
    "Immigration_Corporate",
    "Infrastructure_Project",
    "Wills_Estates",
    "Administrative_Public",
    "Arbitration_International",
    "Class_Actions",
    "Construction_Infrastructure_Disputes",
    "Defamation_Media",
    "Financial_Regulatory",
    "Franchise_Distribution",
    "Health_Life_Sciences",
    "Insurance_Reinsurance",
    "International_Trade",
    "Mining_Natural_Resources",
    "Municipal_Land_Use",
    "NFP_Charity",
    "Pension_Benefits",
    "Product_Liability",
    "Sports_Entertainment",
    "Technology_Fintech",
    "Data_Privacy_Technology",
]


async def compute_score_quality_report(db: AsyncSession) -> dict[str, Any]:
    """
    Compute score quality report for the last 30 days.

    Reads from prediction_accuracy_log (Phase 9 table).
    Falls back gracefully if that table does not yet exist.

    Returns a dict matching the score_quality_reports schema.
    Persists to score_quality_reports table + writes .md file.
    """
    today = date.today()
    since = datetime.now(UTC) - timedelta(days=30)

    summary = await _compute_accuracy_by_practice_area(db, since)
    worst_five = _identify_worst_five(summary)

    report: dict[str, Any] = {
        "report_date": today,
        "summary": summary,
        "worst_five": worst_five,
    }

    # ── Persist to DB ──────────────────────────────────────────────────────────
    try:
        await db.execute(
            text(
                """
                INSERT INTO score_quality_reports (report_date, summary, worst_five)
                VALUES (:report_date, :summary::jsonb, :worst_five::jsonb)
                """
            ),
            {
                "report_date": today,
                "summary": json.dumps(summary),
                "worst_five": json.dumps(worst_five),
            },
        )
        await db.commit()
    except Exception:
        log.exception("score_quality: failed to persist report")

    # ── Write markdown ─────────────────────────────────────────────────────────
    _write_markdown_report(report)

    log.info(
        "score_quality.computed",
        report_date=str(today),
        worst_five=worst_five,
        total_practice_areas=len(summary),
    )
    return report


async def get_latest_score_quality_report(db: AsyncSession) -> dict[str, Any] | None:
    """Return the most recently stored score_quality_reports row."""
    row = (
        await db.execute(
            text(
                """
                SELECT report_date, summary, worst_five, created_at
                FROM score_quality_reports
                ORDER BY report_date DESC
                LIMIT 1
                """
            )
        )
    ).first()

    if row is None:
        return None

    return {
        "report_date": str(row.report_date),
        "summary": row.summary or [],
        "worst_five": row.worst_five or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def _compute_accuracy_by_practice_area(
    db: AsyncSession,
    since: datetime,
) -> list[dict[str, Any]]:
    """
    Pull prediction_accuracy_log and mandate_labels to compute per-PA metrics.
    Returns graceful empty list if tables don't exist yet (Phases 9+ not yet run).
    """
    try:
        accuracy_rows = (
            await db.execute(
                text(
                    """
                    SELECT
                        practice_area,
                        COUNT(*) AS total,
                        SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) AS correct,
                        AVG(lead_days) AS avg_lead_days
                    FROM prediction_accuracy_log
                    WHERE logged_at >= :since
                    GROUP BY practice_area
                    """
                ),
                {"since": since},
            )
        ).all()
    except Exception:
        log.warning("score_quality: prediction_accuracy_log not available (Phase 9 pending)")
        accuracy_rows = []

    # Build accuracy map
    accuracy_map: dict[str, dict[str, Any]] = {}
    for row in accuracy_rows:
        total = row.total or 0
        correct = row.correct or 0
        accuracy_map[row.practice_area] = {
            "sample_count": total,
            "precision": round(correct / total, 4) if total > 0 else None,
            "avg_lead_days": round(float(row.avg_lead_days), 1) if row.avg_lead_days else None,
        }

    # Check training data volume from mandate_labels
    label_counts = await _get_label_counts(db)

    summary: list[dict[str, Any]] = []
    for pa in PRACTICE_AREAS:
        acc = accuracy_map.get(pa, {})
        label_count = label_counts.get(pa, 0)
        summary.append(
            {
                "practice_area": pa,
                "precision": acc.get("precision"),
                "recall": None,  # recall requires denominator = all real mandates (out of scope here)
                "avg_lead_days": acc.get("avg_lead_days"),
                "sample_count": acc.get("sample_count", 0),
                "label_count": label_count,
                "low_data_flag": label_count < MIN_POSITIVES_THRESHOLD,
            }
        )

    return summary


async def _get_label_counts(db: AsyncSession) -> dict[str, int]:
    """Count positive mandate_labels per practice area."""
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT practice_area, COUNT(*) AS cnt
                    FROM mandate_labels
                    WHERE label = 1
                    GROUP BY practice_area
                    """
                )
            )
        ).all()
        return {row.practice_area: row.cnt for row in rows}
    except Exception:
        log.warning("score_quality: mandate_labels not available")
        return {}


def _identify_worst_five(summary: list[dict[str, Any]]) -> list[str]:
    """Return the 5 practice areas with lowest precision (excluding None)."""
    ranked = [s for s in summary if s.get("precision") is not None and s["sample_count"] >= 5]
    ranked.sort(key=lambda s: s["precision"])  # type: ignore[arg-type]
    return [s["practice_area"] for s in ranked[:5]]


def _write_markdown_report(report: dict[str, Any]) -> None:
    """Write human-readable markdown report to backend/reports/."""
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_date = report["report_date"]
        filepath = REPORTS_DIR / f"score_quality_{report_date}.md"

        lines = [
            f"# ORACLE Score Quality Report — {report_date}",
            "",
            "## Worst 5 Practice Areas (lowest precision, last 30 days)",
            "",
        ]
        for pa in report.get("worst_five", []):
            lines.append(f"- {pa}")

        lines += [
            "",
            "## Full Summary",
            "",
            "| Practice Area | Precision | Avg Lead Days | Samples | Low Data? |",
            "|---|---|---|---|---|",
        ]

        for row in report.get("summary", []):
            prec = f"{row['precision']:.3f}" if row.get("precision") is not None else "N/A"
            lead = f"{row['avg_lead_days']:.1f}d" if row.get("avg_lead_days") else "N/A"
            low = "⚠️" if row.get("low_data_flag") else ""
            lines.append(
                f"| {row['practice_area']} | {prec} | {lead} | {row['sample_count']} | {low} |"
            )

        lines += ["", f"*Generated: {datetime.now(UTC).isoformat()}*", ""]
        filepath.write_text("\n".join(lines), encoding="utf-8")
        log.info("score_quality.report_written", path=str(filepath))
    except Exception:
        log.warning("score_quality: failed to write markdown report")
