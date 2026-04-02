"""
app/ml/convergence/engine.py — Bayesian signal convergence scoring.

This is the core scoring engine. Each signal has a base weight (probability
that it precedes a legal mandate within 90 days). Convergence score is:

    P(mandate) = 1 - ∏(1 - w_i * decay_i)

Multiple signals from different categories get a convergence multiplier.
"""

import math
from dataclasses import dataclass, field

# ── Signal catalogue ───────────────────────────────────────────────────────────
# Base weights from: historical mandate rate when this signal alone fires.
# These are calibrated priors — update from your data after 6 months.

SIGNAL_WEIGHTS: dict[str, float] = {
    # Corporate filings
    "sedar_material_change": 0.88,
    "sedar_business_acquisition": 0.92,
    "sedar_confidentiality": 0.91,
    "sedar_cease_trade": 0.87,
    "sedar_going_concern": 0.84,
    "sedar_auditor_change": 0.79,
    "sedar_director_resign": 0.76,
    "edgar_conf_treatment": 0.89,
    "edgar_sc13d": 0.85,
    "edgar_merger_confirmed": 0.96,
    "edgar_8k": 0.75,
    # Court / litigation
    "canlii_defendant": 0.88,
    "canlii_plaintiff": 0.72,
    "canlii_class_action": 0.91,
    "canlii_ccaa": 0.94,
    "canlii_injunction": 0.86,
    "canlii_tribunal": 0.83,
    # Regulatory enforcement
    "osc_enforcement": 0.90,
    "osfi_supervisory": 0.88,
    "competition_investigation": 0.91,
    "fintrac_noncompliance": 0.87,
    "health_canada_recall": 0.82,
    "eccc_enforcement": 0.89,
    "competitor_hit_same_industry": 0.71,
    # Job postings
    "job_gc_hire": 0.78,
    "job_cco_urgent": 0.85,
    "job_privacy_counsel": 0.82,
    "job_ma_counsel": 0.80,
    "job_litigation_counsel": 0.83,
    "job_deputy_gc_regulatory": 0.77,
    "job_environmental_counsel": 0.79,
    # Physical / geospatial
    "jet_baystreet_2x": 0.88,
    "satellite_parking_drop": 0.82,
    "permit_environmental": 0.83,
    "permit_construction": 0.76,
    "foot_traffic_competitor": 0.79,
    # News NLP
    "news_lawsuit": 0.75,
    "news_investigation": 0.81,
    "news_layoffs": 0.78,
    "news_data_breach": 0.87,
    "news_merger": 0.82,
    "news_exploring_strategic": 0.86,
    "news_legal_proceedings": 0.74,
    # LinkedIn / people
    "linkedin_gc_spike": 0.77,
    "linkedin_gc_posts_legal": 0.72,
    "linkedin_exec_departure": 0.74,
    "linkedin_mass_exits": 0.80,
    "linkedin_gc_connected_restr": 0.76,
    # Corporate / filings (scraper naming alignment)
    "filing_material_change": 0.88,
    "business_acquisition_report": 0.92,
    "annual_report": 0.45,
    "corporate_filing": 0.50,
    "corporate_status_change": 0.72,
    "company_dissolution": 0.76,
    "late_filing": 0.71,
    "proxy_circular": 0.65,
    "insider_transaction": 0.68,
    "insider_trade_sell": 0.70,
    "insider_trade_cluster": 0.79,
    "market_signal": 0.55,
    "market_trading_halt": 0.81,
    # Regulatory / enforcement
    "enforcement_action": 0.88,
    "regulatory_enforcement": 0.87,
    "regulatory_osfi_action": 0.88,
    "regulatory_fintrac_penalty": 0.87,
    "regulatory_fsra_action": 0.82,
    "regulatory_crtc_decision": 0.79,
    "regulatory_doj_action": 0.85,
    "regulatory_sec_aaer": 0.83,
    "regulatory_environmental_enforcement": 0.89,
    "regulatory_environmental_assessment": 0.78,
    "regulatory_federal": 0.70,
    "regulatory_cccs_advisory": 0.75,
    "regulated_entity": 0.60,
    "regulation_published": 0.55,
    "impact_assessment": 0.78,
    "monetary_policy_rate_change": 0.50,
    # Legal / courts
    "litigation_class_action": 0.91,
    "litigation_competition": 0.88,
    "litigation_immigration": 0.72,
    "litigation_judgment": 0.80,
    "litigation_scc_decision": 0.85,
    "litigation_tribunal_decision": 0.83,
    "insolvency_statistic": 0.76,
    # Jobs
    "job_posting": 0.68,
    # Consumer / recalls
    "recall_health_canada": 0.82,
    "recall_transport_canada": 0.74,
    "recall_cpsc_us": 0.70,
    "consumer_complaint_spike": 0.75,
    "consumer_complaint_financial": 0.76,
    "consumer_complaint_telecom": 0.70,
    "privacy_breach_report": 0.87,
    "privacy_enforcement": 0.86,
    "privacy_provincial_finding": 0.81,
    "regulatory_health_recall": 0.82,
    "regulatory_health_enforcement": 0.86,
    # Geo / physical
    "geo_flight_corporate_jet": 0.88,
    "geo_permit_issued": 0.76,
    "geo_permit_major_construction": 0.78,
    "geo_permit_demolition": 0.65,
    "geo_credit_downgrade": 0.86,
    "geo_credit_outlook_negative": 0.79,
    "geo_data_breach": 0.87,
    "geo_labour_decision": 0.74,
    "geo_union_certification": 0.73,
    "geo_trade_remedy": 0.78,
    "geo_procurement_contract_award": 0.68,
    "geo_property_tax_arrears": 0.77,
    "geo_darkweb_mention": 0.80,
    "geo_cipo_patent_grant": 0.65,
    "geo_cfcj_access_to_justice": 0.50,
    # News / social
    "news_mention": 0.50,
    "macro_indicator": 0.48,
    "social_breach_detected": 0.85,
    "social_linkedin_exec_departure": 0.74,
    "social_linkedin_legal_hire": 0.77,
    # Law blogs
    "blog_legal_trend": 0.45,
    "blog_practice_alert": 0.55,
    # Class actions
    "class_action_filed": 0.91,
    "class_action_filed_federal": 0.89,
    "class_action_investigation": 0.85,
    "class_action_analysis": 0.60,
    # ── Phase S-NEW: 28 new signal types ─────────────────────────────────────
    # HNWI & Estate (Phase 1)
    "trust_deemed_disposition_approaching": 0.91,
    "estate_art_liquidation": 0.74,
    "probate_filing_high_value": 0.82,
    "hnwi_foundation_director_change": 0.72,
    "vessel_registry_change": 0.68,
    # Immigration (Phase 2)
    "immigration_lmia_spike": 0.76,
    "immigration_express_entry_draw": 0.52,
    # PE / VC (Phase 2)
    "pe_fund_exit_pressure": 0.83,
    "vc_series_b_plus": 0.77,
    # Financial Stress (Phase 3)
    "ppsa_layered_lending": 0.87,
    "credit_rating_downgrade_sp": 0.86,
    # Legal (Phase 3)
    "tax_court_dispute": 0.81,
    # Restructuring (Phase 3)
    "ccaa_monitor_report": 0.95,
    # Grants (Phase 3)
    "federal_grant_awarded": 0.73,
    # Courts (Phase 4)
    "ontario_commercial_list_filing": 0.90,
    "bc_supreme_court_filing": 0.88,
    "quebec_superior_court_filing": 0.88,
    # Energy (Phase 4)
    "cer_pipeline_incident": 0.84,
    # Macro (Phase 4)
    "cmhc_housing_starts_decline": 0.68,
    # IP (Phase 4)
    "trademark_new_class_expansion": 0.74,
    # Ownership (Phase 5)
    "beneficial_owner_change": 0.78,
    # PE — Pension (Phase 5)
    "pension_fund_investment": 0.85,
    # Startups (Phase 5)
    "accelerator_cohort_member": 0.65,
    # Financial Stress — Private Credit (Phase 5)
    "private_credit_deterioration": 0.88,
    # Environmental (Phase 6)
    "npri_pollution_spike": 0.77,
    # Labour (Phase 6)
    "labour_code_payment_order": 0.79,
    "worksafebc_penalty": 0.76,
    # Macro — BOS/SLOS (Phase 6 enhancement)
    "macro_bos_credit_tightening": 0.72,
}

