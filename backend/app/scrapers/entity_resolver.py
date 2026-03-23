"""
app/scrapers/entity_resolver.py — EntityResolver.

Maps raw company names/IDs from scraped data → canonical company_id in PostgreSQL.

Resolution hierarchy (highest confidence first):
  1. Exact SEDAR ID match              → confidence 1.0
  2. Exact CIK match (SEC EDGAR)       → confidence 1.0
  3. Exact ticker + exchange match     → confidence 0.99
  4. Exact normalized name match       → confidence 0.98
  5. Alias table lookup (normalized)   → confidence varies
  6. Fuzzy name match (RapidFuzz)      → confidence 0.75–0.95
  7. Unresolved                        → confidence 0.0 (saved as-is, resolved later)

Resolved company_ids are cached in Redis (TTL: 24h) to avoid repeat DB lookups.
"""
from __future__ import annotations
import re
import unicodedata
import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


def normalize_company_name(name: str) -> str:
    """
    Normalize a company name for matching.

    Steps:
      1. Unicode NFKD normalization
      2. Lowercase
      3. Remove legal suffixes (Inc., Ltd., Corp., etc.)
      4. Remove punctuation
      5. Collapse whitespace
    """
    if not name:
        return ""

    # Unicode normalize
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.lower().strip()

    # Remove common legal suffixes
    suffixes = [
        r"\binc\.?\b", r"\bltd\.?\b", r"\bcorp\.?\b", r"\bllc\.?\b",
        r"\blp\.?\b", r"\bllp\.?\b", r"\bco\.?\b", r"\bcompany\b",
        r"\bcorporation\b", r"\blimited\b", r"\bincorporated\b",
        r"\bpartnership\b", r"\bholdings?\b", r"\bgroup\b",
        r"\binternational\b", r"\bcanada\b",
    ]
    for suffix in suffixes:
        name = re.sub(suffix, "", name)

    # Remove punctuation
    name = re.sub(r"[^\w\s]", " ", name)

    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


class EntityResolver:
    """
    Resolves raw company identifiers to canonical company_id.

    Usage:
        resolver = EntityResolver(db_session)
        company_id = await resolver.resolve(name="Royal Bank of Canada")
        company_id = await resolver.resolve(sedar_id="0000004")
        company_id = await resolver.resolve(ticker="RY", exchange="TSX")
    """

    def __init__(self, db: AsyncSession, redis_client=None) -> None:
        self._db = db
        self._redis = redis_client
        self._local_cache: dict[str, int | None] = {}

    async def resolve(
        self,
        *,
        name: str | None = None,
        sedar_id: str | None = None,
        cik: str | None = None,
        ticker: str | None = None,
        exchange: str | None = None,
        lei: str | None = None,
    ) -> tuple[int | None, float]:
        """
        Resolve to (company_id, confidence_score).

        Returns (None, 0.0) if no match found.
        """
        from app.models.company import Company, CompanyAlias

        # ── 1. SEDAR ID exact match ─────────────────────────────────────────
        if sedar_id:
            cache_key = f"resolve:sedar:{sedar_id}"
            cached = await self._cache_get(cache_key)
            if cached is not None:
                return cached, 1.0

            result = await self._db.execute(
                select(Company.id).where(Company.sedar_id == sedar_id).limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                await self._cache_set(cache_key, row)
                return row, 1.0

        # ── 2. CIK exact match ──────────────────────────────────────────────
        if cik:
            cache_key = f"resolve:cik:{cik}"
            cached = await self._cache_get(cache_key)
            if cached is not None:
                return cached, 1.0

            result = await self._db.execute(
                select(Company.id).where(Company.cik == cik).limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                await self._cache_set(cache_key, row)
                return row, 1.0

        # ── 3. Ticker + exchange exact match ────────────────────────────────
        if ticker and exchange:
            cache_key = f"resolve:ticker:{ticker.upper()}:{exchange.upper()}"
            cached = await self._cache_get(cache_key)
            if cached is not None:
                return cached, 0.99

            result = await self._db.execute(
                select(Company.id)
                .where(Company.ticker == ticker.upper(), Company.exchange == exchange.upper())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                await self._cache_set(cache_key, row)
                return row, 0.99

        # ── 4. Normalized name exact match ──────────────────────────────────
        if name:
            normalized = normalize_company_name(name)
            if not normalized:
                return None, 0.0

            cache_key = f"resolve:name:{normalized}"
            cached = await self._cache_get(cache_key)
            if cached is not None:
                return cached, 0.98

            # Check company table first
            result = await self._db.execute(
                select(Company.id)
                .where(Company.name_normalized == normalized)
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                await self._cache_set(cache_key, row)
                return row, 0.98

            # ── 5. Alias table lookup ─────────────────────────────────────
            result = await self._db.execute(
                select(CompanyAlias.company_id, CompanyAlias.confidence)
                .where(CompanyAlias.alias_normalized == normalized)
                .order_by(CompanyAlias.confidence.desc())
                .limit(1)
            )
            alias_row = result.one_or_none()
            if alias_row:
                company_id, confidence = alias_row
                await self._cache_set(cache_key, company_id)
                return company_id, float(confidence)

            # ── 6. Fuzzy match (only if rapidfuzz available) ──────────────
            try:
                company_id, score = await self._fuzzy_match(normalized)
                if company_id and score >= 0.85:
                    await self._cache_set(cache_key, company_id)
                    return company_id, score
            except ImportError:
                pass  # rapidfuzz not installed yet — OK, resolved in Phase 2

        # ── 7. Unresolved ─────────────────────────────────────────────────
        return None, 0.0

    async def _fuzzy_match(self, normalized: str) -> tuple[int | None, float]:
        """Fuzzy name match using rapidfuzz. Returns (company_id, score)."""
        from rapidfuzz import process, fuzz
        from app.models.company import Company

        result = await self._db.execute(
            select(Company.id, Company.name_normalized)
            .where(Company.status == "active")
            .limit(5000)
        )
        candidates = result.all()
        if not candidates:
            return None, 0.0

        names = [row.name_normalized for row in candidates]
        match = process.extractOne(normalized, names, scorer=fuzz.token_sort_ratio, score_cutoff=85)
        if match is None:
            return None, 0.0

        matched_name, score, idx = match
        return candidates[idx].id, score / 100.0

    async def _cache_get(self, key: str) -> int | None:
        if key in self._local_cache:
            return self._local_cache[key]
        if self._redis:
            try:
                val = await self._redis.get(key)
                if val:
                    company_id = int(val)
                    self._local_cache[key] = company_id
                    return company_id
            except Exception:
                pass
        return None

    async def _cache_set(self, key: str, company_id: int, ttl: int = 86400) -> None:
        self._local_cache[key] = company_id
        if self._redis:
            try:
                await self._redis.setex(key, ttl, str(company_id))
            except Exception:
                pass
