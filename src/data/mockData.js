// ─── ORACLE Mock Data ────────────────────────────────────────────────────────

export const FIRM_NAME = "Blackstone Meridian LLP"

// ─── Clients ──────────────────────────────────────────────────────────────────
export const clients = [
  { id: 1, name: "Aurelia Capital Group", industry: "Asset Management", type: "Public", revenue: "$4.2B", matters: 14, activeMatter: "M&A Advisory", lastContact: 3, churnScore: 78, walletShare: 12, totalSpend: 8400000, firmRevenue: 1020000, riskLevel: "critical", geoRegion: "Toronto", partnerOwner: "Sarah Chen", practiceGroups: ["M&A", "Securities"] },
  { id: 2, name: "Vantage Rail Corp", industry: "Infrastructure", type: "Public", revenue: "$2.1B", matters: 7, activeMatter: "Regulatory Defense", lastContact: 8, churnScore: 61, walletShare: 23, totalSpend: 3100000, firmRevenue: 712000, riskLevel: "high", geoRegion: "Calgary", partnerOwner: "Marcus Webb", practiceGroups: ["Regulatory", "Employment"] },
  { id: 3, name: "Centurion Pharma Inc.", industry: "Life Sciences", type: "Public", revenue: "$890M", matters: 11, activeMatter: "IP Litigation", lastContact: 12, churnScore: 44, walletShare: 31, totalSpend: 2200000, firmRevenue: 680000, riskLevel: "medium", geoRegion: "Mississauga", partnerOwner: "Diana Park", practiceGroups: ["IP", "Litigation", "Regulatory"] },
  { id: 4, name: "Northfield Energy Partners", industry: "Oil & Gas", type: "Private", revenue: "$5.7B", matters: 22, activeMatter: "JV Structuring", lastContact: 2, churnScore: 18, walletShare: 41, totalSpend: 9100000, firmRevenue: 3731000, riskLevel: "low", geoRegion: "Calgary", partnerOwner: "James Okafor", practiceGroups: ["M&A", "Finance", "Environmental"] },
  { id: 5, name: "Ember Financial Services", industry: "Banking", type: "Public", revenue: "$12.3B", matters: 31, activeMatter: "OSFI Compliance", lastContact: 1, churnScore: 22, walletShare: 8, totalSpend: 18200000, firmRevenue: 1456000, riskLevel: "low", geoRegion: "Toronto", partnerOwner: "Sarah Chen", practiceGroups: ["Banking", "Securities", "Employment"] },
  { id: 6, name: "Solaris Construction Ltd.", industry: "Real Estate", type: "Private", revenue: "$340M", matters: 5, activeMatter: "Construction Dispute", lastContact: 41, churnScore: 87, walletShare: 17, totalSpend: 890000, firmRevenue: 151300, riskLevel: "critical", geoRegion: "Vancouver", partnerOwner: "Paul Rodrigues", practiceGroups: ["Litigation", "Real Estate"] },
  { id: 7, name: "Meridian Logistics Group", industry: "Transportation", type: "Public", revenue: "$1.4B", matters: 9, activeMatter: "Customs Dispute", lastContact: 15, churnScore: 53, walletShare: 19, totalSpend: 2700000, firmRevenue: 513000, riskLevel: "medium", geoRegion: "Montreal", partnerOwner: "Marcus Webb", practiceGroups: ["Trade", "Litigation"] },
  { id: 8, name: "ClearPath Technologies", industry: "Technology", type: "Private", revenue: "$180M", matters: 3, activeMatter: "Series C Financing", lastContact: 5, churnScore: 29, walletShare: 45, totalSpend: 620000, firmRevenue: 279000, riskLevel: "low", geoRegion: "Waterloo", partnerOwner: "Diana Park", practiceGroups: ["Finance", "IP", "Employment"] },
]