# Signals grouped into categories for convergence multiplier
SIGNAL_CATEGORIES: dict[str, str] = {
    **dict.fromkeys(
        [
            "sedar_material_change",
            "sedar_business_acquisition",
            "sedar_confidentiality",
            "sedar_cease_trade",
            "sedar_going_concern",
            "sedar_auditor_change",
            "sedar_director_resign",
            "edgar_conf_treatment",
            "edgar_sc13d",
            "edgar_merger_confirmed",
            "edgar_8k",
        ],
        "filings",
    ),
    **dict.fromkeys(
        [
            "canlii_defendant",
            "canlii_plaintiff",
            "canlii_class_action",
            "canlii_ccaa",
            "canlii_injunction",
            "canlii_tribunal",
        ],
        "litigation",
    ),
    **dict.fromkeys(
        [
            "osc_enforcement",
            "osfi_supervisory",
            "competition_investigation",
            "fintrac_noncompliance",
            "health_canada_recall",
            "eccc_enforcement",
            "competitor_hit_same_industry",
        ],
        "enforcement",
    ),
    **dict.fromkeys(
        [
            "job_gc_hire",
            "job_cco_urgent",
            "job_privacy_counsel",
            "job_ma_counsel",
            "job_litigation_counsel",
            "job_deputy_gc_regulatory",
            "job_environmental_counsel",
        ],
        "jobs",
    ),
    **dict.fromkeys(
        [
            "jet_baystreet_2x",
            "satellite_parking_drop",
            "permit_environmental",
            "permit_construction",
            "foot_traffic_competitor",
        ],
        "geospatial",
    ),
    **dict.fromkeys(
        [
            "news_lawsuit",
            "news_investigation",
            "news_layoffs",
            "news_data_breach",
            "news_merger",
            "news_exploring_strategic",
            "news_legal_proceedings",
        ],
        "news",
    ),
    **dict.fromkeys(
        [
            "linkedin_gc_spike",
            "linkedin_gc_posts_legal",
            "linkedin_exec_departure",
            "linkedin_mass_exits",
            "linkedin_gc_connected_restr",
        ],
        "people",
    ),
    **dict.fromkeys(
        [
            "filing_material_change",
            "business_acquisition_report",
            "annual_report",
            "corporate_filing",
            "corporate_status_change",
            "company_dissolution",
            "late_filing",
            "proxy_circular",
            "insider_transaction",
            "insider_trade_sell",
            "insider_trade_cluster",
            "market_signal",
            "market_trading_halt",
        ],
        "filings",
    ),
    **dict.fromkeys(
        [
            "enforcement_action",
            "regulatory_enforcement",
            "regulatory_osfi_action",
            "regulatory_fintrac_penalty",
            "regulatory_fsra_action",
            "regulatory_crtc_decision",
            "regulatory_doj_action",
            "regulatory_sec_aaer",
            "regulatory_environmental_enforcement",
            "regulatory_environmental_assessment",
            "regulatory_federal",
            "regulatory_cccs_advisory",
            "regulated_entity",
            "regulation_published",
            "impact_assessment",
            "monetary_policy_rate_change",
            "recall_health_canada",
            "recall_transport_canada",
            "recall_cpsc_us",
            "consumer_complaint_spike",
            "consumer_complaint_financial",
            "consumer_complaint_telecom",
            "privacy_breach_report",
            "privacy_enforcement",
            "privacy_provincial_finding",
            "regulatory_health_recall",
            "regulatory_health_enforcement",
        ],
        "enforcement",
    ),
    **dict.fromkeys(
        [
            "litigation_class_action",
            "litigation_competition",
            "litigation_immigration",
            "litigation_judgment",
            "litigation_scc_decision",
            "litigation_tribunal_decision",
            "insolvency_statistic",
            "class_action_filed",
            "class_action_filed_federal",
            "class_action_investigation",
            "class_action_analysis",
        ],
        "litigation",
    ),
    **dict.fromkeys(["job_posting"], "jobs"),
    **dict.fromkeys(
        [
            "geo_flight_corporate_jet",
            "geo_permit_issued",
            "geo_permit_major_construction",
            "geo_permit_demolition",
            "geo_credit_downgrade",
            "geo_credit_outlook_negative",
            "geo_data_breach",
            "geo_labour_decision",
            "geo_union_certification",
            "geo_trade_remedy",
            "geo_procurement_contract_award",
            "geo_property_tax_arrears",
            "geo_darkweb_mention",
            "geo_cipo_patent_grant",
            "geo_cfcj_access_to_justice",
        ],
        "geospatial",
    ),
    **dict.fromkeys(
        [
            "news_mention",
            "macro_indicator",
            "social_breach_detected",
            "social_linkedin_exec_departure",
            "social_linkedin_legal_hire",
            "blog_legal_trend",
            "blog_practice_alert",
        ],
        "news",
    ),
    # ── Phase S-NEW: 28 new signal categories ────────────────────────────────
    # HNWI (new category)
    **dict.fromkeys(
        [
            "trust_deemed_disposition_approaching",
            "estate_art_liquidation",
            "probate_filing_high_value",
            "hnwi_foundation_director_change",
            "vessel_registry_change",
        ],
        "hnwi",
    ),
    # Immigration (new category — maps to filings)
    **dict.fromkeys(
        ["immigration_lmia_spike", "immigration_express_entry_draw"],
        "filings",
    ),
    # PE / VC
    **dict.fromkeys(
        ["pe_fund_exit_pressure", "vc_series_b_plus", "pension_fund_investment"],
        "filings",
    ),
    # Financial Stress
    **dict.fromkeys(
        ["ppsa_layered_lending", "credit_rating_downgrade_sp", "private_credit_deterioration"],
        "filings",
    ),
    # Legal / Courts / Restructuring
    **dict.fromkeys(
        [
            "tax_court_dispute",
            "ontario_commercial_list_filing",
            "bc_supreme_court_filing",
            "quebec_superior_court_filing",
            "ccaa_monitor_report",
        ],
        "litigation",
    ),
    # Grants
    **dict.fromkeys(["federal_grant_awarded", "beneficial_owner_change"], "filings"),
    # Energy / Environmental / Labour → enforcement
    **dict.fromkeys(
        [
            "cer_pipeline_incident",
            "npri_pollution_spike",
            "labour_code_payment_order",
            "worksafebc_penalty",
        ],
        "enforcement",
    ),
    # Macro / Geospatial
    **dict.fromkeys(
        ["cmhc_housing_starts_decline", "macro_bos_credit_tightening"],
        "geospatial",
    ),
    # IP / Startups → filings
    **dict.fromkeys(
        ["trademark_new_class_expansion", "accelerator_cohort_member"],
        "filings",
    ),
}

