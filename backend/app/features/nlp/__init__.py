"""
app/features/nlp/__init__.py — NLP Features (12 features).

These features extract signals from text content in signal_records.
Phase 4 LLM training will improve these with fine-tuned models.
In Phase 2, we use rule-based + statistical NLP (fast, no GPU needed).

Libraries: rapidfuzz (matching), nltk (tokenization), spacy (NER — if available),
           numpy (statistics). No torch dependency in Phase 2.

Features:
  legal_language_density      — fraction of tokens that are legal keywords
  regulatory_mention_count    — count of regulator names in window
  litigation_keyword_count    — count of litigation-related terms
  hedging_score               — fraction of sentences with hedging language
  blog_consensus_score        — how many Tier 1 firms published same practice area
  blog_practice_dominance     — which practice area dominates firm blogs for this company
  executive_departure_mentions — count of exec departure signals in window
  financial_distress_language_score — composite financial distress text score
  disclosure_tone_shift       — positive→negative tone shift vs prior period
  forward_guidance_negativity — negative forward guidance language score
  breach_regulatory_cooccurrence — data breach + regulatory mention same window
  ma_rumour_score             — M&A rumour signal from social/news co-occurrence
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, func, or_, select

from app.features.base import BaseFeature, FeatureValue, register_feature

log = structlog.get_logger(__name__)

# ── Keyword dictionaries ───────────────────────────────────────────────────────
_LEGAL_KEYWORDS = {
    "litigation",
    "lawsuit",
    "plaintiff",
    "defendant",
    "injunction",
    "judgment",
    "arbitration",
    "class action",
    "settlement",
    "damages",
    "liability",
    "breach",
    "negligence",
    "indemnification",
    "subrogation",
    "discovery",
    "deposition",
    "court order",
    "cease and desist",
    "regulatory action",
    "enforcement",
    "investigation",
    "penalty",
    "fine",
    "sanction",
    "compliance order",
    "receivership",
    "insolvency",
    "ccaa",
    "proposal",
    "trustee",
    "liquidation",
}

_HEDGING_PHRASES = [
    "may",
    "might",
    "could",
    "should",
    "would",
    "approximately",
    "estimated",
    "subject to",
    "if any",
    "no assurance",
    "cannot guarantee",
    "risk",
    "uncertainty",
    "potential",
    "anticipated",
    "expected to",
    "believes",
    "intends to",
    "plans to",
    "forward-looking",
    "forward looking",
]

_DISTRESS_KEYWORDS = {
    "going concern",
    "substantial doubt",
    "material uncertainty",
    "liquidity",
    "default",
    "covenant breach",
    "credit facility",
    "working capital deficit",
    "net loss",
    "negative cash flow",
    "restructuring",
    "impairment",
    "write-down",
    "receivership",
    "ccaa",
    "proposal",
    "creditor",
    "insolvency",
}

_REGULATORY_NAMES = {
    "osc",
    "bcsc",
    "asc",
    "amf",
    "fintrac",
    "osfi",
    "opc",
    "crtc",
    "competition bureau",
    "securities commission",
    "health canada",
    "eccc",
    "competition tribunal",
    "financial services regulatory",
    "ontario securities",
    "securities act",
    "pipeda",
}

_EXEC_DEPARTURE_KEYWORDS = {
    "resign",
    "stepped down",
    "departure",
    "left the company",
    "no longer",
    "effective immediately",
    "terminated",
    "dismissed",
    "retired",
    "replaced as",
    "transition of",
    "leadership change",
}

_NEGATIVE_GUIDANCE = {
    "below expectations",
    "revenue decline",
    "lower than anticipated",
    "challenging",
    "headwinds",
    "pressure",
    "softening",
    "deterioration",
    "withdrawal of guidance",
    "suspended dividend",
    "reduced forecast",
    "impairment charge",
    "restructuring charge",
    "write-off",
}


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer. No NLTK dependency."""
    return re.findall(r"\b[a-zA-Z][a-zA-Z\'-]*\b", text.lower())


