"""
scripts/seed_db.py — Seed the database with realistic demo data.

Run: python -m scripts.seed_db
Requires a running PostgreSQL instance and DATABASE_URL in .env
"""

import asyncio
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, engine, Base
from app.models import *  # noqa — imports all models
from app.models.bd_activity import (
    Alumni, Partner, ReferralContact, WritingSample, ContentPiece
)
from app.models.signal import (
    CompetitorThreat, FootTrafficEvent, JetTrack,
    PermitFiling, RegulatoryAlert, SatelliteSignal
)

now = datetime.now(timezone.utc)


async def seed():
    # Drop and recreate all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await _seed_clients(db)
        await _seed_prospects(db)
        await _seed_partners(db)
        await _seed_alumni(db)
        await _seed_geo_signals(db)
        await _seed_regulatory_alerts(db)
        await _seed_triggers(db)
        await db.commit()

    print("✓ Database seeded successfully")


async def _seed_clients(db: AsyncSession):
    clients = [
        Client(name="Aurelia Capital Group",   industry="Asset Management",  region="Toronto",     partner_name="S. Chen",       churn_score=78, risk_level="critical", practice_groups=["M&A","Securities"],            annual_revenue=Decimal("1020000"), estimated_annual_spend=Decimal("8400000"), wallet_share_pct=12, days_since_last_contact=3),
        Client(name="Vantage Rail Corp",        industry="Infrastructure",    region="Calgary",     partner_name="M. Webb",       churn_score=61, risk_level="high",     practice_groups=["Regulatory","Employment"],      annual_revenue=Decimal("712000"),  estimated_annual_spend=Decimal("3100000"), wallet_share_pct=23, days_since_last_contact=8),
        Client(name="Centurion Pharma",         industry="Life Sciences",     region="Mississauga", partner_name="D. Park",       churn_score=44, risk_level="medium",   practice_groups=["IP","Litigation"],              annual_revenue=Decimal("680000"),  estimated_annual_spend=Decimal("2200000"), wallet_share_pct=31, days_since_last_contact=12),
        Client(name="Northfield Energy",        industry="Oil & Gas",         region="Calgary",     partner_name="J. Okafor",     churn_score=18, risk_level="low",      practice_groups=["M&A","Finance","Environmental"], annual_revenue=Decimal("3731000"), estimated_annual_spend=Decimal("9100000"), wallet_share_pct=41, days_since_last_contact=2),
        Client(name="Ember Financial",          industry="Banking",           region="Toronto",     partner_name="S. Chen",       churn_score=22, risk_level="low",      practice_groups=["Banking","Securities"],          annual_revenue=Decimal("1456000"), estimated_annual_spend=Decimal("18200000"),wallet_share_pct=8,  days_since_last_contact=1),
        Client(name="Solaris Construction",     industry="Real Estate",       region="Vancouver",   partner_name="P. Rodrigues",  churn_score=87, risk_level="critical", practice_groups=["Litigation","Real Estate"],     annual_revenue=Decimal("151300"),  estimated_annual_spend=Decimal("890000"),  wallet_share_pct=17, days_since_last_contact=41),
        Client(name="Meridian Logistics",       industry="Transportation",    region="Montreal",    partner_name="M. Webb",       churn_score=53, risk_level="medium",   practice_groups=["Trade","Litigation"],           annual_revenue=Decimal("513000"),  estimated_annual_spend=Decimal("2700000"), wallet_share_pct=19, days_since_last_contact=15),
        Client(name="ClearPath Technologies",   industry="Technology",        region="Waterloo",    partner_name="D. Park",       churn_score=29, risk_level="low",      practice_groups=["Finance","IP"],                 annual_revenue=Decimal("279000"),  estimated_annual_spend=Decimal("620000"),  wallet_share_pct=45, days_since_last_contact=5),
    ]
    for c in clients:
        c.is_active = True
        db.add(c)
    await db.flush()

    # Churn signals
    signals = [
        ChurnSignal(client_id=1, signal_text="Billing frequency dropped 38%", severity="high"),
        ChurnSignal(client_id=1, signal_text="GC replaced 6 weeks ago", severity="high"),
        ChurnSignal(client_id=1, signal_text="2 invoices disputed in 90 days", severity="medium"),
        ChurnSignal(client_id=6, signal_text="No contact in 41 days", severity="critical"),
        ChurnSignal(client_id=6, signal_text="LinkedIn: GC visiting competitor offices", severity="high"),
        ChurnSignal(client_id=6, signal_text="Lead partner leaving firm", severity="critical"),
        ChurnSignal(client_id=2, signal_text="Budget dispute unresolved", severity="medium"),
        ChurnSignal(client_id=7, signal_text="Associate changed twice on one matter", severity="medium"),
    ]
    for s in signals:
        db.add(s)


