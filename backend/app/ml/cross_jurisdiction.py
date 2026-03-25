"""
app/ml/cross_jurisdiction.py — Enhancement 8: Cross-jurisdiction risk propagation.

When a US company (EDGAR) has a regulatory/legal event, propagate signal
to Canadian subsidiaries and sector peers.

Propagation graph maintained in MongoDB: oracle_cross_jurisdiction_links
Link types: subsidiary, peer_same_sector, competitor

Adds cross_jurisdiction_signal feature to company_features.
Celery task: agents.run_cross_jurisdiction_propagation — daily.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)

# Propagation decay: how much signal strength carries across jurisdictions
LINK_DECAY: dict[str, float] = {
    "subsidiary": 0.85,  # parent's signal propagates strongly to subsidiary
    "peer_same_sector": 0.40,  # peer event = moderate warning
    "competitor": 0.25,  # competitor event = weak warning
}

# Signal types that propagate across jurisdictions
PROPAGATING_SIGNAL_TYPES: set[str] = {
    "osc_enforcement",
    "competition_investigation",
    "fintrac_noncompliance",
    "osfi_supervisory",
    "edgar_8k",
    "edgar_conf_treatment",
    "edgar_merger_confirmed",
    "sec_aaer",  # SEC accounting enforcement
    "news_investigation",
    "news_merger",
    "news_data_breach",
    "canlii_class_action",
    "canlii_ccaa",
}

# Minimum source signal strength to bother propagating
MIN_SOURCE_STRENGTH: float = 0.5


@dataclass
class PropagatedSignal:
    """A signal that has been propagated from a source company to a target."""

    target_company_id: int
    source_company_id: int
    source_signal_type: str
    source_signal_strength: float
    propagated_strength: float
    link_type: str
    propagated_at: str


def compute_propagated_signal(
    source_strength: float,
    link_type: str,
) -> float:
    """
    Compute propagated signal strength across jurisdiction link.

    Args:
        source_strength: Original signal strength (0–1).
        link_type:       "subsidiary", "peer_same_sector", or "competitor".
    Returns:
        Propagated strength (0–1), 0.0 if link type unknown.
    """
    decay = LINK_DECAY.get(link_type, 0.0)
    return float(source_strength * decay)


def propagate_signals(
    trigger_events: list[dict[str, Any]],
    jurisdiction_links: list[dict[str, Any]],
) -> list[PropagatedSignal]:
    """
    Propagate signals from source companies to linked target companies.

    Args:
        trigger_events: List of {company_id, signal_type, signal_strength, jurisdiction}.
                        These are the raw events triggering propagation.
        jurisdiction_links: List of {source_company_id, target_company_id, link_type}.
                        From MongoDB oracle_cross_jurisdiction_links collection.

    Returns:
        List of PropagatedSignal objects to store.
    """
    if not trigger_events or not jurisdiction_links:
        return []

    # Build link index: source_company_id → list of {target, link_type}
    link_index: dict[int, list[dict[str, Any]]] = {}
    for link in jurisdiction_links:
        src = link.get("source_company_id")
        if src is None:
            continue
        link_index.setdefault(src, []).append(link)

    propagated: list[PropagatedSignal] = []
    now = datetime.now(tz=UTC).isoformat()

    for event in trigger_events:
        company_id = event.get("company_id")
        signal_type = event.get("signal_type", "")
        strength = float(event.get("signal_strength", 0.0))

        # Only propagate qualifying signal types with sufficient strength
        if signal_type not in PROPAGATING_SIGNAL_TYPES:
            continue
        if strength < MIN_SOURCE_STRENGTH:
            continue

        for link in link_index.get(company_id, []):
            target_id = link.get("target_company_id")
            link_type = link.get("link_type", "peer_same_sector")

            if target_id is None or target_id == company_id:
                continue

            prop_strength = compute_propagated_signal(strength, link_type)
            if prop_strength < 0.05:
                continue  # too weak to store

            propagated.append(
                PropagatedSignal(
                    target_company_id=target_id,
                    source_company_id=company_id,
                    source_signal_type=signal_type,
                    source_signal_strength=strength,
                    propagated_strength=prop_strength,
                    link_type=link_type,
                    propagated_at=now,
                )
            )

    log.info(
        "cross_jurisdiction: %d propagated signals from %d trigger events",
        len(propagated),
        len(trigger_events),
    )
    return propagated


def aggregate_cross_jurisdiction_feature(
    company_id: int,
    propagated_signals: list[PropagatedSignal],
) -> float:
    """
    Aggregate incoming propagated signals into a single feature value.

    Uses max pooling across signal types (one strong signal is enough).
    Combined using convergence formula: P = 1 - prod(1 - p_i).

    Args:
        company_id:          Target company to aggregate for.
        propagated_signals:  All incoming propagated signals (pre-filtered).
    Returns:
        cross_jurisdiction_signal feature value in [0, 1].
    """
    incoming = [s for s in propagated_signals if s.target_company_id == company_id]
    if not incoming:
        return 0.0

    # Convergence formula: multiple independent signals compound
    combined = 1.0
    for sig in incoming:
        combined *= 1.0 - sig.propagated_strength

    return float(1.0 - combined)


async def fetch_jurisdiction_links_from_mongo(
    mongo_db: Any,
) -> list[dict[str, Any]]:
    """
    Fetch cross-jurisdiction company links from MongoDB.

    Args:
        mongo_db: Motor AsyncIOMotorDatabase instance.
    Returns:
        List of {source_company_id, target_company_id, link_type}
    """
    try:
        cursor = mongo_db["cross_jurisdiction_links"].find(
            {},
            {"_id": 0, "source_company_id": 1, "target_company_id": 1, "link_type": 1},
        )
        records = await cursor.to_list(length=100_000)
        log.info("Fetched %d cross-jurisdiction links from MongoDB", len(records))
        return records
    except Exception:
        log.exception("Failed to fetch cross-jurisdiction links")
        return []


async def upsert_jurisdiction_link(
    mongo_db: Any,
    source_company_id: int,
    target_company_id: int,
    link_type: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Upsert a cross-jurisdiction link in MongoDB."""
    try:
        doc = {
            "link_type": link_type,
            "last_verified_at": datetime.now(tz=UTC),
            **(metadata or {}),
        }
        await mongo_db["cross_jurisdiction_links"].update_one(
            {
                "source_company_id": source_company_id,
                "target_company_id": target_company_id,
            },
            {"$set": doc},
            upsert=True,
        )
    except Exception:
        log.exception(
            "Failed to upsert jurisdiction link %d→%d",
            source_company_id,
            target_company_id,
        )
