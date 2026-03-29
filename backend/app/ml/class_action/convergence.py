"""
Class Action Convergence Engine.

Takes all signals for a company and computes:
1. class_action_probability: 0.0–1.0 (overall likelihood)
2. predicted_type: most likely class action category
3. time_horizon_days: estimated days until filing (30/60/90)
4. contributing_signals: ranked list of signals driving the score
5. confidence: how confident the model is in its prediction
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.database_sync import get_sync_db
from app.models.class_action_score import ClassActionScore
from app.models.company import Company
from app.models.signal import SignalRecord

# Signal weights (calibrated from historical Canadian class action data)
SIGNAL_WEIGHTS = {
    "regulatory_enforcement": 0.85,
    "regulatory_sec_enforcement": 0.85,
    "securities_restatement": 0.90,
    "stock_price_drop_20pct": 0.75,
    "consumer_complaint_spike": 0.70,
    "recall_health_canada": 0.80,
    "recall_transport_canada": 0.80,
    "recall_cpsc_us": 0.75,
    "privacy_breach_report": 0.85,
    "insider_selling_spike": 0.65,
    "media_coverage_spike": 0.60,
    "class_action_same_sector": 0.50,
    "executive_departure": 0.55,
    "auditor_change": 0.60,
    "going_concern_note": 0.70,
    "layoff_signal": 0.55,
    "environmental_violation": 0.75,
    "competition_bureau_investigation": 0.80,
}

# Type inference rules
TYPE_INFERENCE = {
    "securities_capital_markets": [
        "securities_restatement",
        "stock_price_drop_20pct",
        "insider_selling_spike",
        "regulatory_sec_enforcement",
    ],
    "product_liability": [
        "recall_health_canada",
        "recall_transport_canada",
        "recall_cpsc_us",
        "consumer_complaint_spike",
    ],
    "privacy_cybersecurity": ["privacy_breach_report", "privacy_provincial_finding"],
    "employment_labour": ["layoff_signal", "executive_departure"],
    "environmental_indigenous_energy": ["environmental_violation"],
    "competition_antitrust": ["competition_bureau_investigation"],
}

DECAY_HALF_LIFE = 30.0  # days

def score_company(company_id: int) -> ClassActionScore | None:
    """Computes Bayesian convergence of all signals for a company."""
    with get_sync_db() as db:
        company = db.get(Company, company_id)
        if not company:
            return None

        # Fetch signals
        signals = db.execute(
            select(SignalRecord).where(SignalRecord.company_id == company_id)
        ).scalars().all()

        if not signals:
            return None

        now = datetime.now(tz=UTC)
        contributing_signals = []
        
        # We will use Noisy-OR to combine probabilities
        combined_prob = 1.0
        type_scores: dict[str, float] = {k: 0.0 for k in TYPE_INFERENCE}
        
        for sig in signals:
            stype = sig.signal_type
            raw_weight = SIGNAL_WEIGHTS.get(stype, 0.0)
            
            if raw_weight == 0.0:
                continue
                
            age_days = (now - min(sig.published_at or sig.scraped_at, now)).total_seconds() / 86400
            
            # Signal decay: signals older than 90 days get exponentially decayed weights
            weight = raw_weight
            if age_days > 90:
                decay_factor = math.exp(-math.log(2) * (age_days - 90) / DECAY_HALF_LIFE)
                weight *= decay_factor
                
            # Noisy-OR inversion
            combined_prob *= (1.0 - weight)
            
            contributing_signals.append({
                "signal_type": stype,
                "weight": weight,
                "source_id": sig.source_id,
                "date": (sig.published_at or sig.scraped_at).isoformat()
            })
            
            # Accumulate scores for predicted type
            for cat, rules in TYPE_INFERENCE.items():
                if stype in rules:
                    type_scores[cat] += weight

        # Final probability
        prob = 1.0 - combined_prob
        
        # Baseline probability if no signals match
        if prob == 0.0:
            prob = 0.01

        # Sector amplification
        if company.sector:
            # Check if any other company in the same sector has a class action
            # We proxy this by looking at high probability in the class action scores
            q = select(ClassActionScore).join(Company).where(
                Company.sector == company.sector,
                Company.id != company_id,
                ClassActionScore.probability > 0.8
            ).limit(1)
            has_peer_action = db.execute(q).scalar_one_or_none()
            if has_peer_action:
                prob = min(prob * 1.3, 0.99)
                contributing_signals.append({
                    "signal_type": "sector_amplification",
                    "weight": prob * 0.3,
                    "source_id": "system",
                    "date": now.isoformat()
                })

        # Infer Type
        predicted_type = max(type_scores.items(), key=lambda x: x[1])[0] if any(type_scores.values()) else "unknown"

        # Time horizon days
        if prob > 0.8:
            time_horizon_days = 30
        elif prob > 0.6:
            time_horizon_days = 60
        else:
            time_horizon_days = 90

        # Confidence correlates with the number of contributing signals
        confidence = min(len(contributing_signals) * 0.2 + 0.3, 0.95)

        contributing_signals.sort(key=lambda x: x["weight"], reverse=True)

        # Upsert
        existing = db.execute(select(ClassActionScore).where(ClassActionScore.company_id == company_id)).scalar_one_or_none()
        
        if existing:
            existing.probability = prob
            existing.predicted_type = predicted_type
            existing.time_horizon_days = time_horizon_days
            existing.contributing_signals = contributing_signals[:10]  # top 10
            existing.confidence = confidence
            existing.scored_at = now
            score_obj = existing
        else:
            score_obj = ClassActionScore(
                company_id=company_id,
                probability=prob,
                predicted_type=predicted_type,
                time_horizon_days=time_horizon_days,
                contributing_signals=contributing_signals[:10],
                confidence=confidence,
                scored_at=now
            )
            db.add(score_obj)

        db.commit()
        db.refresh(score_obj)
        return score_obj

def score_all_companies() -> list[ClassActionScore]:
    """Batch scoring, called by Celery nightly."""
    scores = []
    with get_sync_db() as db:
        company_ids = db.execute(select(Company.id).where(Company.status == "active")).scalars().all()
        
    for cid in company_ids:
        sc = score_company(cid)
        if sc:
            scores.append(sc)
            
    return scores

def get_top_risks(n: int = 20) -> list[ClassActionScore]:
    """Highest risk companies."""
    with get_sync_db() as db:
        items = db.execute(
            select(ClassActionScore)
            .order_by(ClassActionScore.probability.desc())
            .limit(n)
        ).scalars().all()
        for x in items:
            db.expunge(x)
        return list(items)