async def _seed_prospects(db: AsyncSession):
    from app.models.signal import Prospect
    prospects = [
        Prospect(name="Arctis Mining Corp",       industry="Mining",        legal_urgency_score=94, predicted_need="M&A Advisory",         estimated_value="$680K", outreach_window="2–4 wks", warmth="warm",      signals=["SEDAR: 3 confidentiality agreements filed","CFO departure announced","M&A banker LinkedIn spike","Competitor acquisition same week"]),
        Prospect(name="Pinnacle Health Systems",   industry="Healthcare",    legal_urgency_score=88, predicted_need="Regulatory Defense",    estimated_value="$420K", outreach_window="1–3 wks", warmth="warm",      signals=["Health Canada inspection notice","CIO resigned","Glassdoor compliance keywords +340%","GC LinkedIn activity ×5"]),
        Prospect(name="Westbrook Digital Corp",    industry="Technology",    legal_urgency_score=81, predicted_need="Privacy / Data Breach", estimated_value="$290K", outreach_window="48 hrs",  warmth="cold",      signals=["Credentials on BreachForums 03:14 AM","IT hiring +200% past 60 days","Privacy policy page deleted","CISO role posted"]),
        Prospect(name="Stellex Infrastructure Fund",industry="Finance",     legal_urgency_score=76, predicted_need="Fund Restructuring",    estimated_value="$1.1M", outreach_window="4–8 wks", warmth="lukewarm",  signals=["Investor redemption notice filed","LP concentration risk in 40-F","3 LP board seats changed"]),
        Prospect(name="Borealis Genomics Inc.",    industry="Life Sciences", legal_urgency_score=69, predicted_need="IP Licensing + Series C",estimated_value="$380K",outreach_window="6–10 wks",warmth="warm",      signals=["17 new PCT patent filings Q3","Trademark filings in 7 jurisdictions","VP BD hired from Moderna"]),
        Prospect(name="Caldwell Steel Works",      industry="Manufacturing", legal_urgency_score=63, predicted_need="Employment / WSIB",    estimated_value="$220K", outreach_window="2–4 wks", warmth="cold",      signals=["3 WSIB inspection orders in 90 days","Mass layoff notice filed","HR Director + VP Operations departed"]),
    ]
    for p in prospects:
        db.add(p)


async def _seed_partners(db: AsyncSession):
    partners = [
        Partner(name="S. Chen",     title="Senior Partner",  email="s.chen@halcyon.legal",     practice_areas=["M&A","Securities"],              target_industries=["Asset Management","Banking","Technology"]),
        Partner(name="M. Webb",     title="Partner",         email="m.webb@halcyon.legal",      practice_areas=["Regulatory","Employment"],        target_industries=["Infrastructure","Transportation","Energy"]),
        Partner(name="D. Park",     title="Partner",         email="d.park@halcyon.legal",      practice_areas=["IP","Litigation"],                target_industries=["Life Sciences","Technology","Consumer"]),
        Partner(name="J. Okafor",   title="Senior Partner",  email="j.okafor@halcyon.legal",    practice_areas=["Finance","Environmental","M&A"],  target_industries=["Oil & Gas","Mining","Infrastructure"]),
        Partner(name="P. Rodrigues",title="Partner",         email="p.rodrigues@halcyon.legal", practice_areas=["Litigation","Real Estate"],       target_industries=["Real Estate","Construction","Retail"]),
    ]
    for p in partners:
        db.add(p)
    await db.flush()

    # Referral contacts
    refs = [
        ReferralContact(partner_id=1, contact_name="David Chen",    firm_name="MNP Advisory",           contact_type="accountant", last_contact=now - timedelta(days=94), matters_sent=2, revenue_sent=Decimal("340000")),
        ReferralContact(partner_id=1, contact_name="Sarah Park",    firm_name="KPMG Corporate Finance",  contact_type="banker",     last_contact=now - timedelta(days=71), matters_sent=1, revenue_sent=Decimal("180000")),
        ReferralContact(partner_id=3, contact_name="Maria Santos",  firm_name="Deloitte Legal",          contact_type="accountant", last_contact=now - timedelta(days=112),matters_sent=3, revenue_sent=Decimal("510000")),
        ReferralContact(partner_id=3, contact_name="Kevin Wu",      firm_name="BDO Advisory",            contact_type="accountant", last_contact=now - timedelta(days=78), matters_sent=2, revenue_sent=Decimal("290000")),
    ]
    for r in refs:
        db.add(r)

    # Writing samples for Ghost Studio
    samples = [
        WritingSample(partner_id=1, text="The OSC's latest guidance on crypto asset disclosure isn't just a compliance checkbox — it redefines how boards think about digital asset risk. Three things every GC should flag before their next audit committee meeting.", content_type="linkedin_post"),
        WritingSample(partner_id=2, text="Transport Canada's new drone corridor regulations took effect this week. What most operators don't realise: the liability exposure for near-miss incidents has tripled under the new framework. Here's what your legal team needs to brief your board on.", content_type="linkedin_post"),
        WritingSample(partner_id=3, text="We just resolved a cross-border IP dispute that touched 7 jurisdictions. The biggest lesson wasn't about the law — it was about which conversations to have in the first 90 days before positions harden.", content_type="linkedin_post"),
        WritingSample(partner_id=4, text="The Clean Electricity Regulations aren't just about electrons. Every major project financing in this sector now requires Indigenous partnership agreements before a single turbine goes up. The legal timeline on that is longer than most developers think.", content_type="linkedin_post"),
    ]
    for s in samples:
        db.add(s)


