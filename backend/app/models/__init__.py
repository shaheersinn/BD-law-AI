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
from app.models.class_action_score import ClassActionScore
from app.models.client import BillingRecord, ChurnSignal, Client, Matter, Prospect, RiskLevel
from app.models.company import Company
from app.models.features import CompanyFeature
from app.models.geo import FootTrafficEvent, JetTrack, PermitFiling, SatelliteSignal
from app.models.ground_truth import GroundTruthLabel, LabelingRun
from app.models.law_firm import LawFirm
from app.models.signal import SignalRecord
from app.models.training import TrainingDataset
from app.models.trigger import Alert, Trigger

# Note: ScraperHealth is NOT re-exported here to avoid duplicate table registration.
# Import it directly via `from app.models.scraper_health import ScraperHealth`.

__all__ = [
    "Alert",
    "Alumni",
    "BDActivity",
    "BillingRecord",
    "ChurnSignal",
    "ClassActionScore",
    "Client",
    "ClientInquiry",
    "Company",
    "CompanyFeature",
    "ContentPiece",
    "FootTrafficEvent",
    "GroundTruthLabel",
    "JetTrack",
    "LabelingRun",
    "LawFirm",
    "Matter",
    "MatterSource",
    "Partner",
    "PermitFiling",
    "Prospect",
    "ReferralContact",
    "RiskLevel",
    "SatelliteSignal",
    "SignalRecord",
    "TrainingDataset",
    "Trigger",
    "WritingSample",
]