// ─── Churn Signals ────────────────────────────────────────────────────────────
export const churnSignals = [
  { clientId: 1, signals: ["Billing frequency dropped 38%", "GC changed 6 weeks ago", "2 invoices disputed in 90 days", "New associate assigned mid-matter", "Reply latency increased 4.2x"], trend: [-2, 0, 5, 12, 28, 41, 56, 78] },
  { clientId: 6, signals: ["No contact in 41 days", "Partner requested project update — ignored", "Company LinkedIn shows visits to competitor offices", "Matter stalled at client's instruction", "Lead partner leaving firm"], trend: [10, 15, 22, 31, 48, 62, 75, 87] },
  { clientId: 2, signals: ["Matter budget dispute unresolved", "CFO publicly commented on legal cost reduction", "3 junior billing write-offs in Q3", "Response time from partner increased"], trend: [20, 22, 28, 35, 42, 55, 61] },
  { clientId: 7, signals: ["Associate changed twice on one matter", "Billing rhythm slowed from monthly to quarterly"], trend: [28, 30, 35, 40, 48, 53] },
]

// ─── Regulatory Alerts ────────────────────────────────────────────────────────
export const regulatoryAlerts = [
  {
    id: "REG-001",
    source: "OSFI",
    title: "Guideline B-20: Residential Mortgage Underwriting Practices — Amendment",
    date: "2025-11-12",
    severity: "high",
    summary: "OSFI has issued amendments requiring federally regulated lenders to implement enhanced stress testing protocols for variable-rate mortgages, effective Q1 2026.",
    affectedClients: [5],
    practiceArea: "Banking & Finance",
    draftReady: true,
  },
  {
    id: "REG-002",
    source: "OSC",
    title: "National Instrument 45-106: Prospectus Exemptions — Update to Offering Memorandum Regime",
    date: "2025-11-08",
    severity: "medium",
    summary: "OSC amends OM exemption disclosure requirements with new risk acknowledgment language and enhanced investor eligibility criteria.",
    affectedClients: [1, 5],
    practiceArea: "Securities",
    draftReady: true,
  },
  {
    id: "REG-003",
    source: "CSA",
    title: "CSA Staff Notice 51-363: Issuers in the Cannabis Sector",
    date: "2025-11-05",
    severity: "low",
    summary: "Staff notice addressing reporting requirements for cannabis sector public issuers related to licensing continuity disclosures.",
    affectedClients: [3],
    practiceArea: "Regulatory / Securities",
    draftReady: false,
  },
  {
    id: "REG-004",
    source: "Environment Canada",
    title: "Clean Electricity Regulations — Final Rule Gazette II",
    date: "2025-10-29",
    severity: "high",
    summary: "Final regulations requiring non-emitting electricity generation standards for all federal entities and provincially regulated utilities by 2035.",
    affectedClients: [4, 2],
    practiceArea: "Environmental / Energy",
    draftReady: false,
  },
  {
    id: "REG-005",
    source: "FINTRAC",
    title: "Proceeds of Crime (ML/TF) Act Amendments — AML Beneficial Ownership",
    date: "2025-10-20",
    severity: "high",
    summary: "Expanded beneficial ownership reporting thresholds and enhanced due diligence requirements for financial entities.",
    affectedClients: [1, 5, 8],
    practiceArea: "Banking & Finance / Corporate",
    draftReady: true,
  },
]