async def _seed_alumni(db: AsyncSession):
    alumni = [
        Alumni(name="Tom Hartley",      current_role="Deputy GC",            current_company="Westbrook Digital Corp",       departure_year=2019, mentor_partner="D. Park",    warmth_score=92, has_active_trigger=True,  trigger_description="Data breach signal — call within 48 hrs"),
        Alumni(name="Sarah Yuen",       current_role="General Counsel",      current_company="Pinnacle Health Systems",      departure_year=2021, mentor_partner="D. Park",    warmth_score=88, has_active_trigger=True,  trigger_description="Health Canada inspection — regulatory mandate forming"),
        Alumni(name="Derek Ma",         current_role="VP Legal & Compliance", current_company="Stellex Infrastructure Fund", departure_year=2020, mentor_partner="J. Okafor",  warmth_score=74, has_active_trigger=True,  trigger_description="Fund restructuring signal detected"),
        Alumni(name="Monica Baptiste",  current_role="Senior Counsel",       current_company="Borealis Genomics",            departure_year=2018, mentor_partner="D. Park",    warmth_score=61, has_active_trigger=False),
        Alumni(name="Hassan Khalil",    current_role="Legal Counsel",        current_company="Arcadia Power Ltd.",           departure_year=2022, mentor_partner="M. Webb",    warmth_score=45, has_active_trigger=False),
    ]
    for a in alumni:
        db.add(a)