def _sentence_count(text: str) -> int:
    return max(1, len(re.split(r"[.!?]+", text)))


async def _get_signals_text(
    company_id: int,
    cutoff: datetime,
    db: Any,
    source_prefixes: list[str] | None = None,
) -> list[str]:
    """Pull signal_text for a company in a time window."""
    from app.models.signal import SignalRecord

    conditions = [
        SignalRecord.company_id == company_id,
        SignalRecord.scraped_at >= cutoff,
        SignalRecord.signal_text.isnot(None),
    ]
    if source_prefixes:
        prefix_conditions = [SignalRecord.source_id.like(f"{p}%") for p in source_prefixes]
        conditions.append(or_(*prefix_conditions))

    result = await db.execute(select(SignalRecord.signal_text).where(and_(*conditions)))
    return [t for t in result.scalars().all() if t]


@register_feature
class LegalLanguageDensityFeature(BaseFeature):
    name = "legal_language_density"
    version = "v1"
    category = "nlp"
    description = "Fraction of tokens in signal text that are legal keywords. Range: 0–1."

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        cutoff = self._cutoff(horizon_days)
        try:
            texts = await _get_signals_text(
                company_id, cutoff, db, ["news_", "corporate_", "legal_"]
            )
            if not texts:
                return self._null_value(company_id, horizon_days)

            all_text = " ".join(texts)
            tokens = _tokenize(all_text)
            if not tokens:
                return self._null_value(company_id, horizon_days)

            legal_count = sum(1 for t in tokens if t in _LEGAL_KEYWORDS)
            # Also check bigrams
            bigrams = [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]
            legal_count += sum(1 for bg in bigrams if bg in _LEGAL_KEYWORDS)

            density = legal_count / max(len(tokens), 1)
            density_clipped = min(1.0, density * 5)  # Scale: 20%+ tokens = score 1.0

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=density_clipped,
                signal_count=len(texts),
                is_null=False,
                confidence=0.85,
                metadata={"raw_density": density, "legal_token_count": legal_count},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class HedgingScoreFeature(BaseFeature):
    name = "hedging_score"
    version = "v1"
    category = "nlp"
    description = (
        "Fraction of sentences containing hedging language. High = uncertainty/risk. Range: 0–1."
    )

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        cutoff = self._cutoff(horizon_days)
        try:
            texts = await _get_signals_text(company_id, cutoff, db, ["corporate_", "news_"])
            if not texts:
                return self._null_value(company_id, horizon_days)

            all_text = " ".join(texts).lower()
            sentences = re.split(r"[.!?]+", all_text)
            if not sentences:
                return self._null_value(company_id, horizon_days)

            hedged = sum(1 for s in sentences if any(phrase in s for phrase in _HEDGING_PHRASES))
            ratio = hedged / max(len(sentences), 1)

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=min(1.0, ratio),
                signal_count=len(texts),
                is_null=False,
                confidence=0.80,
                metadata={"hedged_sentences": hedged, "total_sentences": len(sentences)},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class RegulatoryMentionCountFeature(BaseFeature):
    name = "regulatory_mention_count"
    version = "v1"
    category = "nlp"
    description = "Count of distinct Canadian regulator names mentioned in window"

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        cutoff = self._cutoff(horizon_days)
        try:
            texts = await _get_signals_text(company_id, cutoff, db)
            if not texts:
                return self._null_value(company_id, horizon_days)

            all_text = " ".join(texts).lower()
            mentioned = sum(1 for name in _REGULATORY_NAMES if name in all_text)

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=float(mentioned),
                signal_count=len(texts),
                is_null=(mentioned == 0 and self.null_if_no_signals),
                confidence=0.90,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class FinancialDistressLanguageScoreFeature(BaseFeature):
    name = "financial_distress_language_score"
    version = "v1"
    category = "nlp"
    description = (
        "Composite score: count of distinct distress keywords × signal frequency. Range: 0–10."
    )

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        cutoff = self._cutoff(horizon_days)
        try:
            texts = await _get_signals_text(company_id, cutoff, db)
            if not texts:
                return self._null_value(company_id, horizon_days)

            all_text = " ".join(texts).lower()
            hit_keywords = {kw for kw in _DISTRESS_KEYWORDS if kw in all_text}
            # Score: distinct keywords found (max 10 for full score)
            score = min(10.0, float(len(hit_keywords)))

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=score,
                signal_count=len(texts),
                is_null=(score == 0 and self.null_if_no_signals),
                confidence=0.85,
                metadata={"keywords_found": sorted(hit_keywords)},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class ExecutiveDepartureMentionsFeature(BaseFeature):
    name = "executive_departure_mentions"
    version = "v1"
    category = "nlp"
    description = "Count of executive departure signals (resign, stepped down, etc.) in window"

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        cutoff = self._cutoff(horizon_days)
        try:
            texts = await _get_signals_text(
                company_id, cutoff, db, ["corporate_", "news_", "social_"]
            )
            if not texts:
                return self._null_value(company_id, horizon_days)

            count = sum(
                1
                for text in texts
                if text and any(kw in text.lower() for kw in _EXEC_DEPARTURE_KEYWORDS)
            )
            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=float(count),
                signal_count=len(texts),
                is_null=(count == 0 and self.null_if_no_signals),
                confidence=0.80,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class BlogConsensusScoreFeature(BaseFeature):
    name = "blog_consensus_score"
    version = "v1"
    category = "nlp"
    description = "How many Tier 1 Bay Street firms published about practice areas relevant to this company. Range: 0–15."

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        import json

        from app.models.signal import SignalRecord

        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_value).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.signal_type == "blog_practice_alert",
                    )
                )
            )
            rows = result.scalars().all()
            tier1_firms = set()
            for row in rows:
                try:
                    val = json.loads(row) if isinstance(row, str) else (row or {})
                    if val.get("tier") == 1:
                        tier1_firms.add(val.get("firm_id", ""))
                except (ValueError, TypeError, AttributeError):
                    continue

            score = float(len(tier1_firms))
            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=score,
                signal_count=len(rows),
                is_null=(score == 0 and self.null_if_no_signals),
                confidence=0.90,
                metadata={"tier1_firms": sorted(tier1_firms)},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class ForwardGuidanceNegativityFeature(BaseFeature):
    name = "forward_guidance_negativity"
    version = "v1"
    category = "nlp"
    description = "Score of negative forward guidance language in filings/news. Range: 0–1."

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        cutoff = self._cutoff(horizon_days)
        try:
            texts = await _get_signals_text(company_id, cutoff, db, ["corporate_", "news_"])
            if not texts:
                return self._null_value(company_id, horizon_days)

            all_text = " ".join(texts).lower()
            hit_count = sum(1 for phrase in _NEGATIVE_GUIDANCE if phrase in all_text)
            score = min(1.0, hit_count / 5.0)  # 5 hits = score of 1.0

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=score,
                signal_count=len(texts),
                is_null=(score == 0 and self.null_if_no_signals),
                confidence=0.78,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class DisclosureToneShiftFeature(BaseFeature):
    name = "disclosure_tone_shift"
    version = "v1"
    category = "nlp"
    description = "Negative shift in disclosure tone vs prior period. Positive = getting worse. Range: -1 to 1."

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        cutoff_current = self._cutoff(horizon_days)
        cutoff_prior = cutoff_current - timedelta(days=horizon_days)

        async def _distress_ratio(start: datetime, end: datetime) -> float:
            from app.models.signal import SignalRecord

            result = await db.execute(
                select(SignalRecord.signal_text).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= start,
                        SignalRecord.scraped_at < end,
                        SignalRecord.source_id.like("corporate_%"),
                    )
                )
            )
            texts = [t for t in result.scalars().all() if t]
            if not texts:
                return 0.0
            all_text = " ".join(texts).lower()
            hits = sum(1 for kw in _DISTRESS_KEYWORDS if kw in all_text)
            return min(1.0, hits / 10.0)

        try:
            current_ratio = await _distress_ratio(cutoff_current, datetime.now(tz=UTC))
            prior_ratio = await _distress_ratio(cutoff_prior, cutoff_current)
            shift = current_ratio - prior_ratio  # Positive = getting worse

            if current_ratio == 0 and prior_ratio == 0:
                return self._null_value(company_id, horizon_days)

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=max(-1.0, min(1.0, shift)),
                is_null=False,
                confidence=0.75,
                metadata={"current_ratio": current_ratio, "prior_ratio": prior_ratio},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class BreachRegulatoryCooccurrenceFeature(BaseFeature):
    name = "breach_regulatory_cooccurrence"
    version = "v1"
    category = "nlp"
    description = "Binary: 1 if data breach + regulatory mention co-occur in same window (strong privacy/class action signal)"
    null_if_no_signals = False

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        from app.models.signal import SignalRecord

        cutoff = self._cutoff(horizon_days)
        try:
            breach_result = await db.execute(
                select(func.count(SignalRecord.id)).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.signal_type == "social_breach_detected",
                    )
                )
            )
            breach_count = breach_result.scalar() or 0

            regulatory_result = await db.execute(
                select(func.count(SignalRecord.id)).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.source_id.like("regulatory_%"),
                    )
                )
            )
            regulatory_count = regulatory_result.scalar() or 0

            has_both = 1.0 if (breach_count > 0 and regulatory_count > 0) else 0.0

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=has_both,
                is_null=False,
                confidence=0.92,
                metadata={"breach_signals": breach_count, "regulatory_signals": regulatory_count},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class LitigationKeywordCountFeature(BaseFeature):
    name = "litigation_keyword_count"
    version = "v1"
    category = "nlp"
    description = "Count of litigation-specific keywords across all signal texts in window"

    _LIT_KEYWORDS = {
        "sued",
        "suing",
        "plaintiff",
        "defendant",
        "class action",
        "lawsuit",
        "litigation",
        "trial",
        "verdict",
        "damages awarded",
        "judgment against",
        "court ruled",
        "appeal filed",
        "settlement reached",
        "injunction granted",
        "stay of proceedings",
        "statement of claim",
        "statement of defence",
    }

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        cutoff = self._cutoff(horizon_days)
        try:
            texts = await _get_signals_text(company_id, cutoff, db)
            if not texts:
                return self._null_value(company_id, horizon_days)

            all_text = " ".join(texts).lower()
            count = sum(1 for kw in self._LIT_KEYWORDS if kw in all_text)

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=float(count),
                signal_count=len(texts),
                is_null=(count == 0 and self.null_if_no_signals),
                confidence=0.88,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class MARumourScoreFeature(BaseFeature):
    name = "ma_rumour_score"
    version = "v1"
    category = "nlp"
    description = "M&A rumour composite: news + social + market signal co-occurrence. Range: 0–3."
    null_if_no_signals = False

    _MA_KEYWORDS = {
        "acquisition",
        "merger",
        "takeover",
        "bid",
        "going private",
        "strategic review",
        "strategic alternatives",
        "sale process",
        "offer to acquire",
        "arrangement agreement",
        "letter of intent",
        "term sheet",
        "due diligence",
        "definitive agreement",
    }

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        from app.models.signal import SignalRecord

        cutoff = self._cutoff(horizon_days)
        try:
            score = 0.0

            for prefix, weight in [("news_", 1.0), ("social_", 0.7), ("market_", 1.3)]:
                result = await db.execute(
                    select(SignalRecord.signal_text).where(
                        and_(
                            SignalRecord.company_id == company_id,
                            SignalRecord.scraped_at >= cutoff,
                            SignalRecord.source_id.like(f"{prefix}%"),
                        )
                    )
                )
                texts = [t for t in result.scalars().all() if t]
                for text in texts:
                    if any(kw in text.lower() for kw in self._MA_KEYWORDS):
                        score += weight
                        break  # Only add weight once per source category

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=min(3.0, score),
                is_null=False,
                confidence=0.75,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)
