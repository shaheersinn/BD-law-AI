"""
app/ground_truth/constants.py — Signal type to practice area mappings for Phase 3.

These mappings drive the Retrospective Labeler (Agent 016):
given a signal_type from signal_records, which practice area(s) does it indicate?

Signal types that appear in the POSITIVE set are used to identify companies
that likely hired legal counsel. The Negative Sampler (Agent 017) looks for
companies whose signal history contains ZERO positive signal types.
"""

from __future__ import annotations

# All 34 ORACLE practice areas (canonical names)
PRACTICE_AREAS: list[str] = [
    "M&A/Corporate",
    "Litigation/Dispute Resolution",
    "Regulatory/Compliance",
    "Employment/Labour",
    "Insolvency/Restructuring",
    "Securities/Capital Markets",
    "Competition/Antitrust",
    "Privacy/Cybersecurity",
    "Environmental/Indigenous/Energy",
    "Tax",
    "Real Estate/Construction",
    "Banking/Finance",
    "Intellectual Property",
    "Immigration (Corporate)",
    "Infrastructure/Project Finance",
    "Wills/Estates",
    "Administrative/Public Law",
    "Arbitration/International Dispute",
    "Class Actions",
    "Construction/Infrastructure Disputes",
    "Defamation/Media Law",
    "Financial Regulatory (OSFI/FINTRAC)",
    "Franchise/Distribution",
    "Health Law/Life Sciences",
    "Insurance/Reinsurance",
    "International Trade/Customs",
    "Mining/Natural Resources",
    "Municipal/Land Use",
    "Not-for-Profit/Charity Law",
    "Pension/Benefits",
    "Product Liability",
    "Sports/Entertainment",
    "Technology/Fintech Regulatory",
    "Data Privacy & Technology",
]

