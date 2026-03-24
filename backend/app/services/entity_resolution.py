"""
app/services/entity_resolution.py — Fuzzy company name matching.

The biggest data quality problem in the signal engine is entity resolution:
"Arctis Mining Corp" from SEDAR might appear as "Arctis Mining Corporation",
"ARCTIS MINING", or "Arctis Mining Corp." from other sources. Without
resolution, signals for the same company don't converge.

This module provides:
  1. Canonical name normalisation (strip legal suffixes, lowercase, etc.)
  2. Fuzzy matching via rapidfuzz against the known client/prospect DB
  3. A scored match result with confidence level
  4. A cached resolution table (reloaded nightly)

Algorithm:
  - Token-sort ratio handles word order differences ("Rail Corp Vantage" vs "Vantage Rail Corp")
  - Partial ratio handles abbreviations and truncations
  - Combined score = 0.6 * token_sort + 0.4 * partial
  - Match threshold: 82 (tuned empirically, see tests)
"""

import logging
import re
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# ── Legal suffix stripping ─────────────────────────────────────────────────────

_LEGAL_SUFFIXES = re.compile(
    r"\b(inc\.?|incorporated|corp\.?|corporation|llc|llp|ltd\.?|limited|"
    r"lp|l\.p\.|co\.?|company|plc|sa|ag|bv|gmbh|s\.a\.|n\.v\.|"
    r"group|enterprises?|partners?|associates?|"
    r"fund|capital|management|trust|reit|properties?)\b",
    re.IGNORECASE,
)

_DOTS = re.compile(r"\.")
_PUNCT = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")


def normalise(name: str) -> str:
    """
    Canonical form: strip legal suffixes, punctuation, extra whitespace, lowercase.
    "Arctis Mining Corp." → "arctis mining"
    "NORTHFIELD ENERGY PARTNERS LP" → "northfield energy"
    "A.B.C. Holdings" → "abc holdings"
    """
    if not name:
        return ""
    n = _LEGAL_SUFFIXES.sub("", name)
    n = _DOTS.sub("", n)        # Remove dots (handles abbreviations: A.B.C. → ABC)
    n = _PUNCT.sub(" ", n)      # Replace remaining punctuation with spaces
    n = _WHITESPACE.sub(" ", n).strip().lower()
    return n


@dataclass
class MatchResult:
    matched: bool
    entity_id: int | None  # client_id or prospect_id
    entity_type: str  # "client", "prospect", "unknown"
    canonical_name: str
    original_name: str
    score: float  # 0.0 – 100.0


class EntityResolver:
    """
    Resolves raw company names to canonical entity IDs.
    Maintains an in-memory index of known names refreshed from DB.

    Usage:
        resolver = EntityResolver()
        await resolver.rebuild(db_session)
        result = resolver.resolve("Arctis Mining Corp.")
    """

    MATCH_THRESHOLD = 82.0  # Minimum combined score to accept a match

    def __init__(self) -> None:
        # Maps normalised_name → (entity_id, entity_type, original_name)
        self._index: dict[str, tuple[int, str, str]] = {}
        self._norm_list: list[str] = []  # for rapidfuzz process.extractOne

    async def rebuild(self, db) -> int:
        """
        Load all clients and prospects from DB and build the index.
        Called at startup and nightly.
        Returns number of entities loaded.
        """
        from sqlalchemy import select

        from app.models import Client, Prospect

        new_index = {}

        # Clients
        result = await db.execute(select(Client.id, Client.name).where(Client.is_active))
        for client_id, name in result.all():
            norm = normalise(name)
            if norm:
                new_index[norm] = (client_id, "client", name)

        # Prospects
        result = await db.execute(select(Prospect.id, Prospect.name))
        for prospect_id, name in result.all():
            norm = normalise(name)
            if norm and norm not in new_index:
                new_index[norm] = (prospect_id, "prospect", name)

        self._index = new_index
        self._norm_list = list(new_index.keys())
        log.info("Entity resolver rebuilt: %d entities", len(self._index))
        return len(self._index)

    def resolve(self, raw_name: str) -> MatchResult:
        """
        Resolve a raw company name to a known entity.
        Returns MatchResult with matched=False if below threshold.
        """
        if not raw_name or not self._index:
            return MatchResult(
                matched=False,
                entity_id=None,
                entity_type="unknown",
                canonical_name=normalise(raw_name),
                original_name=raw_name,
                score=0.0,
            )

        query_norm = normalise(raw_name)

        # Exact match first (free)
        if query_norm in self._index:
            entity_id, entity_type, original = self._index[query_norm]
            return MatchResult(
                matched=True,
                entity_id=entity_id,
                entity_type=entity_type,
                canonical_name=query_norm,
                original_name=original,
                score=100.0,
            )

        # Fuzzy match
        result = process.extractOne(
            query_norm,
            self._norm_list,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=self.MATCH_THRESHOLD - 10,  # Lower cutoff for combined score
        )

        if result is None:
            return MatchResult(
                matched=False,
                entity_id=None,
                entity_type="unknown",
                canonical_name=query_norm,
                original_name=raw_name,
                score=0.0,
            )

        best_norm, sort_score, _ = result

        # Combined score with partial ratio for better accuracy
        partial_score = fuzz.partial_ratio(query_norm, best_norm)
        combined = 0.6 * sort_score + 0.4 * partial_score

        if combined < self.MATCH_THRESHOLD:
            return MatchResult(
                matched=False,
                entity_id=None,
                entity_type="unknown",
                canonical_name=query_norm,
                original_name=raw_name,
                score=combined,
            )

        entity_id, entity_type, original = self._index[best_norm]
        return MatchResult(
            matched=True,
            entity_id=entity_id,
            entity_type=entity_type,
            canonical_name=best_norm,
            original_name=original,
            score=combined,
        )

    def resolve_many(self, names: list[str]) -> list[MatchResult]:
        return [self.resolve(n) for n in names]

    def add_entity(self, name: str, entity_id: int, entity_type: str) -> None:
        """Add a single entity to the live index (no DB reload needed)."""
        norm = normalise(name)
        if norm:
            self._index[norm] = (entity_id, entity_type, name)
            if norm not in self._norm_list:
                self._norm_list.append(norm)


# Module-level singleton
resolver = EntityResolver()
