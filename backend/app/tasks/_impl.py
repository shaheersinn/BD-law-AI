"""
app/tasks/_impl.py — async implementations for all Celery tasks.

These are pure async functions — Celery wrappers in celery_app.py call them
via asyncio.new_event_loop().run_until_complete().
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import (
    Alert,
    Client,
    JetTrack,
    Prospect,
    Trigger,
    TriggerSource,
)
from app.ml.churn_model import ChurnModel, ClientFeatures
from app.ml.convergence import (
    ScoredSignal,
    SIGNAL_WEIGHTS,
    convergence_score,
    crossed_threshold,
    threshold_label,
)
from app.ml.practice_classifier import PracticeAreaClassifier
from app.scrapers.edgar import EdgarScraper
from app.scrapers.enforcement import EnforcementScraper
from app.scrapers.jobs import JobsScraper
from app.scrapers.opensky import OpenSkyScraper
from app.scrapers.sedar import SedarScraper

log = logging.getLogger(__name__)

# ── Helper ─────────────────────────────────────────────────────────────────────

async def _persist_signals(session: AsyncSession, signals, source: str) -> int:
    """Deduplicate and persist a list of RawSignal objects to the triggers table.
    Uses entity resolver for accurate company matching instead of ILIKE.
    """
    from app.services.entity_resolution import resolver

    count = 0
    for sig in signals:
        # Deduplicate: same company + type + filed within 24h
        existing = await session.execute(
            select(Trigger).where(
                Trigger.company_name == sig.company_name,
                Trigger.trigger_type == sig.trigger_type,
                Trigger.filed_at >= sig.filed_at - timedelta(hours=24),
            )
        )
        if existing.scalars().first():
            continue

        # Use entity resolver for accurate client matching
        match = resolver.resolve(sig.company_name)
        client = None
        if match.matched and match.entity_type == "client":
            client_result = await session.execute(
                select(Client).where(Client.id == match.entity_id)
            )
            client = client_result.scalars().first()

        trigger = Trigger(
            source=source,
            trigger_type=sig.trigger_type,
            company_name=sig.company_name,
            client_id=client.id if client else None,
            title=sig.title,
            description=sig.description,
            url=sig.url,
            filed_at=sig.filed_at,
            urgency=sig.urgency,
            practice_area=sig.practice_area,
            practice_confidence=int(sig.base_weight * 100),
        )
        session.add(trigger)
        count += 1

    await session.commit()
    return count


# ── Scraper implementations ────────────────────────────────────────────────────

async def run_sedar_scrape() -> int:
    async with AsyncSessionLocal() as session:
        async with SedarScraper() as scraper:
            signals = await scraper.fetch_new(days_back=1)
        return await _persist_signals(session, signals, "SEDAR")


async def run_edgar_scrape() -> int:
    async with AsyncSessionLocal() as session:
        async with EdgarScraper() as scraper:
            signals = await scraper.fetch_new(days_back=2)
        return await _persist_signals(session, signals, "EDGAR")


async def run_enforcement_scrape() -> int:
    async with AsyncSessionLocal() as session:
        async with EnforcementScraper() as scraper:
            signals = await scraper.fetch_new()
        return await _persist_signals(session, signals, "OSC")


async def run_jobs_scrape() -> int:
    """Scrape job postings for all active clients + prospects."""
    async with AsyncSessionLocal() as session:
        # Build watchlist from clients + prospects
        clients = (await session.execute(select(Client).where(Client.is_active == True))).scalars().all()
        prospects = (await session.execute(select(Prospect))).scalars().all()
        watchlist = [c.name for c in clients] + [p.name for p in prospects]

        async with JobsScraper() as scraper:
            all_signals = []
            for company in watchlist[:50]:  # rate-limit
                sigs = await scraper.fetch_for_company(company)
                all_signals.extend(sigs)

        return await _persist_signals(session, all_signals, "JOBS")


async def run_canlii_scrape() -> int:
    from app.scrapers.canlii import CanLIIScraper

    async with AsyncSessionLocal() as session:
        clients = (await session.execute(select(Client).where(Client.is_active == True))).scalars().all()
        prospects = (await session.execute(select(Prospect))).scalars().all()
        watchlist = [c.name for c in clients] + [p.name for p in prospects]

        async with CanLIIScraper() as scraper:
            all_signals = []
            for company in watchlist[:30]:
                sigs = await scraper.search_company(company, days_back=7)
                all_signals.extend(sigs)

        return await _persist_signals(session, all_signals, "CANLII")


async def run_jet_scrape() -> int:
    """
    Fetch flight history for watchlisted tail numbers.
    Watchlist stored in a config table or hardcoded in settings.
    """
    # Production: load tail_number → company mapping from database
    # For now, we use a minimal hardcoded example set
    WATCHLIST = [
        {"tail": "c-fmtx", "company": "Arctis Mining Corp", "executive": "CEO", "icao24": "c0ffee", "warmth": 18},
        {"tail": "c-gxlp", "company": "Stellex Infrastructure", "executive": "CFO", "icao24": "c0ffef", "warmth": 44},
    ]

    async with AsyncSessionLocal() as session:
        scraper = OpenSkyScraper()
        new_tracks = 0

        for item in WATCHLIST:
            try:
                flights = await scraper.get_flights_for_aircraft(item["icao24"], days_back=14)
                result = scraper.analyse_flights(
                    company=item["company"],
                    tail_number=item["tail"].upper(),
                    executive=item["executive"],
                    flights=flights,
                    relationship_warmth=item["warmth"],
                )
                if result:
                    # Deduplicate: same company + same 14-day window
                    existing = await session.execute(
                        select(JetTrack).where(
                            JetTrack.company == result["company"],
                            JetTrack.departed_at >= datetime.now(timezone.utc) - timedelta(days=14),
                        )
                    )
                    if not existing.scalars().first():
                        track = JetTrack(**result)
                        session.add(track)
                        new_tracks += 1
            except Exception as e:
                log.warning("Jet scrape error for %s: %s", item["company"], e)

        await session.commit()
        await scraper.close()
        return new_tracks


# ── Convergence scoring ────────────────────────────────────────────────────────

async def run_scoring() -> dict:
    """
    Nightly scoring engine:
    1. For each company with signals in past 90 days, compute convergence score
    2. If score crosses a threshold, create an Alert
    3. Deliver alerts via notification service
    """
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as session:
        pa_classifier = PracticeAreaClassifier.get()
        notifier = NotificationService()
        alerts_fired = 0
        companies_scored = 0

        # Get distinct companies with recent triggers
        result = await session.execute(
            select(Trigger.company_name).distinct().where(
                Trigger.filed_at >= datetime.now(timezone.utc) - timedelta(days=90)
            )
        )
        companies = [r[0] for r in result.all()]

        for company in companies:
            companies_scored += 1
            # Load all signals for this company in past 90 days
            triggers_result = await session.execute(
                select(Trigger).where(
                    Trigger.company_name == company,
                    Trigger.filed_at >= datetime.now(timezone.utc) - timedelta(days=90),
                ).order_by(Trigger.filed_at.desc())
            )
            triggers = triggers_result.scalars().all()

            if not triggers:
                continue

            # Build scored signals
            scored = [
                ScoredSignal(
                    signal_type=_trigger_type_to_signal_key(t.trigger_type),
                    days_ago=(datetime.now(timezone.utc) - t.filed_at).days,
                )
                for t in triggers
            ]

            score = convergence_score(scored)
            if score < 50:
                continue

            # Get previous score from most recent alert
            prev_alert_result = await session.execute(
                select(Alert).where(Alert.company_name == company).order_by(Alert.fired_at.desc()).limit(1)
            )
            prev_alert = prev_alert_result.scalars().first()
            prev_score = prev_alert.score if prev_alert else 0.0

            threshold = crossed_threshold(prev_score, score)
            if not threshold:
                continue

            # Classify practice area
            practice, pa_conf, _ = pa_classifier.predict(scored)

            # Find matching client
            client_result = await session.execute(
                select(Client).where(Client.name.ilike(f"%{company[:20]}%"))
            )
            client = client_result.scalars().first()

            alert = Alert(
                company_name=company,
                client_id=client.id if client else None,
                is_existing_client=client is not None,
                score=score,
                prev_score=prev_score,
                threshold=threshold,
                practice_area=practice,
                pa_confidence=pa_conf,
                top_signals=[s.signal_type for s in scored[:3]],
            )
            session.add(alert)
            await session.flush()

            # Send notification
            try:
                await notifier.send_alert(alert, client)
            except Exception as e:
                log.error("Notification failed for %s: %s", company, e)

            alerts_fired += 1

        await session.commit()
        return {"companies_scored": companies_scored, "alerts_fired": alerts_fired}


async def run_churn_update() -> dict:
    """Recompute churn scores for all active clients using billing + contact data."""
    from app.services.churn_feature_service import extract_client_features

    model = ChurnModel.get()
    async with AsyncSessionLocal() as session:
        clients = (
            await session.execute(select(Client).where(Client.is_active == True))
        ).scalars().all()

        updated = 0
        for client in clients:
            try:
                features = await extract_client_features(session, client)
                score = model.score(features)
                client.churn_score = score
                client.churn_score_updated_at = datetime.now(timezone.utc)

                # Update risk level
                if score >= 75:
                    client.risk_level = "critical"
                elif score >= 55:
                    client.risk_level = "high"
                elif score >= 35:
                    client.risk_level = "medium"
                else:
                    client.risk_level = "low"

                updated += 1
            except Exception as e:
                log.warning("Churn update failed for %s: %s", client.name, e)

        await session.commit()
        return {"clients_updated": updated}


async def run_model_retrain() -> dict:
    """Retrain urgency + PA classifier from accumulated confirmed labels."""
    from pathlib import Path

    from app.config import get_settings
    from app.ml.urgency_model import train as train_urgency
    from app.ml.practice_classifier import train as train_pa

    settings = get_settings()

    results = {}

    urgency_csv = Path(settings.models_dir) / "training" / "urgency_training_data.csv"
    if urgency_csv.exists():
        try:
            metrics = train_urgency(str(urgency_csv))
            results["urgency"] = metrics
        except Exception as e:
            results["urgency_error"] = str(e)

    pa_csv = Path(settings.models_dir) / "training" / "pa_training_data.csv"
    if pa_csv.exists():
        try:
            metrics = train_pa(str(pa_csv))
            results["practice_area"] = metrics
        except Exception as e:
            results["pa_error"] = str(e)

    return results


# ── Helpers ────────────────────────────────────────────────────────────────────

def _trigger_type_to_signal_key(trigger_type: str) -> str:
    """Map a raw trigger_type string to a convergence signal key."""
    mapping = {
        "Material Change Report": "sedar_material_change",
        "Business Acquisition Report": "sedar_business_acquisition",
        "Confidential Treatment Request": "sedar_confidentiality",
        "Cease Trade Order": "sedar_cease_trade",
        "Going Concern Qualification": "sedar_going_concern",
        "Auditor Change": "sedar_auditor_change",
        "Director or Officer Change": "sedar_director_resign",
        "CT ORDER": "edgar_conf_treatment",
        "SC 13D": "edgar_sc13d",
        "DEFM14A": "edgar_merger_confirmed",
        "S-4": "edgar_merger_confirmed",
        "8-K": "edgar_8k",
        "litigation_defendant": "canlii_defendant",
        "litigation_plaintiff": "canlii_plaintiff",
        "enforcement_action": "osc_enforcement",
        "job_gc_hire": "job_gc_hire",
        "job_cco_urgent": "job_cco_urgent",
        "job_privacy_counsel": "job_privacy_counsel",
        "job_ma_counsel": "job_ma_counsel",
        "job_litigation_counsel": "job_litigation_counsel",
    }
    result = mapping.get(trigger_type)
    if not result:
        # Fuzzy match on first word
        for k, v in mapping.items():
            if trigger_type.lower().startswith(k.lower()[:8]):
                return v
        return "news_lawsuit"  # safe default
    return result