# Practice area voting weights for each signal
PRACTICE_AREA_VOTES: dict[str, dict[str, float]] = {
    "sedar_material_change": {"Corporate / M&A": 1.0},
    "sedar_business_acquisition": {"Corporate / M&A": 1.0},
    "sedar_confidentiality": {"Corporate / M&A": 1.0},
    "sedar_cease_trade": {"Securities": 1.0},
    "sedar_going_concern": {"Restructuring / Insolvency": 1.0},
    "sedar_auditor_change": {"Corporate / Governance": 0.6, "Fraud": 0.4},
    "sedar_director_resign": {"Corporate / Governance": 1.0},
    "edgar_conf_treatment": {"Corporate / M&A": 1.0},
    "edgar_sc13d": {"Corporate / M&A": 0.8, "Securities": 0.2},
    "edgar_merger_confirmed": {"Corporate / M&A": 1.0},
    "edgar_8k": {"Corporate / M&A": 0.5, "Securities": 0.5},
    "canlii_defendant": {"Litigation": 1.0},
    "canlii_plaintiff": {"Litigation": 1.0},
    "canlii_class_action": {"Litigation": 1.0},
    "canlii_ccaa": {"Restructuring / Insolvency": 1.0},
    "canlii_injunction": {"Litigation": 0.7, "IP": 0.3},
    "canlii_tribunal": {"Regulatory": 1.0},
    "osc_enforcement": {"Securities": 1.0},
    "osfi_supervisory": {"Banking & Finance": 1.0},
    "competition_investigation": {"Competition": 1.0},
    "fintrac_noncompliance": {"Banking & Finance": 0.7, "Regulatory": 0.3},
    "health_canada_recall": {"Regulatory": 0.7, "Litigation": 0.3},
    "eccc_enforcement": {"Environmental": 1.0},
    "competitor_hit_same_industry": {"Regulatory": 1.0},
    "job_gc_hire": {},  # no practice vote
    "job_cco_urgent": {"Regulatory": 0.6, "Banking & Finance": 0.4},
    "job_privacy_counsel": {"Privacy & Cybersecurity": 1.0},
    "job_ma_counsel": {"Corporate / M&A": 1.0},
    "job_litigation_counsel": {"Litigation": 1.0},
    "job_deputy_gc_regulatory": {"Regulatory": 1.0},
    "job_environmental_counsel": {"Environmental": 1.0},
    "jet_baystreet_2x": {"Corporate / M&A": 1.0},
    "satellite_parking_drop": {"Restructuring / Insolvency": 0.6, "Employment & Labour": 0.4},
    "permit_environmental": {"Environmental": 1.0},
    "permit_construction": {"Real Estate & Construction": 1.0},
    "foot_traffic_competitor": {},
    "news_lawsuit": {"Litigation": 1.0},
    "news_investigation": {"Regulatory": 1.0},
    "news_layoffs": {"Employment & Labour": 0.6, "Restructuring / Insolvency": 0.4},
    "news_data_breach": {"Privacy & Cybersecurity": 1.0},
    "news_merger": {"Corporate / M&A": 1.0},
    "news_exploring_strategic": {"Corporate / M&A": 1.0},
    "news_legal_proceedings": {"Litigation": 1.0},
    "linkedin_gc_spike": {},
    "linkedin_gc_posts_legal": {},
    "linkedin_exec_departure": {"Corporate / Governance": 1.0},
    "linkedin_mass_exits": {"Employment & Labour": 0.7, "Restructuring / Insolvency": 0.3},
    "linkedin_gc_connected_restr": {"Restructuring / Insolvency": 1.0},
    # Scraper-aligned catalogue (votes mirror nearest canonical signal)
    "filing_material_change": {"Corporate / M&A": 1.0},
    "business_acquisition_report": {"Corporate / M&A": 1.0},
    "annual_report": {"Corporate / Governance": 0.7, "Securities": 0.3},
    "corporate_filing": {"Corporate / M&A": 0.5, "Securities": 0.5},
    "corporate_status_change": {"Corporate / M&A": 0.6, "Restructuring / Insolvency": 0.4},
    "company_dissolution": {"Restructuring / Insolvency": 0.7, "Corporate / M&A": 0.3},
    "late_filing": {"Securities": 1.0},
    "proxy_circular": {"Corporate / M&A": 0.6, "Securities": 0.4},
    "insider_transaction": {"Securities": 1.0},
    "insider_trade_sell": {"Securities": 1.0},
    "insider_trade_cluster": {"Securities": 1.0},
    "market_signal": {"Securities": 0.6, "Corporate / M&A": 0.4},
    "market_trading_halt": {"Securities": 1.0},
    "enforcement_action": {"Regulatory": 0.5, "Litigation": 0.5},
    "regulatory_enforcement": {"Regulatory": 1.0},
    "regulatory_osfi_action": {"Banking & Finance": 1.0},
    "regulatory_fintrac_penalty": {"Banking & Finance": 0.7, "Regulatory": 0.3},
    "regulatory_fsra_action": {"Regulatory": 1.0},
    "regulatory_crtc_decision": {"Regulatory": 0.7, "Technology": 0.3},
    "regulatory_doj_action": {"Litigation": 0.6, "Regulatory": 0.4},
    "regulatory_sec_aaer": {"Securities": 1.0},
    "regulatory_environmental_enforcement": {"Environmental": 1.0},
    "regulatory_environmental_assessment": {"Environmental": 1.0},
    "regulatory_federal": {"Regulatory": 1.0},
    "regulatory_cccs_advisory": {"Competition": 1.0},
    "regulated_entity": {"Regulatory": 1.0},
    "regulation_published": {"Regulatory": 1.0},
    "impact_assessment": {"Environmental": 0.5, "Regulatory": 0.5},
    "monetary_policy_rate_change": {"Banking & Finance": 0.7, "Corporate / M&A": 0.3},
    "litigation_class_action": {"Litigation": 1.0},
    "litigation_competition": {"Competition": 0.5, "Litigation": 0.5},
    "litigation_immigration": {"Corporate / M&A": 0.6, "Regulatory": 0.4},
    "litigation_judgment": {"Litigation": 1.0},
    "litigation_scc_decision": {"Litigation": 0.8, "Regulatory": 0.2},
    "litigation_tribunal_decision": {"Regulatory": 0.7, "Litigation": 0.3},
    "insolvency_statistic": {"Restructuring / Insolvency": 1.0},
    "job_posting": {},
    "recall_health_canada": {"Regulatory": 0.7, "Litigation": 0.3},
    "recall_transport_canada": {"Regulatory": 1.0},
    "recall_cpsc_us": {"Regulatory": 0.6, "Litigation": 0.4},
    "consumer_complaint_spike": {"Regulatory": 0.7, "Litigation": 0.3},
    "consumer_complaint_financial": {"Banking & Finance": 0.6, "Regulatory": 0.4},
    "consumer_complaint_telecom": {"Regulatory": 1.0},
    "privacy_breach_report": {"Privacy & Cybersecurity": 1.0},
    "privacy_enforcement": {"Privacy & Cybersecurity": 1.0},
    "privacy_provincial_finding": {"Privacy & Cybersecurity": 1.0},
    "regulatory_health_recall": {"Regulatory": 0.7, "Litigation": 0.3},
    "regulatory_health_enforcement": {"Regulatory": 0.7, "Litigation": 0.3},
    "geo_flight_corporate_jet": {"Corporate / M&A": 1.0},
    "geo_permit_issued": {"Real Estate & Construction": 0.7, "Environmental": 0.3},
    "geo_permit_major_construction": {"Real Estate & Construction": 1.0},
    "geo_permit_demolition": {"Real Estate & Construction": 1.0},
    "geo_credit_downgrade": {"Restructuring / Insolvency": 0.6, "Banking & Finance": 0.4},
    "geo_credit_outlook_negative": {"Banking & Finance": 0.7, "Restructuring / Insolvency": 0.3},
    "geo_data_breach": {"Privacy & Cybersecurity": 1.0},
    "geo_labour_decision": {"Employment & Labour": 0.8, "Litigation": 0.2},
    "geo_union_certification": {"Employment & Labour": 1.0},
    "geo_trade_remedy": {"Regulatory": 0.7, "Litigation": 0.3},
    "geo_procurement_contract_award": {"Regulatory": 0.4, "Corporate / M&A": 0.6},
    "geo_property_tax_arrears": {
        "Real Estate & Construction": 0.6,
        "Restructuring / Insolvency": 0.4,
    },
    "geo_darkweb_mention": {"Privacy & Cybersecurity": 0.8, "Regulatory": 0.2},
    "geo_cipo_patent_grant": {"IP": 1.0},
    "geo_cfcj_access_to_justice": {},
    "news_mention": {},
    "macro_indicator": {},
    "social_breach_detected": {"Privacy & Cybersecurity": 1.0},
    "social_linkedin_exec_departure": {"Corporate / Governance": 1.0},
    "social_linkedin_legal_hire": {"Corporate / M&A": 0.5, "Litigation": 0.5},
    "blog_legal_trend": {},
    "blog_practice_alert": {"Regulatory": 0.5, "Litigation": 0.5},
    "class_action_filed": {"Litigation": 1.0},
    "class_action_filed_federal": {"Litigation": 1.0},
    "class_action_investigation": {"Litigation": 1.0},
    "class_action_analysis": {"Litigation": 0.6, "Regulatory": 0.4},
    # ── Phase S-NEW: 28 new practice area votes ─────────────────────────────
    # HNWI (Phase 1)
    "trust_deemed_disposition_approaching": {"Tax": 0.8, "Wills / Estates": 0.2},
    "estate_art_liquidation": {"Wills / Estates": 1.0},
    "probate_filing_high_value": {"Wills / Estates": 1.0},
    "hnwi_foundation_director_change": {
        "Wills / Estates": 0.3,
        "Tax": 0.3,
        "Corporate / Governance": 0.4,
    },
    "vessel_registry_change": {
        "Wills / Estates": 0.5,
        "Banking & Finance": 0.3,
        "Regulatory": 0.2,
    },
    # Immigration (Phase 2)
    "immigration_lmia_spike": {"Employment & Labour": 0.6, "Corporate / M&A": 0.4},
    "immigration_express_entry_draw": {"Employment & Labour": 1.0},
    # PE / VC (Phase 2)
    "pe_fund_exit_pressure": {"Corporate / M&A": 0.7, "Securities": 0.3},
    "vc_series_b_plus": {"Corporate / M&A": 0.6, "Securities": 0.4},
    # Financial Stress (Phase 3)
    "ppsa_layered_lending": {"Restructuring / Insolvency": 0.6, "Banking & Finance": 0.4},
    "credit_rating_downgrade_sp": {"Restructuring / Insolvency": 0.6, "Banking & Finance": 0.4},
    # Legal (Phase 3)
    "tax_court_dispute": {"Tax": 1.0},
    # Restructuring (Phase 3)
    "ccaa_monitor_report": {"Restructuring / Insolvency": 1.0},
    # Grants (Phase 3)
    "federal_grant_awarded": {"Corporate / M&A": 0.6, "IP": 0.4},
    # Courts (Phase 4)
    "ontario_commercial_list_filing": {"Restructuring / Insolvency": 0.5, "Litigation": 0.5},
    "bc_supreme_court_filing": {"Litigation": 1.0},
    "quebec_superior_court_filing": {"Litigation": 1.0},
    # Energy (Phase 4)
    "cer_pipeline_incident": {"Environmental": 0.5, "Regulatory": 0.5},
    # Macro (Phase 4)
    "cmhc_housing_starts_decline": {"Real Estate & Construction": 1.0},
    # IP (Phase 4)
    "trademark_new_class_expansion": {"IP": 0.6, "Corporate / M&A": 0.4},
    # Ownership (Phase 5)
    "beneficial_owner_change": {"Corporate / Governance": 1.0},
    # Pension (Phase 5)
    "pension_fund_investment": {"Corporate / M&A": 0.7, "Securities": 0.3},
    # Startups (Phase 5)
    "accelerator_cohort_member": {"Corporate / M&A": 0.6, "IP": 0.4},
    # Private Credit (Phase 5)
    "private_credit_deterioration": {"Restructuring / Insolvency": 1.0},
    # Environmental (Phase 6)
    "npri_pollution_spike": {"Environmental": 1.0},
    # Labour (Phase 6)
    "labour_code_payment_order": {"Employment & Labour": 1.0},
    "worksafebc_penalty": {"Employment & Labour": 0.7, "Regulatory": 0.3},
    # Macro BOS/SLOS (Phase 6)
    "macro_bos_credit_tightening": {"Banking & Finance": 0.7, "Restructuring / Insolvency": 0.3},
}


