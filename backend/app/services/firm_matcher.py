"""
app/services/firm_matcher.py — Law firm ↔ class action matcher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_action_score import ClassActionScore
from app.models.company import Company
from app.models.law_firm import LawFirm
from app.scrapers.law_blogs.firm_blogs import ALL_FIRMS

_ALL_PROVINCES = [
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NS",
    "NT",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
]

_PROVINCE_MAP = {
    "alberta": "AB",
    "british columbia": "BC",
    "manitoba": "MB",
    "new brunswick": "NB",
    "newfoundland and labrador": "NL",
    "nova scotia": "NS",
    "northwest territories": "NT",
    "nunavut": "NU",
    "ontario": "ON",
    "prince edward island": "PE",
    "quebec": "QC",
    "québec": "QC",
    "saskatchewan": "SK",
    "yukon": "YT",
}

_TYPE_ALIASES = {
    "securities_capital_markets": ["securities", "capital_markets"],
    "product_liability": ["product_liability", "consumer_protection"],
    "privacy_cybersecurity": ["privacy", "cybersecurity", "technology"],
    "employment_labour": ["employment", "labour", "employment_labour"],
    "environmental_indigenous_energy": ["environmental", "energy"],
    "competition_antitrust": ["competition", "antitrust", "regulatory"],
}


@dataclass
class FirmMatch:
    firm: LawFirm
    score: float
    reasons: list[str]
    side_fit: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "firm": {
                "id": self.firm.id,
                "name": self.firm.name,
                "tier": self.firm.tier,
                "hq_province": self.firm.hq_province,
                "website": self.firm.website,
                "is_plaintiff_firm": self.firm.is_plaintiff_firm,
                "is_defence_firm": self.firm.is_defence_firm,
                "lawyer_count": self.firm.lawyer_count,
                "class_action_lawyers": self.firm.class_action_lawyers,
            },
            "score": self.score,
            "reasons": self.reasons,
            "side_fit": self.side_fit,
        }


def _normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _normalize_province(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if len(raw) == 2:
        return raw.upper()
    return _PROVINCE_MAP.get(raw.lower())


def _practice_strengths_from_focus(focus: list[str]) -> dict[str, float]:
    base = {
        "securities": 0.62,
        "product_liability": 0.55,
        "privacy": 0.55,
        "employment": 0.55,
        "environmental": 0.50,
        "competition": 0.55,
    }
    for f in focus:
        lower = f.lower()
        if lower in ("securities", "capital_markets"):
            base["securities"] = max(base["securities"], 0.84)
        if lower in ("class_actions", "litigation", "consumer"):
            base["product_liability"] = max(base["product_liability"], 0.76)
        if lower in ("privacy", "technology"):
            base["privacy"] = max(base["privacy"], 0.78)
        if lower in ("employment", "labour"):
            base["employment"] = max(base["employment"], 0.80)
        if lower in ("environmental", "energy"):
            base["environmental"] = max(base["environmental"], 0.75)
        if lower in ("competition", "antitrust", "regulatory"):
            base["competition"] = max(base["competition"], 0.82)
    return base


def _default_track_record(practice_strengths: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {
            "case_type": "securities_capital_markets",
            "count": int(8 + practice_strengths.get("securities", 0.6) * 12),
            "avg_settlement": 38_000_000,
        },
        {
            "case_type": "product_liability",
            "count": int(6 + practice_strengths.get("product_liability", 0.5) * 10),
            "avg_settlement": 22_000_000,
        },
        {
            "case_type": "privacy_cybersecurity",
            "count": int(5 + practice_strengths.get("privacy", 0.5) * 10),
            "avg_settlement": 18_000_000,
        },
        {
            "case_type": "employment_labour",
            "count": int(5 + practice_strengths.get("employment", 0.5) * 8),
            "avg_settlement": 14_000_000,
        },
        {
            "case_type": "environmental_indigenous_energy",
            "count": int(3 + practice_strengths.get("environmental", 0.5) * 6),
            "avg_settlement": 19_000_000,
        },
        {
            "case_type": "competition_antitrust",
            "count": int(4 + practice_strengths.get("competition", 0.5) * 7),
            "avg_settlement": 26_000_000,
        },
    ]


async def seed_law_firms(db: AsyncSession) -> int:
    """Populate law_firms if empty. Returns number inserted."""
    existing = await db.scalar(select(func.count()).select_from(LawFirm))
    if (existing or 0) > 0:
        return 0

    firms: list[LawFirm] = []

    tier1 = [f for f in ALL_FIRMS if f.tier == 1][:15]
    for idx, firm in enumerate(tier1):
        strengths = _practice_strengths_from_focus(list(firm.practice_focus))
        province = "ON" if idx % 2 == 0 else "QC"
        firms.append(
            LawFirm(
                name=firm.firm_name,
                name_normalized=_normalize_name(firm.firm_name),
                tier=1,
                hq_province=province,
                offices=[
                    {"city": "Toronto", "province": "ON"},
                    {"city": "Montreal", "province": "QC"},
                    {"city": "Vancouver", "province": "BC"},
                    {"city": "Calgary", "province": "AB"},
                ],
                practice_strengths=strengths,
                class_action_track_record=_default_track_record(strengths),
                jurisdictions=_ALL_PROVINCES,
                website=firm.base_url or None,
                is_plaintiff_firm=False,
                is_defence_firm=True,
                lawyer_count=520 - (idx * 14),
                class_action_lawyers=46 - (idx // 2),
            )
        )

    plaintiff_firms = [
        ("Siskinds LLP", "ON", "https://www.siskinds.com"),
        ("Branch MacMaster LLP", "BC", "https://www.branchmacmaster.com"),
        ("Koskie Minsky LLP", "ON", "https://www.kmlaw.ca"),
        ("Merchant Law Group LLP", "SK", "https://www.merchantlaw.com"),
        ("Sotos LLP", "ON", "https://www.sotosllp.com"),
        ("Kim Orr Barristers P.C.", "ON", "https://www.kimorr.ca"),
        ("Camp Fiorante Matthews Mogerman LLP", "BC", "https://www.cfmlawyers.ca"),
        ("Rochon Genova LLP", "ON", "https://www.rochongenova.com"),
        ("Cavalluzzo LLP", "ON", "https://www.cavalluzzo.com"),
        ("Charney Lawyers", "ON", "https://www.charneylawyers.com"),
    ]
    for idx, (name, province, website) in enumerate(plaintiff_firms):
        strengths = {
            "securities": 0.78,
            "product_liability": 0.86,
            "privacy": 0.82,
            "employment": 0.74,
            "environmental": 0.70,
            "competition": 0.67,
        }
        firms.append(
            LawFirm(
                name=name,
                name_normalized=_normalize_name(name),
                tier=3 if idx < 7 else 4,
                hq_province=province,
                offices=[{"city": "Toronto", "province": province}],
                practice_strengths=strengths,
                class_action_track_record=[
                    {
                        "case_type": "product_liability",
                        "count": 24 - idx,
                        "avg_settlement": 41_000_000,
                    },
                    {
                        "case_type": "privacy_cybersecurity",
                        "count": 12 - (idx // 2),
                        "avg_settlement": 16_000_000,
                    },
                    {
                        "case_type": "securities_capital_markets",
                        "count": 10 - (idx // 3),
                        "avg_settlement": 34_000_000,
                    },
                ],
                jurisdictions=["ON", "BC", "QC", "AB"] if idx < 5 else [province, "ON"],
                website=website,
                is_plaintiff_firm=True,
                is_defence_firm=False,
                lawyer_count=75 - (idx * 2),
                class_action_lawyers=18 - (idx // 2),
            )
        )

    defence_groups = [
        ("McCarthy Tétrault Class Actions Group", "ON"),
        ("Osler Class Actions Defence Group", "ON"),
        ("Torys Litigation Group (Class Actions)", "ON"),
        ("Stikeman Elliott Defence Class Actions Team", "QC"),
        ("Blakes Class Action Defence Group", "ON"),
        ("Fasken National Class Actions Group", "QC"),
        ("Goodmans Class Actions Group", "ON"),
        ("BLG National Class Actions Group", "ON"),
        ("Norton Rose Fulbright Class Actions Team", "QC"),
        ("Dentons Canada Class Actions Defence", "ON"),
    ]
    for idx, (name, province) in enumerate(defence_groups):
        strengths = {
            "securities": 0.84,
            "product_liability": 0.79,
            "privacy": 0.75,
            "employment": 0.71,
            "environmental": 0.68,
            "competition": 0.80,
        }
        firms.append(
            LawFirm(
                name=name,
                name_normalized=_normalize_name(name),
                tier=2,
                hq_province=province,
                offices=[
                    {"city": "Toronto", "province": "ON"},
                    {"city": "Montreal", "province": "QC"},
                    {"city": "Calgary", "province": "AB"},
                ],
                practice_strengths=strengths,
                class_action_track_record=[
                    {
                        "case_type": "securities_capital_markets",
                        "count": 20 - idx,
                        "avg_settlement": 32_000_000,
                    },
                    {
                        "case_type": "competition_antitrust",
                        "count": 12 - (idx // 2),
                        "avg_settlement": 21_000_000,
                    },
                    {
                        "case_type": "privacy_cybersecurity",
                        "count": 10 - (idx // 2),
                        "avg_settlement": 14_000_000,
                    },
                ],
                jurisdictions=_ALL_PROVINCES,
                website="https://www.example.com",
                is_plaintiff_firm=False,
                is_defence_firm=True,
                lawyer_count=240 - (idx * 8),
                class_action_lawyers=26 - (idx // 2),
            )
        )

    db.add_all(firms)
    return len(firms)


def _jurisdiction_score(firm: LawFirm, company: Company) -> tuple[float, str]:
    target = _normalize_province(company.province)
    jurisdictions = {str(x).upper() for x in (firm.jurisdictions or []) if x}
    office_provinces = {
        str(item.get("province", "")).upper()
        for item in (firm.offices or [])
        if isinstance(item, dict)
    }
    if not target:
        return 0.55, "Company province unknown; default national coverage weighting applied"
    if target in jurisdictions:
        return 1.0, f"Licensed in {target}"
    if target in office_provinces:
        return 0.75, f"Office presence in {target}"
    return 0.15, f"No direct licensing footprint in {target}"


def _practice_score(firm: LawFirm, predicted_type: str | None) -> tuple[float, str]:
    if not predicted_type:
        return 0.5, "No predicted class action type; neutral expertise weighting"
    strengths = firm.practice_strengths or {}
    aliases = _TYPE_ALIASES.get(predicted_type, [predicted_type])
    values: list[float] = []
    for key in aliases:
        val = strengths.get(key)
        if val is None:
            continue
        num = float(val)
        values.append(num / 100.0 if num > 1 else num)
    if values:
        score = max(values)
        return score, f"Strong {predicted_type.replace('_', ' ')} capability ({score:.0%})"
    return 0.4, f"Limited direct {predicted_type.replace('_', ' ')} specialization data"


def _track_record_score(firm: LawFirm, predicted_type: str | None) -> tuple[float, str]:
    records = firm.class_action_track_record or []
    if not records:
        return 0.25, "No formal class action track record metadata provided"

    def _norm(v: Any) -> str:
        return str(v or "").strip().lower()

    target = _norm(predicted_type)
    matching = [r for r in records if _norm(r.get("case_type")) == target] if target else records
    sample = matching if matching else records
    total_count = sum(int(r.get("count", 0) or 0) for r in sample)
    avg_settlement = (
        sum(float(r.get("avg_settlement", 0) or 0) for r in sample) / max(len(sample), 1)
    )
    count_score = min(total_count / 30.0, 1.0)
    settlement_score = min(avg_settlement / 50_000_000.0, 1.0)
    score = (count_score * 0.75) + (settlement_score * 0.25)
    if matching:
        return score, f"{total_count} prior matched-type class action mandates"
    return max(score * 0.75, 0.2), "General class action track record used as proxy"


def _capacity_score(firm: LawFirm, class_action_score: ClassActionScore) -> tuple[float, str]:
    probability = float(class_action_score.probability or 0.0)
    confidence = float(class_action_score.confidence or 0.5)
    signal_density = min(len(class_action_score.contributing_signals or []) / 10.0, 1.0)
    complexity = min((probability * 0.55) + (confidence * 0.25) + (signal_density * 0.20), 1.0)

    class_action_lawyers = float(firm.class_action_lawyers or 0)
    total_lawyers = float(firm.lawyer_count or 1)
    tier_bonus = {1: 1.0, 2: 0.85, 3: 0.7, 4: 0.58}.get(int(firm.tier or 4), 0.58)
    capacity = min(
        (min(class_action_lawyers / 30.0, 1.0) * 0.65)
        + (min(total_lawyers / 350.0, 1.0) * 0.25)
        + (tier_bonus * 0.10),
        1.0,
    )
    score = max(0.0, 1.0 - abs(capacity - complexity) * 0.9)
    return score, f"Capacity fit: {int(class_action_lawyers)} CA lawyers vs complexity {complexity:.2f}"


def _side_fit(side: str, firm: LawFirm) -> bool:
    side_norm = side.lower().strip()
    if side_norm == "plaintiff":
        return bool(firm.is_plaintiff_firm)
    if side_norm == "defence":
        return bool(firm.is_defence_firm)
    return bool(firm.is_plaintiff_firm or firm.is_defence_firm)


async def match_firms_to_class_action(
    db: AsyncSession,
    class_action_score: ClassActionScore,
    company: Company,
    side: str = "both",
    top_n: int = 5,
) -> list[FirmMatch]:
    """
    Score and rank law firms for a potential class action.

    Weights:
    1. Jurisdiction match: 0.30
    2. Practice area expertise: 0.35
    3. Track record: 0.25
    4. Capacity fit: 0.10
    """
    await seed_law_firms(db)
    result = await db.execute(select(LawFirm).order_by(LawFirm.tier.asc(), LawFirm.name.asc()))
    firms = list(result.scalars().all())

    matches: list[FirmMatch] = []
    for firm in firms:
        if not _side_fit(side, firm):
            continue

        jurisdiction, reason_j = _jurisdiction_score(firm, company)
        practice, reason_p = _practice_score(firm, class_action_score.predicted_type)
        record, reason_r = _track_record_score(firm, class_action_score.predicted_type)
        capacity, reason_c = _capacity_score(firm, class_action_score)

        total = (jurisdiction * 0.30) + (practice * 0.35) + (record * 0.25) + (capacity * 0.10)
        reasons = [reason_j, reason_p, reason_r, reason_c]
        side_fit = (
            "both"
            if firm.is_plaintiff_firm and firm.is_defence_firm
            else "plaintiff"
            if firm.is_plaintiff_firm
            else "defence"
        )
        matches.append(
            FirmMatch(
                firm=firm,
                score=round(total, 4),
                reasons=reasons,
                side_fit=side_fit,
            )
        )

    matches.sort(key=lambda item: item.score, reverse=True)
    return matches[: max(1, top_n)]
