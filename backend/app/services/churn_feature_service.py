"""
app/services/churn_feature_service.py — Extracts ML features from client DB records.
app/services/notification_service.py — Delivers alerts via Slack + email.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Churn feature extraction
# ─────────────────────────────────────────────────────────────────────────────

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.churn_model import ClientFeatures
from app.models.client import BillingRecord, Client

log = logging.getLogger(__name__)


async def extract_client_features(session: AsyncSession, client: Client) -> ClientFeatures:
    """Build a ClientFeatures dataclass from current DB records for one client."""
    now = datetime.now(UTC)
    year_ago = now - timedelta(days=365)
    two_years_ago = now - timedelta(days=730)

    # Current year billing
    cy_result = await session.execute(
        select(
            func.sum(BillingRecord.amount_billed).label("billed"),
            func.sum(BillingRecord.write_off_amount).label("writeoffs"),
            func.count(BillingRecord.id).filter(BillingRecord.has_dispute).label("disputes"),
        ).where(
            BillingRecord.client_id == client.id,
            BillingRecord.bill_date >= year_ago.date(),
        )
    )
    cy = cy_result.one()
    total_billed = float(cy.billed or 0)
    write_off_total = float(cy.writeoffs or 0)
    disputes = int(cy.disputes or 0)

    # Prior year billing for YoY calculation
    py_result = await session.execute(
        select(func.sum(BillingRecord.amount_billed)).where(
            BillingRecord.client_id == client.id,
            BillingRecord.bill_date >= two_years_ago.date(),
            BillingRecord.bill_date < year_ago.date(),
        )
    )
    prior_year_billed = float(py_result.scalar() or 0)
    yoy_change = (
        ((total_billed - prior_year_billed) / prior_year_billed * 100)
        if prior_year_billed > 0
        else 0.0
    )

    # Matter stats
    from app.models.client import Matter

    matters_result = await session.execute(
        select(Matter).where(
            Matter.client_id == client.id,
            Matter.opened_at >= year_ago.date(),
        )
    )
    matters = matters_result.scalars().all()
    matters_opened = len(matters)
    closed_matters = sum(1 for m in matters if not m.is_open)
    completion_rate = closed_matters / matters_opened if matters_opened > 0 else 1.0

    # Days since last matter
    last_matter_result = await session.execute(
        select(func.max(Matter.opened_at)).where(Matter.client_id == client.id)
    )
    last_matter_date = last_matter_result.scalar()
    days_since_matter = (now.date() - last_matter_date).days if last_matter_date else 365

    # Write-off percentage
    writeoff_pct = write_off_total / total_billed if total_billed > 0 else 0.0

    return ClientFeatures(
        total_billed_this_year=total_billed,
        yoy_billing_change_pct=yoy_change,
        matters_opened_this_year=matters_opened,
        days_since_last_matter=days_since_matter,
        disputes_this_year=disputes,
        writeoff_pct=writeoff_pct,
        gc_changed_this_year=0,  # TODO: wire from CRM/LinkedIn
        days_since_last_contact=client.days_since_last_contact,
        practice_area_count=len(client.practice_groups or []),
        matter_completion_rate=completion_rate,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Notification service
# ─────────────────────────────────────────────────────────────────────────────

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402

settings = get_settings()

# Practice area → partner routing (update with real partner data)
PRACTICE_ROUTING: dict[str, list[str]] = {
    "Corporate / M&A": ["S. Chen", "M. Webb"],
    "Litigation": ["P. Rodrigues", "D. Park"],
    "Securities": ["S. Chen", "J. Okafor"],
    "Regulatory": ["M. Webb", "J. Okafor"],
    "Restructuring / Insolvency": ["D. Park", "P. Rodrigues"],
    "Employment & Labour": ["M. Webb"],
    "Privacy & Cybersecurity": ["D. Park"],
    "Environmental": ["J. Okafor"],
    "Banking & Finance": ["S. Chen", "J. Okafor"],
    "Competition": ["M. Webb"],
    "Real Estate & Construction": ["P. Rodrigues"],
    "Corporate / Governance": ["S. Chen"],
    "IP": ["D. Park"],
}


class NotificationService:
    async def send_alert(self, alert, client=None) -> None:
        partners = PRACTICE_ROUTING.get(alert.practice_area or "", [])[:2]
        if not partners:
            partners = ["Managing Partner"]

        message = self._format_slack_message(alert, partners)

        if alert.threshold in ("CRITICAL", "HIGH"):
            await self._send_slack(message)

        # Nightly digest handles MODERATE/WATCH — no immediate push

    def _format_slack_message(self, alert, partners: list[str]) -> str:
        emoji = {"CRITICAL": "🚨", "HIGH": "🔴", "MODERATE": "🟡", "WATCH": "⚪"}.get(
            str(alert.threshold), "📊"
        )
        return (
            f"{emoji} *{alert.threshold} Alert* — {alert.company_name}\n"
            f"Score: *{alert.score:.0f}/100* | Practice: {alert.practice_area}\n"
            f"Top signals: {', '.join(alert.top_signals or [])[:120]}\n"
            f"Routed to: {', '.join(partners)}\n"
            f"_Open ORACLE dashboard to generate tactical brief →_"
        )

    async def _send_slack(self, text: str) -> None:
        if not settings.slack_webhook_url:
            log.debug("Slack webhook not configured — skipping")
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(settings.slack_webhook_url, json={"text": text})
        except Exception as e:
            log.warning("Slack send error: %s", e)