// ─── Prospect Signals (Pre-Crime) ─────────────────────────────────────────────
export const prospects = [
  { id: 1, name: "Arctis Mining Corp", ticker: "ARC", industry: "Mining", market_cap: "$2.3B", urgency_score: 94, predicted_need: "M&A Advisory", signals: ["Filed 3 confidentiality agreements on SEDAR in 30 days", "CFO departure announced", "Hired M&A associate at Goldman Sachs internally", "Competitor acquisition announced same week"], warmth: "cold", path: "Partner Webb → shared board with ARC Chairman", timeframe: "2-4 weeks", est_value: "$680K" },
  { id: 2, name: "Pinnacle Health Systems", ticker: "PHS", industry: "Healthcare", market_cap: "$890M", urgency_score: 88, predicted_need: "Regulatory Defense", signals: ["Health Canada inspection notice filed", "CIO resigned without announcement", "Glassdoor compliance keyword spike +340%", "GC LinkedIn activity increased 5x"], warmth: "warm", path: "Diana Park mentored GC Sarah Yuen at U of T Law", timeframe: "1-3 weeks", est_value: "$420K" },
  { id: 3, name: "Westbrook Digital Corp", ticker: "WDC", industry: "Technology", market_cap: "$340M", urgency_score: 81, predicted_need: "Privacy / Data Breach Response", signals: ["Domain credentials appeared in BreachForums at 03:14 AM", "IT hiring velocity +200% past 60 days", "Privacy policy page deleted from website", "CISO role posted within 24h of breach signal"], warmth: "cold", path: "Alumni: Tom Hartley (former associate) → Deputy GC", timeframe: "48 hours", est_value: "$290K" },
  { id: 4, name: "Stellex Infrastructure Fund", ticker: "SIF", industry: "PE / Infrastructure", market_cap: "$5.1B", urgency_score: 76, predicted_need: "Fund Restructuring", signals: ["Investor redemption notice filed", "LP concentration risk in 40-F", "3 LP board seats changed in 60 days", "Hired external restructuring advisor (LinkedIn inference)"], warmth: "lukewarm", path: "2-degree: Marcus Webb → Osler partner → Stellex board", timeframe: "4-8 weeks", est_value: "$1.1M" },
  { id: 5, name: "Borealis Genomics Inc.", ticker: "BGI", industry: "Life Sciences", market_cap: "$180M", urgency_score: 69, predicted_need: "IP Licensing + Series C", signals: ["17 new PCT patent filings in Q3", "New trademark filings in 7 jurisdictions", "Hired VP Business Development from Moderna", "VC meeting inference from device clustering"], warmth: "warm", path: "Diana Park → VC firm partner → Borealis board", timeframe: "6-10 weeks", est_value: "$380K" },
  { id: 6, name: "Caldwell Steel Works Ltd.", industry: "Manufacturing", market_cap: "N/A (Private)", urgency_score: 63, predicted_need: "Employment / WSIB Defense", signals: ["3 WSIB inspection orders in 90 days", "Mass layoff notice filed with MOL", "6 small claims court filings against company", "HR Director and VP Operations both departed"], warmth: "cold", path: "Cold — no current relationship path", timeframe: "2-4 weeks", est_value: "$220K" },
]

// ─── Partners ─────────────────────────────────────────────────────────────────
export const partners = [
  { id: 1, name: "Sarah Chen", title: "Senior Partner", practice: "M&A / Securities", clients: [1, 5], book: 4200000, yoy: +12, bd_score: 84 },
  { id: 2, name: "Marcus Webb", title: "Partner", practice: "Regulatory / Trade", clients: [2, 7], book: 2800000, yoy: -3, bd_score: 61 },
  { id: 3, name: "Diana Park", title: "Partner", practice: "IP / Life Sciences", clients: [3, 8], book: 1900000, yoy: +22, bd_score: 78 },
  { id: 4, name: "James Okafor", title: "Senior Partner", practice: "Energy / M&A", clients: [4], book: 5600000, yoy: +8, bd_score: 91 },
  { id: 5, name: "Paul Rodrigues", title: "Partner", practice: "Litigation / Real Estate", clients: [6], book: 980000, yoy: -18, bd_score: 42 },
]

// ─── Relationship Heat Map Data ───────────────────────────────────────────────
export const heatMapData = partners.map(p => ({
  partner: p.name.split(' ')[0],
  ...Object.fromEntries(
    clients.map(c => [
      c.name.split(' ').slice(0,2).join(' '),
      p.clients.includes(c.id) ? Math.floor(Math.random() * 40) + 60 :
      Math.random() > 0.6 ? Math.floor(Math.random() * 30) + 10 : 0
    ])
  )
}))

// ─── Wallet Share ─────────────────────────────────────────────────────────────
export const walletShareData = clients.map(c => ({
  name: c.name.split(' ').slice(0,2).join(' '),
  captured: c.walletShare,
  uncaptured: 100 - c.walletShare,
  totalSpend: c.totalSpend,
  firmRevenue: c.firmRevenue,
  whitespace: ["Employment Law", "Tax", "ESG Advisory", "Restructuring", "IP Licensing"].slice(0, Math.floor(Math.random()*3)+1)
}))