async def _seed_geo_signals(db: AsyncSession):
    # Jet tracks
    jets = [
        JetTrack(company="Arctis Mining Corp",       tail_number="C-FMTX", executive="CEO Marcus Reid",   origin_icao="CYYC", origin_name="Calgary YYC",     dest_icao="CYTZ", dest_name="Toronto Billy Bishop", departed_at=now - timedelta(days=1,  hours=2),  signal_text="3rd Bay Street trip in 10 days",          predicted_mandate="Corporate / M&A",   confidence=91, relationship_warmth=18, bay_street_trip_count=3, is_flagged=True),
        JetTrack(company="Stellex Infrastructure",   tail_number="C-GXLP", executive="CFO Jana Obi",      origin_icao="CYYZ", origin_name="Toronto Pearson",  dest_icao="KJFK", dest_name="New York JFK",         departed_at=now - timedelta(days=2,  hours=6),  signal_text="2nd NYC trip — Lazard HQ proximate",      predicted_mandate="Restructuring",     confidence=74, relationship_warmth=44, bay_street_trip_count=2, is_flagged=True),
        JetTrack(company="Vesta Retail REIT",        tail_number="C-HRTV", executive="CEO + COO",         origin_icao="CYYZ", origin_name="Toronto YYZ",      dest_icao="CYVR", dest_name="Vancouver YVR",         departed_at=now - timedelta(days=3,  hours=9),  signal_text="Unscheduled — no investor event listed",  predicted_mandate="Asset Sale",        confidence=68, relationship_warmth=5,  bay_street_trip_count=1, is_flagged=False),
        JetTrack(company="Caldwell Steel Works",     tail_number="N821PW",  executive="Board Chair",       origin_icao="KDTW", origin_name="Detroit DTW",      dest_icao="CYHM", dest_name="Hamilton YHM",          departed_at=now - timedelta(days=4,  hours=14), signal_text="Same-day return — restructuring counsel", predicted_mandate="Insolvency / CCAA", confidence=55, relationship_warmth=12, bay_street_trip_count=1, is_flagged=False),
    ]
    for j in jets:
        db.add(j)

    # Foot traffic
    foot = [
        FootTrafficEvent(target_company="Aurelia Capital Group",  client_id=1, location_name="Davies Ward Phillips — 155 Wellington St W",  location_type="competitor", device_count=14, avg_duration_minutes=150, occurred_at=now - timedelta(days=2), threat_assessment="RFP or active pitch in progress at rival firm",   severity="critical", recommended_action="Counter-pitch today. Use conflict arbitrage angle."),
        FootTrafficEvent(target_company="Meridian Logistics",     client_id=7, location_name="Blake Cassels CLE event space",               location_type="competitor", device_count=6,  avg_duration_minutes=480, occurred_at=now - timedelta(days=3), threat_assessment="Competitor relationship-building CLE event",        severity="high",     recommended_action="M. Webb to arrange direct 1:1 with GC this week."),
        FootTrafficEvent(target_company="Centurion Pharma",       client_id=3, location_name="Osler offices — 100 King St W",               location_type="competitor", device_count=8,  avg_duration_minutes=186, occurred_at=now - timedelta(days=5), threat_assessment="Potential mandate evaluation underway",             severity="high",     recommended_action="D. Park to call Deputy GC immediately."),
        FootTrafficEvent(target_company="Vantage Rail Corp",      client_id=2, location_name="Transport Canada Ottawa HQ",                  location_type="regulator",  device_count=22, avg_duration_minutes=480, occurred_at=now - timedelta(days=6), threat_assessment="Regulatory examination — personnel on-site all day", severity="medium",   recommended_action="Government audit likely. Offer regulatory response counsel."),
    ]
    for f in foot:
        db.add(f)

    # Satellite signals
    sats = [
        SatelliteSignal(company="Caldwell Steel Works",   location="Hamilton, ON",        signal_type="Workforce",     observation="Parking lot occupancy: 94% → 31% over 4 weeks",        legal_inference="Mass layoff forming — employment law mandate imminent within 2–3 weeks",       confidence=88, urgency="high"),
        SatelliteSignal(company="Northfield Energy",      location="Fort McMurray, AB",   signal_type="Construction",  observation="Excavation equipment appeared at previously idle pad",   legal_inference="Capital project resuming — construction, environmental, financing counsel needed", confidence=76, urgency="medium", lead_partner="J. Okafor"),
        SatelliteSignal(company="Arctis Mining Corp",     location="Timmins, ON",         signal_type="Supply Chain",  observation="Shipping container accumulation +340% vs 12-month avg", legal_inference="Supply chain disruption or shutdown preparation — restructuring signal",        confidence=71, urgency="medium"),
        SatelliteSignal(company="Unknown Industrial",     location="Sarnia, ON",          signal_type="Environmental", observation="Thermal plume detected — 3.2 km NE drift from facility", legal_inference="Environmental violation pre-enforcement — call before regulator does",         confidence=83, urgency="high"),
    ]
    for s in sats:
        db.add(s)

    # Permit filings
    permits = [
        PermitFiling(company="Northfield Energy Partners", permit_type="Environmental Assessment Application", project_type="New pipeline — 480 km corridor",       location="Fort McMurray, AB",   filed_at=now - timedelta(days=5), legal_work_triggered=["Environmental","Indigenous","Regulatory"],      urgency="high",   estimated_fee="$420K", lead_partner="J. Okafor", source_portal="IAAC Federal"),
        PermitFiling(company="Unknown Applicant",          permit_type="Demolition Permit — Class A tower",   project_type="Full commercial tower demolition",        location="King & Bay, Toronto", filed_at=now - timedelta(days=7), legal_work_triggered=["Real Estate","Construction","Lender Counsel"],  urgency="medium", estimated_fee="$180K"),
        PermitFiling(company="Borealis Genomics",          permit_type="Building Permit — Lab expansion",     project_type="22,000 sq ft R&D facility",               location="Waterloo Research Park",filed_at=now - timedelta(days=9),legal_work_triggered=["Construction","Employment","IP Licensing"],    urgency="medium", estimated_fee="$140K", lead_partner="D. Park", source_portal="City of Waterloo"),
        PermitFiling(company="Caldwell Steel Works",       permit_type="Change of Use — Industrial to Storage",project_type="Major facility conversion + rezoning",   location="Hamilton, ON",        filed_at=now - timedelta(days=12),legal_work_triggered=["Restructuring","Real Estate","Environmental"],   urgency="high",   estimated_fee="$220K", source_portal="City of Hamilton"),
    ]
    for p in permits:
        db.add(p)


