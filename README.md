# BD for Law — Legal Market Intelligence Platform

> The first BigLaw BD platform operating in the **behavioral, physical, and predictive layers** where mandates are actually won and lost.

React + Vite · 19 AI modules · **6-module Geospatial Intelligence Layer** · Claude Sonnet AI throughout

---

## Quick Start

```bash
npm install && npm run dev   # → http://localhost:5173
```

---

## What's Built

### INTELLIGENCE
| Module | Description |
|--------|-------------|
| `Dashboard.jsx` | Command Center — KPIs, pipeline chart, live signal feeds |
| `ChurnPredictor.jsx` | Supervised ML churn scoring — billing rhythm, response time, associate changes |
| `RegulatoryRipple.jsx` | OSC/OSFI/CSA/SEC feed → client mapping → AI alert drafting |
| `RelationshipHeatMap.jsx` | Partner × client matrix with whitespace detection |

### GEOSPATIAL (New)
| Module | Signal Source | What It Detects |
|--------|--------------|-----------------|
| `GeoMandateMap.jsx` | NLP + political feeds | World map: legal demand intensity by jurisdiction (0–100) |
| `JetTracker.jsx` | Public ADS-B transponders | C-suite flights → M&A, financing, restructuring mandates |
| `FootTrafficIntel.jsx` | SafeGraph/Veraset GPS clusters | Clients visiting competitor offices; regulator visits; deal clusters |
| `SatelliteSignals.jsx` | Planet Labs / Maxar imagery | Parking lot occupancy, construction, environmental plumes |
| `PermitRadar.jsx` | ePlans, OneStop, POSSE, CEAA | Building/demolition/env permits → legal triggers |
| `ConferenceClusters.jsx` | Speaker lists + partner calendars | Physical co-location warmth delta + 72hr AI follow-up |

### ACQUISITION
| Module | Description |
|--------|-------------|
| `PreCrimeAcquisition.jsx` | Legal Urgency Index (0–100) from behavioral pre-signals |
| `MandatePreFormation.jsx` | 6-layer convergence detector — before GC calls any firm |
| `MADarkSignals.jsx` | M&A dark signals + supply chain litigation cascade |

### INTEL OPS
| Module | Description |
|--------|-------------|
| `CompetitiveIntel.jsx` | Competitor radar + conflict-of-interest arbitrage |
| `WalletShare.jsx` | Capture rate estimator + practice whitespace map |
| `AlumniActivator.jsx` | Former associates tracked in-house → trigger-based outreach |
| `GCProfiler.jsx` | Psychographic profiling + Trust Score dials (Trusted Advisor model) |
| `AssociateAccelerator.jsx` | Personal BD dashboard, warm path mapper, shadow origination tracker |
| `PitchAutopsy.jsx` | Win/loss stats + AI debrief agent + campaign orchestration |

---

## Geospatial Intelligence — Technical Detail

### Corporate Jet Tracker (ADS-B)
All commercial aircraft broadcast public ADS-B signals. Legal, free, real-time.

**Signal patterns → legal mandates:**
- Bay Street / Wall Street × 3+ trips in 30 days → M&A or financing active
- CEO jet same-day round trip to competitor city → confidential meeting
- C-suite + investment banker devices at same venue → deal signing
- PE firm HQ proximity → buyout process forming

*Data:* FlightAware API, OpenSky Network

### Foot Traffic (GPS Clustering)
1.6B+ devices tracked via commercial brokers (SafeGraph, Veraset). Anonymized.

**Detects:**
- Your client employees at competitor law firm offices → counter-pitch immediately
- Investment bank device clusters at client HQ → sell-side mandate awarded
- Regulator enforcement team at corporate campus → investigation underway

### Satellite Imagery
*Planet Labs / Maxar / Satellogic commercial APIs*

- **Parking lots** (occupancy drop 90% → 30% over 4 weeks) = mass layoff forming
- **Excavation detection** at idle industrial sites = capital project resuming
- **Thermal plumes** (multispectral) = environmental violation pre-enforcement
- **Container accumulation** = supply chain disruption / shutdown prep

### Construction Permits (Canada)
Daily scraping of all provincial portals:
- Ontario: **ePlans**
- BC: **OneStop**
- Alberta: **POSSE**
- Quebec: Municipal registries
- Federal: **CEAA** environmental assessments

Every permit → practice group assignment → partner notification

### Conference Gravity
Warmth delta from physical co-location:
- `< 1hr` = +5 to +12 pts
- `1–3 hrs` = +12 to +25 pts
- `Full day` = +25 to +40 pts
- Follow-up within 72hrs = ×1.8 multiplier

---

## ML Models (Backend Spec)

| Model | Type | Output | Notes |
|-------|------|--------|-------|
| Churn Classifier | XGBoost | Monthly risk 0–100 | ~74% precision @60+ threshold |
| Legal Urgency Index | RF + LightGBM | Company urgency 0–100 | 68% of ≥80 → mandate in 90d |
| Mandate Formation | Bayesian convergence | Confidence % + practice area | 81% @≥85 threshold |
| Semantic Loyalty Drift | Fine-tuned BERT | Relationship health delta | 90–120d advance detection |

Full model specs: `src/components/pages/GeospatialModule.js`

---

## Deploy

```bash
# GitHub
git init && git add . && git commit -m "feat: BD for Law v3.0"
git remote add origin https://github.com/YOUR_ORG/bd-for-law.git
git push -u origin main

# Vercel
npx vercel
# Add: VITE_ANTHROPIC_API_KEY in Vercel dashboard → Settings → Env Vars
```

## Stack

React 18 · Vite 5 · Tailwind CSS · Recharts · SVG Maps · Fraunces + JetBrains Mono · Anthropic Claude Sonnet
