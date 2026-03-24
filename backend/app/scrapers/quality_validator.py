"""
app/scrapers/quality_validator.py — Signal data quality validator.

Validates ScraperResult objects against quality rules:
  1. Required fields present (source_id, signal_type)
  2. Confidence score in valid range (0.0–1.0)
  3. source_url has valid HTTP/HTTPS scheme if present
  4. published_at is not more than 24h in the future
  5. signal_value is JSON-serializable
  6. raw_company_name is not suspiciously long (>500 chars)
  7. practice_area_hints contain only known practice areas
  8. No duplicate source_url within the same scraper run (batch check)

Used by:
  - storage.persist_signals() (validate before writing)
  - canary Celery task (validate synthetic canary signal)
  - Phase 1B regression tests
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import structlog

from app.scrapers.base import ScraperResult

log = structlog.get_logger(__name__)

# Canonical practice area names — kept in sync with models/signal.py:PRACTICE_AREA_BITS
# Defined inline to avoid importing app.database at module load time.
KNOWN_PRACTICE_AREAS: frozenset[str] = frozenset(
    [
        "ma_corporate",
        "litigation",
        "regulatory_compliance",
        "employment_labour",
        "insolvency_restructuring",
        "securities_capital_markets",
        "competition_antitrust",
        "privacy_cybersecurity",
        "environmental_indigenous_energy",
        "tax",
        "real_estate_construction",
        "banking_finance",
        "intellectual_property",
        "immigration_corporate",
        "infrastructure_project_finance",
        "wills_estates",
        "administrative_public_law",
        "arbitration_international",
        "class_actions",
        "construction_infrastructure_disputes",
        "defamation_media_law",
        "financial_regulatory",
        "franchise_distribution",
        "health_law_life_sciences",
        "insurance_reinsurance",
        "international_trade_customs",
        "mining_natural_resources",
        "municipal_land_use",
        "not_for_profit_charity",
        "pension_benefits",
        "product_liability",
        "sports_entertainment",
        "technology_fintech_regulatory",
        "data_privacy_technology",
    ]
)


@dataclass
class ValidationResult:
    """Result of validating a single ScraperResult."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_signal(result: ScraperResult) -> ValidationResult:
    """
    Validate a single ScraperResult.

    Returns ValidationResult with valid=True only if no errors found.
    Warnings are informational — they do not mark the signal as invalid.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── Required fields ───────────────────────────────────────────────────────
    if not result.source_id:
        errors.append("source_id is empty")
    if not result.signal_type:
        errors.append("signal_type is empty")

    # ── Confidence score range ────────────────────────────────────────────────
    if not (0.0 <= result.confidence_score <= 1.0):
        errors.append(f"confidence_score {result.confidence_score:.3f} out of range [0.0, 1.0]")

    # ── URL scheme validation ─────────────────────────────────────────────────
    if result.source_url:
        parsed = urlparse(result.source_url)
        if parsed.scheme not in ("http", "https"):
            warnings.append(f"source_url has non-HTTP scheme: {parsed.scheme!r}")

    # ── Published-at temporal sanity ─────────────────────────────────────────
    if result.published_at:
        now = datetime.now(tz=UTC)
        delta_hours = (result.published_at - now).total_seconds() / 3600
        if delta_hours > 24:
            warnings.append(
                f"published_at is {delta_hours:.1f}h in the future — likely a parse error"
            )

    # ── Company name length ───────────────────────────────────────────────────
    if result.raw_company_name and len(result.raw_company_name) > 500:
        warnings.append(
            f"raw_company_name is {len(result.raw_company_name)} chars — likely a parse error"
        )

    # ── signal_value JSON-serializability ────────────────────────────────────
    if result.signal_value:
        try:
            json.dumps(result.signal_value)
        except (TypeError, ValueError) as exc:
            errors.append(f"signal_value is not JSON-serializable: {exc}")

    # ── Practice area hints validity ─────────────────────────────────────────
    unknown = [h for h in result.practice_area_hints if h not in KNOWN_PRACTICE_AREAS]
    if unknown:
        warnings.append(f"Unknown practice_area_hints: {unknown}")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_batch(results: list[ScraperResult]) -> dict[str, Any]:
    """
    Validate a list of ScraperResults.

    Returns a summary dict with:
      - total: int
      - valid: int
      - invalid: int
      - with_warnings: int
      - pass_rate: float (0.0–1.0)
      - details: list of per-result dicts
    """
    valid_count = 0
    invalid_count = 0
    warning_count = 0
    seen_urls: set[str] = set()
    details: list[dict[str, Any]] = []

    for result in results:
        vr = validate_signal(result)

        # Intra-batch duplicate URL detection
        if result.source_url:
            if result.source_url in seen_urls:
                vr.warnings.append(f"Duplicate source_url in batch: {result.source_url}")
            else:
                seen_urls.add(result.source_url)

        if vr.valid:
            valid_count += 1
        else:
            invalid_count += 1
            log.warning(
                "signal_validation_failed",
                source_id=result.source_id,
                signal_type=result.signal_type,
                errors=vr.errors,
            )

        if vr.warnings:
            warning_count += 1

        details.append(
            {
                "source_id": result.source_id,
                "signal_type": result.signal_type,
                "valid": vr.valid,
                "errors": vr.errors,
                "warnings": vr.warnings,
            }
        )

    total = len(results)
    return {
        "total": total,
        "valid": valid_count,
        "invalid": invalid_count,
        "with_warnings": warning_count,
        "pass_rate": valid_count / max(total, 1),
        "details": details,
    }