// ─── Competitive Intel ────────────────────────────────────────────────────────
export const competitorActivity = [
  { firm: "Osler, Hoskin & Harcourt", signal: "Hired 4 M&A laterals with fintech background", date: "2025-10-28", threat_level: "high", affected_clients: ["Aurelia Capital Group", "Ember Financial Services"], category: "Lateral Hire" },
  { firm: "Stikeman Elliott", signal: "Announced new Energy Transition practice group", date: "2025-11-01", threat_level: "medium", affected_clients: ["Northfield Energy Partners"], category: "Practice Expansion" },
  { firm: "Davies Ward Phillips & Vineberg", signal: "Partner James Holbrook (former Blackstone Meridian) now advising Aurelia Capital", date: "2025-10-15", threat_level: "critical", affected_clients: ["Aurelia Capital Group"], category: "Alumni Threat" },
  { firm: "Blake, Cassels & Graydon", signal: "Sponsoring CLEs attended by Meridian Logistics GC", date: "2025-11-10", threat_level: "medium", affected_clients: ["Meridian Logistics Group"], category: "Event Presence" },
  { firm: "McCarthy Tétrault", signal: "Competitor to Centurion Pharma received enforcement action — conflict creates opening", date: "2025-11-08", threat_level: "low", affected_clients: ["Centurion Pharma Inc."], category: "Conflict Opportunity" },
]

// ─── Associates ───────────────────────────────────────────────────────────────
export const associates = [
  { id: 1, name: "Priya Mehta", year: 5, practice: "M&A", bd_activities: 12, pipeline_value: 340000, shadow_origination: 180000, opportunities: ["Borealis Genomics (warm - shared U of T alumni)", "ClearPath Tech (referred by client contact)"], content_plan: ["Post on OSFI B-20 impact for fintechs", "LinkedIn article: AI in M&A due diligence 2026"] },
  { id: 2, name: "Owen Clarke", year: 4, practice: "Litigation", bd_activities: 4, pipeline_value: 80000, shadow_origination: 0, opportunities: ["Caldwell Steel Works (WSIB exposure)"], content_plan: ["LinkedIn post on new Ontario Construction Act changes"] },
  { id: 3, name: "Nadia Osei", year: 6, practice: "Securities / Regulatory", bd_activities: 19, pipeline_value: 620000, shadow_origination: 290000, opportunities: ["Arctis Mining Corp (urgency 94)", "Westbrook Digital (privacy breach signal)"], content_plan: ["Client alert on CSA Staff Notice 51-363", "Webinar: New OSC Offering Memorandum regime"] },
  { id: 4, name: "Liam Park", year: 3, practice: "Employment", bd_activities: 6, pipeline_value: 120000, shadow_origination: 0, opportunities: ["Caldwell Steel Works (mass layoff notice filed)"], content_plan: ["Post: Mass termination notice obligations — 2025 update"] },
]

// ─── Alumni Network ───────────────────────────────────────────────────────────
export const alumni = [
  { id: 1, name: "Tom Hartley", left_year: 2019, current_role: "Deputy General Counsel", current_company: "Westbrook Digital Corp", practice_when_left: "Privacy & Technology", mentor: "Diana Park", trigger_active: true, trigger: "Data breach signal — mandate forming now", warmth: 92 },
  { id: 2, name: "Sarah Yuen", left_year: 2021, current_role: "General Counsel", current_company: "Pinnacle Health Systems", practice_when_left: "Regulatory / Health", mentor: "Diana Park", trigger_active: true, trigger: "Health Canada inspection — regulatory mandate", warmth: 88 },
  { id: 3, name: "Derek Ma", left_year: 2020, current_role: "VP Legal & Compliance", current_company: "Stellex Infrastructure Fund", practice_when_left: "Finance / PE", mentor: "James Okafor", trigger_active: true, trigger: "Fund restructuring signal detected", warmth: 74 },
  { id: 4, name: "Monica Baptiste", left_year: 2018, current_role: "Senior Counsel", current_company: "Borealis Genomics Inc.", practice_when_left: "IP / Life Sciences", mentor: "Diana Park", trigger_active: false, trigger: null, warmth: 61 },
  { id: 5, name: "Hassan Khalil", left_year: 2022, current_role: "Legal Counsel", current_company: "Arcadia Power Ltd.", practice_when_left: "Energy / Environmental", mentor: "Marcus Webb", trigger_active: false, trigger: null, warmth: 45 },
]

