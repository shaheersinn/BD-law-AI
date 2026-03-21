// ─── BD for Law — Geospatial Intelligence Module ─────────────────────────────
// 6 pages covering all geospatial features from the product specification.
// Each page is fully implemented in the live dashboard artifact (BDforLaw_Dashboard.jsx).
// To run locally: npm install && npm run dev

export const GEOSPATIAL_MODULES = [
  {
    id: "geomap",
    name: "Geopolitical Mandate Heat Map",
    file: "GeoMandateMap.jsx",
    description: `
      Interactive SVG world map showing legal demand intensity by jurisdiction (0-100).
      Hover any country/region to see: practice area, mandate drivers, intensity score.
      
      Data sources:
      - Parliamentary/congressional hearing monitoring (NLP)
      - Regulatory agency budget announcements
      - Trade agreement and sanctions feeds
      - Election result mapping to legal demand patterns
      - Real-time filter by practice area (M&A, Regulatory, Litigation, etc.)
      
      Key feature: Geopolitical triggers panel shows 4 active mandate waves
      with predicted practice area and recommended positioning timing.
    `,
    dataFile: "geoPoliticalData.js",
  },
  {
    id: "jets",
    name: "Corporate Jet Tracker",
    file: "JetTracker.jsx",
    description: `
      Real-time ADS-B transponder signal aggregation for corporate aircraft.
      All commercial aircraft broadcast public ADS-B — this is 100% legal.
      
      Intelligence signals:
      - CEO jet to financial centers (NYC, London, Zurich, Toronto) → M&A/financing
      - Same-day round trips → confidential meeting at destination
      - Repeat routes (3+ in 30 days) → active deal process
      - Multiple executives on same flight → board/closing meeting
      - PE firm HQ proximity → buyout process forming
      
      Interactive map: SVG flight path visualization with clickable routes.
      Each route generates an AI tactical brief with legal seat recommendations.
      
      Data integration: FlightAware API, OpenSky Network (free public ADS-B)
    `,
    dataFile: "jetTrackData.js",
  },
  {
    id: "foot",
    name: "Foot Traffic Intelligence",
    file: "FootTrafficIntel.jsx",
    description: `
      Commercial GPS clustering data legally aggregated from brokers 
      (SafeGraph, Veraset, Placer.ai). Tracks device clusters at:
      
      - Competitor law firm offices → client evaluating other counsel
      - Investment bank offices → deal mandate in progress  
      - Regulator offices (OSC, SEC, OSFI) at client HQ → investigation
      - Conference venues → relationship-building opportunities
      
      Severity tiers:
      - CRITICAL: Your existing client visiting competitor firm (counter-pitch today)
      - HIGH: Investment bank hotspot + your client overlap (deal forming)
      - MEDIUM: Regulatory examination signals
      
      AI response brief: interprets clustering event, who acts, exact action.
      
      Note: Uses anonymized device-level data, not individual tracking.
    `,
    dataFile: "footTrafficData.js",
  },
  {
    id: "sat",
    name: "Satellite Signal Intelligence", 
    file: "SatelliteSignals.jsx",
    description: `
      Commercial satellite and multispectral imagery analysis.
      
      Signal types:
      WORKFORCE: Parking lot occupancy monitoring (mass layoff detection)
        - Drop from 90%+ to <35% over 4 weeks = mass layoff forming
        - Employment law mandate typically follows in 2-6 weeks
      
      CONSTRUCTION: Excavation/equipment detection at industrial sites
        - New equipment at idle site = capital project resuming
        - Triggers: construction contracts, environmental permits, financing
      
      ENVIRONMENTAL: Thermal plume and chemical runoff detection
        - Multispectral imaging detects violations before EPA/ECCC inspectors
        - Firm calls company before regulator does = first-mover advantage
      
      SUPPLY CHAIN: Container/inventory anomalies
        - Unusual container accumulation = supply disruption or shutdown prep
        
      Data providers: Planet Labs, Maxar, Satellogic (commercial API)
      Update frequency: 3-5 day revisit cycle for Canadian/US facilities
    `,
    dataFile: "satelliteData.js",
  },
  {
    id: "permits",
    name: "Construction Permit Surveillance",
    file: "PermitRadar.jsx",
    description: `
      Real-time scraping of Canadian and US public permit portals.
      
      Canadian sources (scraped daily):
      - Ontario ePlans portal
      - BC OneStop (online services)
      - Alberta POSSE system
      - Quebec municipal permit registries
      - Federal CEAA environmental assessment filings
      - Provincial land registry systems (Teranet, BC LTO, SPIN2)
      
      US sources:
      - Municipal open data APIs (NYC, Chicago, LA, Seattle)
      - EPA environmental assessment database
      - Army Corps of Engineers permits
      
      Permit types → legal triggers:
      - Building permit (new jurisdiction) = expansion = employment/construction/regulatory
      - Demolition permit = restructuring/asset sale/lender enforcement
      - Environmental assessment = Indigenous consultation/regulatory approvals
      - Change of use = business wind-down/asset monetization
      - Builders lien filed = construction dispute forming NOW
      
      Auto-assigns to practice group partner based on permit type + geography.
    `,
    dataFile: "permitData.js",
  },
  {
    id: "conf",
    name: "Conference Relationship Gravity",
    file: "ConferenceClusters.jsx",
    description: `
      Tracks physical co-location of firm partners and target GCs at industry events.
      
      Data sources:
      - Conference speaker/attendee lists (scraped from event websites)
      - PDAC, OBA Institute, Clean Energy Canada, legal sector summits
      - Cross-referenced against firm partner calendars
      
      Warmth delta calculation:
      - Co-location < 1 hour = +5 to +12 pts
      - Co-location 1-3 hours = +12 to +25 pts  
      - Full-day co-location = +25 to +40 pts
      - Follow-up within 72 hours multiplies warmth gain by 1.8x
      
      Output: 
      - "Relationship Warming Report" per conference
      - AI-generated 72-hour follow-up brief
      - Optimal message referencing specific conference context
      
      Physical proximity is the #1 BD touchpoint lawyers never log in CRM.
      This makes the invisible visible.
    `,
    dataFile: "conferenceData.js",
  },
];