async def _seed_regulatory_alerts(db: AsyncSession):
    alerts = [
        RegulatoryAlert(source="OSFI",    title="Guideline B-20 Amendment — Mortgage Stress Testing",      practice_area="Banking & Finance", severity="high",   published_at=now - timedelta(days=3),  affected_client_ids=[5]),
        RegulatoryAlert(source="OSC",     title="NI 45-106 Offering Memorandum Regime Update",             practice_area="Securities",        severity="medium", published_at=now - timedelta(days=7),  affected_client_ids=[1, 5]),
        RegulatoryAlert(source="CSA",     title="Staff Notice 51-363: Cannabis Sector Issuers",            practice_area="Regulatory",        severity="low",    published_at=now - timedelta(days=10), affected_client_ids=[3]),
        RegulatoryAlert(source="ECCC",    title="Clean Electricity Regulations — Final Rule",              practice_area="Environmental",     severity="high",   published_at=now - timedelta(days=16), affected_client_ids=[4, 2]),
        RegulatoryAlert(source="FINTRAC", title="AML Beneficial Ownership Threshold Changes",              practice_area="Banking & Finance", severity="high",   published_at=now - timedelta(days=25), affected_client_ids=[1, 5, 8]),
    ]
    for a in alerts:
        db.add(a)

    # Competitor threats
    threats = [
        CompetitorThreat(firm_name="Davies Ward Phillips", signal="Partner J. Holbrook (ex-Halcyon) now advising Aurelia Capital",               category="Alumni Threat",       level="critical", affected_clients=["Aurelia Capital Group"]),
        CompetitorThreat(firm_name="Osler Hoskin",         signal="Hired 4 M&A laterals with fintech background — targeting your clients",        category="Lateral Hire",        level="high",     affected_clients=["Aurelia Capital Group","Ember Financial"]),
        CompetitorThreat(firm_name="Stikeman Elliott",     signal="New Energy Transition practice group announced",                               category="Practice Expansion",  level="medium",   affected_clients=["Northfield Energy"]),
        CompetitorThreat(firm_name="Blake Cassels",        signal="Sponsoring CLEs attended by Meridian Logistics GC",                            category="Event Presence",      level="medium",   affected_clients=["Meridian Logistics"]),
    ]
    for t in threats:
        db.add(t)


async def _seed_triggers(db: AsyncSession):
    triggers = [
        Trigger(source="SEDAR",  trigger_type="Material Change Report",         company_name="Arctis Mining Corp",       practice_area="Corporate / M&A",         urgency=88, filed_at=now - timedelta(hours=8),  description="Material change report filed — transaction underway."),
        Trigger(source="EDGAR",  trigger_type="Confidential Treatment Request", company_name="Westbrook Digital Corp",   practice_area="Corporate / M&A",         urgency=89, filed_at=now - timedelta(hours=18), description="CTR filed on recent 8-K — deal terms redacted."),
        Trigger(source="CANLII", trigger_type="litigation_defendant",           company_name="Caldwell Steel Works",     practice_area="Litigation",              urgency=91, filed_at=now - timedelta(hours=32), description="Class action certification application — 847-person plaintiff class."),
        Trigger(source="JOBS",   trigger_type="job_cco_urgent",                 company_name="Ember Financial",          practice_area="Regulatory / AML",        urgency=85, filed_at=now - timedelta(hours=36), description="CCO role posted with 'immediate start'."),
        Trigger(source="OSC",    trigger_type="enforcement_action",             company_name="Centurion Pharma",         practice_area="Securities / Regulatory", urgency=90, filed_at=now - timedelta(hours=48), description="OSC enforcement proceeding commenced. Penalty exposure up to $5M."),
        Trigger(source="SEDAR",  trigger_type="Auditor Change",                 company_name="Vesta Retail REIT",        practice_area="Corporate / Governance",  urgency=79, filed_at=now - timedelta(hours=52), description="Auditor changed without disclosed reason."),
        Trigger(source="JOBS",   trigger_type="job_ma_counsel",                 company_name="Borealis Genomics Inc.",   practice_area="Corporate / M&A",         urgency=80, filed_at=now - timedelta(hours=60), description="In-house M&A counsel role posted — 4–6 week window."),
        Trigger(source="CANLII", trigger_type="canlii_ccaa",                   company_name="Stellex Infrastructure Fund", practice_area="Restructuring",        urgency=94, filed_at=now - timedelta(hours=64), description="CCAA protection filed. Monitor appointment imminent."),
    ]
    for t in triggers:
        db.add(t)


if __name__ == "__main__":
    asyncio.run(seed())