// ─── M&A Dark Signals ─────────────────────────────────────────────────────────
export const maDarkSignals = [
  { company: "Arctis Mining Corp", confidence: 91, signals: ["Options volume 340% above 90-day avg", "CEO jet tracked to Bay Street 3x in 10 days", "Investment banker LinkedIn spike with Lazard team", "Confidential treatment request filed on SEDAR"], predicted_type: "Sale Process (Sell-Side)", est_deal_value: "$2.1B–$2.8B", days_to_announcement: "14–28", relationship_warmth: 18 },
  { company: "Stellex Infrastructure Fund", confidence: 74, signals: ["LP redemption pressure from 40-F", "External restructuring advisor retained", "Board director resigned from audit committee", "Supply chain JV partner public filing change"], predicted_type: "Portfolio Restructuring / Recap", est_deal_value: "$800M–$1.4B", days_to_announcement: "30–60", relationship_warmth: 44 },
  { company: "Vesta Retail REIT", confidence: 68, signals: ["CRE broker clusters near HQ detected", "CEO attending CBRE private equity summit", "3 subsidiary name changes in 60 days"], predicted_type: "REIT Privatization or Portfolio Sale", est_deal_value: "$600M–$900M", days_to_announcement: "45–90", relationship_warmth: 5 },
]

// ─── Supply Chain Cascade ─────────────────────────────────────────────────────
export const supplyChainEvents = [
  { source_company: "Nexeon Chip Technologies", event: "US BIS Entity List designation (export controls)", date: "2025-11-10", cascade_targets: ["Centurion Pharma Inc.", "ClearPath Technologies", "Northfield Energy Partners"], legal_need: "Trade Compliance / Contract Force Majeure", urgency: "immediate", est_exposure: "$12M–$40M aggregate" },
  { source_company: "Pacific Freight Alliance", event: "Class action filed — rate-fixing conspiracy", date: "2025-10-30", cascade_targets: ["Meridian Logistics Group", "Vantage Rail Corp"], legal_need: "Litigation / Cartel Defense", urgency: "high", est_exposure: "$8M–$25M aggregate" },
]

// ─── GC Profiles ──────────────────────────────────────────────────────────────
export const gcProfiles = [
  {
    id: 1,
    name: "Raymond Lau",
    company: "Aurelia Capital Group",
    title: "General Counsel & Corporate Secretary",
    linkedin_summary: "Former OSC enforcement lawyer. Vocal on panels about AI in capital markets. Published 3 articles on insider trading in 2024. Mentioned 'cost discipline' in last 2 public panels.",
    psychographic: {
      decision_style: "Analytical / Evidence-driven",
      risk_tolerance: "Low",
      communication_pref: "Written briefs over calls",
      relationship_type: "Transaction-focused",
      career_ambition: "Board seat trajectory",
      fee_sensitivity: "High — publicly advocates for fixed-fee panels",
    },
    key_concerns: ["Regulatory exposure in AI-assisted trading", "Outside counsel cost control", "Board-level legal reporting"],
    pitch_hooks: ["Lead with your OSC regulatory team's enforcement defense track record", "Propose fixed-fee retainer with quarterly scope review", "Reference peer firms in asset management sector"],
    trust_score: 61,
  }
]

// ─── Pitches Won/Lost ────────────────────────────────────────────────────────
export const pitchData = [
  { date: "2025-Q3", won: 7, lost: 4, win_rate: 63.6 },
  { date: "2025-Q2", won: 5, lost: 6, win_rate: 45.5 },
  { date: "2025-Q1", won: 8, lost: 3, win_rate: 72.7 },
  { date: "2024-Q4", won: 6, lost: 5, win_rate: 54.5 },
  { date: "2024-Q3", won: 9, lost: 2, win_rate: 81.8 },
]

// ─── BD Performance ───────────────────────────────────────────────────────────
export const bdPerformanceData = [
  { month: "Jun", pipeline: 4200000, closed: 1800000, activities: 42 },
  { month: "Jul", pipeline: 4800000, closed: 2100000, activities: 38 },
  { month: "Aug", pipeline: 3900000, closed: 1400000, activities: 31 },
  { month: "Sep", pipeline: 5200000, closed: 2600000, activities: 51 },
  { month: "Oct", pipeline: 6100000, closed: 2900000, activities: 48 },
  { month: "Nov", pipeline: 7400000, closed: 3100000, activities: 55 },
]

// ─── KPIs ──────────────────────────────────────────────────────────────────────
export const kpis = {
  total_pipeline: 7400000,
  pipeline_change: +21,
  clients_at_risk: 3,
  active_prospects: 6,
  regulatory_alerts: 5,
  win_rate: 63.6,
  win_rate_change: +18.1,
  avg_wallet_share: 24.5,
  wallet_share_change: +3.2,
  mandate_signals: 9,
}