export const ML_MODELS = [
  {
    name: "Churn Classifier",
    type: "Gradient Boosting (XGBoost)",
    features: ["billing_frequency_delta", "response_time_delta", "associate_changes", "invoice_disputes", "matter_count_change", "partner_contact_gap"],
    output: "Monthly flight risk probability (0-100)",
    training: "Firm's historical matter/billing data — minimum 3 years",
    accuracy: "~74% precision at 60+ risk threshold (industry benchmark)",
  },
  {
    name: "Legal Urgency Index",
    type: "Multi-signal Ensemble (RF + LightGBM)",
    features: ["sedar_filings_delta", "linkedin_executive_changes", "job_posting_velocity", "dark_web_mentions", "options_volume_anomaly", "glassdoor_keyword_spike"],
    output: "0-100 urgency score per company",
    training: "Historical mandate triggers from public deal databases",
    accuracy: "~68% of scores ≥80 result in mandate within 90 days",
  },
  {
    name: "Mandate Formation Detector",
    type: "Multi-layer Convergence (Bayesian)",
    features: ["regulatory_layer", "human_capital_layer", "behavioral_nlp_layer", "dark_web_layer", "ma_signal_layer", "structural_layer"],
    output: "Formation confidence % + predicted practice area",
    training: "Labeled mandate formation events from CanLII/EDGAR/SEDAR",
    accuracy: "~81% at ≥85 confidence threshold",
  },
  {
    name: "Semantic Loyalty Drift",
    type: "NLP (fine-tuned BERT)",
    features: ["pronoun_ratio", "message_entropy", "response_latency", "topic_narrowing", "formality_regression"],
    output: "Monthly relationship health score + drift alert",
    training: "Anonymized firm email corpus (requires consent)",
    accuracy: "Detects departure intent 90-120 days in advance",
  },
];
