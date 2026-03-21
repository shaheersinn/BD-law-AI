"""app/models — expose all ORM models for Alembic and import convenience."""

from app.models.client import BillingRecord, ChurnSignal, Client, Matter, RiskLevel
from app.models.signal import (
    Alert,
    AlertThreshold,
    CompetitorThreat,
    FootTrafficEvent,
    JetTrack,
    PermitFiling,
    Prospect,
    RegulatoryAlert,
    SatelliteSignal,
    Trigger,
    TriggerSource,
)
from app.models.bd_activity import (
    Alumni,
    BDActivity,
    ClientInquiry,
    ContentPiece,
    MatterSource,
    Partner,
    ReferralContact,
    WritingSample,
)

__all__ = [
    "Client", "Matter", "BillingRecord", "ChurnSignal", "RiskLevel",
    "Prospect", "Trigger", "TriggerSource", "Alert", "AlertThreshold",
    "JetTrack", "FootTrafficEvent", "SatelliteSignal", "PermitFiling",
    "RegulatoryAlert", "CompetitorThreat",
    "Partner", "BDActivity", "MatterSource", "ReferralContact",
    "ContentPiece", "WritingSample", "ClientInquiry", "Alumni",
]

from app.auth.models import User, UserRole