# Signal type → practice area(s)
# Key: signal_type value stored in signal_records.signal_type
# Value: list of practice areas this signal type indicates
SIGNAL_TYPE_TO_PRACTICE_AREAS: dict[str, list[str]] = {
    # ── Insolvency ──────────────────────────────────────────────────────────────
    "insolvency_filing": ["Insolvency/Restructuring"],
    "ccaa_filing": ["Insolvency/Restructuring"],
    "bia_proposal": ["Insolvency/Restructuring"],
    "receivership": ["Insolvency/Restructuring", "Banking/Finance"],
    "osb_insolvency": ["Insolvency/Restructuring"],
    # ── Securities / Capital Markets ────────────────────────────────────────────
    "enforcement_action_securities": ["Securities/Capital Markets", "Regulatory/Compliance"],
    "material_change_report": ["Securities/Capital Markets", "M&A/Corporate"],
    "securities_filing": ["Securities/Capital Markets"],
    "sedar_filing": ["Securities/Capital Markets"],
    "sedi_insider_trade": ["Securities/Capital Markets"],
    "cease_trade_order": ["Securities/Capital Markets", "Regulatory/Compliance"],
    "going_private": ["Securities/Capital Markets", "M&A/Corporate"],
    "prospectus": ["Securities/Capital Markets", "Banking/Finance"],
    # ── M&A / Corporate ─────────────────────────────────────────────────────────
    "ma_announcement": ["M&A/Corporate"],
    "acquisition_target": ["M&A/Corporate"],
    "merger_filing": ["M&A/Corporate", "Competition/Antitrust"],
    "divestiture": ["M&A/Corporate"],
    "hostile_takeover": ["M&A/Corporate", "Securities/Capital Markets"],
    "privatization": ["M&A/Corporate"],
    "corporate_restructuring": ["M&A/Corporate", "Insolvency/Restructuring"],
    # ── Competition / Antitrust ──────────────────────────────────────────────────
    "enforcement_action_competition": ["Competition/Antitrust"],
    "competition_tribunal_filing": ["Competition/Antitrust"],
    "merger_review": ["Competition/Antitrust", "M&A/Corporate"],
    "cartel_investigation": ["Competition/Antitrust"],
    # ── Regulatory / Compliance ──────────────────────────────────────────────────
    "regulatory_sanction": ["Regulatory/Compliance"],
    "enforcement_action": ["Regulatory/Compliance"],
    "consent_order": ["Regulatory/Compliance"],
    "warning_letter": ["Regulatory/Compliance"],
    "osfi_action": ["Financial Regulatory (OSFI/FINTRAC)", "Regulatory/Compliance"],
    "fintrac_penalty": ["Financial Regulatory (OSFI/FINTRAC)", "Regulatory/Compliance"],
    "crtc_decision": ["Regulatory/Compliance"],
    # ── Privacy / Cybersecurity ──────────────────────────────────────────────────
    "enforcement_action_privacy": ["Privacy/Cybersecurity", "Data Privacy & Technology"],
    "data_breach": ["Privacy/Cybersecurity", "Data Privacy & Technology"],
    "privacy_complaint": ["Privacy/Cybersecurity"],
    "opc_finding": ["Privacy/Cybersecurity", "Data Privacy & Technology"],
    "hibp_breach": ["Privacy/Cybersecurity", "Data Privacy & Technology"],
    # ── Employment / Labour ──────────────────────────────────────────────────────
    "court_filing_employment": ["Employment/Labour"],
    "mass_layoff": ["Employment/Labour"],
    "labour_board_complaint": ["Employment/Labour"],
    "wsib_claim": ["Employment/Labour"],
    "constructive_dismissal": ["Employment/Labour"],
    "executive_departure": ["Employment/Labour", "M&A/Corporate"],
    # ── Environmental ────────────────────────────────────────────────────────────
    "environmental_order": ["Environmental/Indigenous/Energy"],
    "eccc_enforcement": ["Environmental/Indigenous/Energy", "Regulatory/Compliance"],
    "indigenous_land_claim": ["Environmental/Indigenous/Energy"],
    "environmental_assessment": ["Environmental/Indigenous/Energy"],
    # ── Litigation ───────────────────────────────────────────────────────────────
    "court_filing": ["Litigation/Dispute Resolution"],
    "lawsuit": ["Litigation/Dispute Resolution"],
    "judgment": ["Litigation/Dispute Resolution"],
    "court_filing_class_action": ["Class Actions", "Litigation/Dispute Resolution"],
    "class_action_certification": ["Class Actions"],
    "arbitration_notice": ["Arbitration/International Dispute"],
    # ── Tax ─────────────────────────────────────────────────────────────────────
    "tax_lien": ["Tax"],
    "cra_audit": ["Tax"],
    "tax_court_filing": ["Tax"],
    "transfer_pricing_dispute": ["Tax", "International Trade/Customs"],
    # ── Immigration ─────────────────────────────────────────────────────────────
    "immigration_enforcement": ["Immigration (Corporate)"],
    "work_permit_issue": ["Immigration (Corporate)"],
    # ── IP ───────────────────────────────────────────────────────────────────────
    "court_filing_ip": ["Intellectual Property"],
    "patent_opposition": ["Intellectual Property"],
    "trademark_dispute": ["Intellectual Property"],
    "cipo_filing": ["Intellectual Property"],
    # ── Real Estate ──────────────────────────────────────────────────────────────
    "real_estate_dispute": ["Real Estate/Construction"],
    "construction_lien": ["Real Estate/Construction", "Construction/Infrastructure Disputes"],
    "municipal_permit_denial": ["Municipal/Land Use", "Real Estate/Construction"],
    # ── Financial / Banking ──────────────────────────────────────────────────────
    "loan_default": ["Banking/Finance", "Insolvency/Restructuring"],
    "credit_rating_downgrade": ["Banking/Finance"],
    "covenant_breach": ["Banking/Finance"],
    # ── Health / Life Sciences ────────────────────────────────────────────────────
    "health_canada_recall": ["Health Law/Life Sciences", "Product Liability"],
    "health_canada_enforcement": ["Health Law/Life Sciences", "Regulatory/Compliance"],
    "product_liability_claim": ["Product Liability"],
    # ── Trade ────────────────────────────────────────────────────────────────────
    "trade_remedy_filing": ["International Trade/Customs"],
    "cbsa_customs_action": ["International Trade/Customs"],
    "sanctions_designation": ["International Trade/Customs", "Regulatory/Compliance"],
    # ── Technology / Fintech ─────────────────────────────────────────────────────
    "fintech_enforcement": ["Technology/Fintech Regulatory"],
    "crypto_enforcement": ["Technology/Fintech Regulatory", "Securities/Capital Markets"],
    # ── Mining / Natural Resources ────────────────────────────────────────────────
    "mining_dispute": ["Mining/Natural Resources"],
    "resource_permit_denial": ["Mining/Natural Resources", "Environmental/Indigenous/Energy"],
    # ── Pension / Benefits ────────────────────────────────────────────────────────
    "pension_deficiency": ["Pension/Benefits"],
    "benefits_dispute": ["Pension/Benefits", "Employment/Labour"],
    # ── Insurance ────────────────────────────────────────────────────────────────
    "insurance_dispute": ["Insurance/Reinsurance"],
    "coverage_denial": ["Insurance/Reinsurance"],
    # ── Procurement ─────────────────────────────────────────────────────────────
    "procurement_dispute": ["Administrative/Public Law"],
    "government_contract_dispute": ["Administrative/Public Law"],
    # ── Defamation / Media ────────────────────────────────────────────────────────
    "defamation_claim": ["Defamation/Media Law"],
}

# Flat set of all signal types that indicate likely legal engagement (positive label)
POSITIVE_SIGNAL_TYPES: frozenset[str] = frozenset(SIGNAL_TYPE_TO_PRACTICE_AREAS.keys())

# Signal types that are clearly NOT indicative of legal engagement
# (routine signals — used to identify pure negative examples)
NEGATIVE_SIGNAL_TYPES: frozenset[str] = frozenset(
    [
        "news_article",
        "job_posting",
        "earnings_release",
        "analyst_report",
        "press_release",
        "social_mention",
        "google_trends_spike",
        "jet_proximity",
        "stock_price_change",
        "volume_spike",
        "market_cap_change",
        "law_blog_mention",
    ]
)

# Time horizons (days) — match Phase 6 ML model horizons
HORIZONS: list[int] = [30, 60, 90]

# Default confidence for retrospective labels (no manual validation yet)
DEFAULT_LABEL_CONFIDENCE: float = 0.75

# Minimum number of positive signals in a window to assign a positive label
MIN_POSITIVE_SIGNALS_FOR_LABEL: int = 1

# Maximum negative examples per sector (prevents sampling bias)
MAX_NEGATIVE_SAMPLES_PER_SECTOR: int = 50