@dataclass
class ScoredSignal:
    signal_type: str
    days_ago: int
    fired_value: float = 1.0  # 1.0 = binary fired; could be continuous
    base_weight: float = field(init=False)
    category: str = field(init=False)

    def __post_init__(self) -> None:
        self.base_weight = SIGNAL_WEIGHTS.get(self.signal_type, 0.50)
        self.category = SIGNAL_CATEGORIES.get(self.signal_type, "other")

    @property
    def decayed_weight(self) -> float:
        """Exponential decay with half-life of 21 days."""
        decay = math.exp(-0.693 * self.days_ago / 21)
        return self.base_weight * decay * self.fired_value


def convergence_score(signals: list[ScoredSignal]) -> float:
    """
    Bayesian complement formula.
    Returns 0-100 probability that a mandate is forming.
    """
    if not signals:
        return 0.0

    prob_no_mandate = 1.0
    for sig in signals:
        prob_no_mandate *= 1.0 - sig.decayed_weight

    raw = (1.0 - prob_no_mandate) * 100

    # Convergence multiplier when signals span multiple categories
    unique_cats = {s.category for s in signals}
    if len(unique_cats) >= 5:
        raw = min(raw * 1.30, 100)
    elif len(unique_cats) >= 3:
        raw = min(raw * 1.18, 100)

    return round(raw, 1)


def classify_practice_area(signals: list[ScoredSignal]) -> tuple[str, float]:
    """
    Weighted vote classifier.
    Returns (practice_area_name, confidence_0_to_1).
    """
    from collections import defaultdict

    votes: dict[str, float] = defaultdict(float)

    for sig in signals:
        pa_votes = PRACTICE_AREA_VOTES.get(sig.signal_type, {})
        for pa, weight in pa_votes.items():
            votes[pa] += sig.decayed_weight * weight

    if not votes:
        return ("General / Unknown", 0.0)

    total = sum(votes.values())
    ranked = sorted(votes.items(), key=lambda x: x[1], reverse=True)
    top_pa, top_score = ranked[0]
    confidence = top_score / total if total > 0 else 0.0

    return (top_pa, round(confidence, 3))


def threshold_label(score: float) -> str | None:
    """Map a convergence score to its alert threshold label."""
    if score >= 95:
        return "CRITICAL"
    elif score >= 80:
        return "HIGH"
    elif score >= 65:
        return "MODERATE"
    elif score >= 50:
        return "WATCH"
    return None


def crossed_threshold(prev: float, curr: float) -> str | None:
    """Return threshold name if the score moved across a boundary, else None."""
    thresholds = [("CRITICAL", 95), ("HIGH", 80), ("MODERATE", 65), ("WATCH", 50)]
    for name, val in thresholds:
        if prev < val <= curr:
            return name
    return None
