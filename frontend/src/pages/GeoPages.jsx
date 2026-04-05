/**
 * pages/GeoPages.jsx — P17 Redesign
 * Five geospatial intelligence modules: GeoMap, JetTracker, FootTraffic, Satellite, PermitRadar
 * Removes inline styles for injected CSS and uses DM type stack.
 */

import { useState } from "react";
import * as apiClient from "../api/client.js";
import AppShell from '../components/layout/AppShell';

/* ── CSS Injection ────────────────────────────────────────────────────────── */
const GEO_CSS = `
.geo-tag { background:rgba(106,137,180,.1); border:1px solid rgba(106,137,180,.25); color:var(--color-on-surface-variant); font-size:9px; font-family:var(--font-mono); letter-spacing:.07em; padding:2px 8px; border-radius:2px; white-space:nowrap; }
.geo-tag.red { background:rgba(224,82,82,.1); border-color:rgba(224,82,82,.3); color:var(--color-error); }
.geo-tag.gold { background:rgba(212,168,67,.1); border-color:rgba(212,168,67,.3); color:var(--color-secondary); }
.geo-tag.green { background:rgba(61,186,122,.1); border-color:rgba(61,186,122,.3); color:var(--color-success); }
.geo-tag.blue { background:rgba(74,143,255,.1); border-color:rgba(74,143,255,.3); color:var(--color-primary); }
.geo-tag.cyan { background:rgba(34,201,212,.1); border-color:rgba(34,201,212,.3); color:var(--color-secondary); }
.geo-tag.purple { background:rgba(155,109,255,.1); border-color:rgba(155,109,255,.3); color:var(--color-primary-container); }

.geo-sbar { display:flex; align-items:center; gap:8px; }
.geo-sbar-track { flex:1; height:3px; background:var(--color-surface-container-high); border-radius:2px; overflow:hidden; }
.geo-sbar-fill { height:100%; border-radius:2px; transition:width .8s ease; }
.geo-sbar-val { font-family:var(--font-mono); font-size:11px; width:26px; text-align:right; }

.geo-panel { background:var(--color-surface-container-lowest); border:1px solid var(--color-outline-variant); border-radius:4px; }
.geo-panel-header { padding:12px 16px; border-bottom:1px solid var(--color-outline-variant); display:flex; justify-content:space-between; align-items:center; }
.geo-panel-title { font-family:var(--font-mono); font-size:10px; color:var(--color-on-surface-variant); letter-spacing:.08em; text-transform:uppercase; }

.geo-metric { background:var(--color-surface-container-lowest); border:1px solid var(--color-outline-variant); border-radius:4px; padding:16px 18px; position:relative; overflow:hidden; }
.geo-metric-label { font-size:9px; font-family:var(--font-mono); color:var(--color-on-surface-variant); letter-spacing:.1em; text-transform:uppercase; margin-bottom:8px; }
.geo-metric-val { font-family:var(--font-mono); font-size:26px; font-weight:600; line-height:1; }
.geo-metric-sub { margin-top:6px; font-size:10px; color:var(--color-on-surface-variant); font-family:var(--font-data); }
.geo-metric-bot { position:absolute; bottom:0; left:0; right:0; height:2px; opacity:.3; }

.geo-ph { margin-bottom:20px; padding-bottom:16px; border-bottom:1px solid var(--color-outline-variant); }
.geo-ph-tag { font-family:var(--font-mono); font-size:9px; color:var(--color-secondary); letter-spacing:.14em; margin-bottom:6px; text-transform:uppercase; }
.geo-ph-title { font-family:var(--font-editorial); font-weight:800; font-size:22px; letter-spacing:-.03em; margin-bottom:4px; color:var(--color-on-surface); }
.geo-ph-sub { color:var(--color-on-surface-variant); font-size:12px; line-height:1.6; font-family:var(--font-data); }

.geo-obtn { padding:7px 16px; border-radius:3px; font-family:var(--font-data); font-size:10px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; border:none; background:var(--color-secondary); color:#fff; cursor:pointer; }
.geo-obtn.small { padding:5px 12px; }
.geo-obtn:disabled { opacity:.6; cursor:default; }

/* Grid / Page Specific */
.geo-page-root { height:100%; overflow-y:auto; padding:20px 24px; }
.geo-grid-4 { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:16px; }
.geo-grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.geo-grid-sidebar { display:grid; grid-template-columns:280px 1fr; gap:12px; }

.geo-list-header { padding:10px 14px; border-bottom:1px solid var(--color-outline-variant); font-family:var(--font-mono); font-size:9px; color:var(--color-on-surface-variant); letter-spacing:.1em; }
.geo-list-item { padding:12px 14px; border-bottom:1px solid var(--color-outline-variant); cursor:pointer; border-left:2px solid transparent; transition:background 0.12s; }
.geo-list-item.active { background:var(--color-surface-container-low); border-left-color:var(--color-secondary); }
.geo-item-title { font-size:12px; font-weight:600; color:var(--color-on-surface); font-family:var(--font-data); }
.geo-item-meta { font-size:10px; color:var(--color-on-surface-variant); margin-bottom:4px; font-family:var(--font-data); }

.geo-detail-title { font-family:var(--font-editorial); font-weight:800; font-size:20px; color:var(--color-on-surface); margin-bottom:6px; }
.geo-detail-val { font-family:var(--font-mono); font-size:44px; font-weight:700; line-height:1; }
.geo-detail-sub { font-size:8px; color:var(--color-on-surface-variant); font-family:var(--font-mono); }

.geo-brief-box { font-size:13px; line-height:1.75; color:var(--color-on-surface-variant); border-left:2px solid var(--color-secondary); padding-left:14px; font-family:var(--font-data); }
.geo-brief-empty { font-size:11px; color:var(--color-on-surface-variant); font-style:italic; font-family:var(--font-data); }
`;

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('geo-styles')) {
    const el = document.createElement('style')
    el.id = 'geo-styles'
    el.textContent = GEO_CSS
    document.head.appendChild(el)
  }
}

/* ── Shared Primitives ────────────────────────────────────────────────────── */
const Tag = ({ label, color = "default" }) => (
  <span className={`geo-tag ${color}`}>{label}</span>
);

const SBar = ({ s, color }) => {
  const c = color || (s >= 75 ? "var(--color-error)" : s >= 50 ? "var(--color-warning)" : s >= 30 ? "var(--color-secondary)" : "var(--color-success)");
  return (
    <div className="geo-sbar">
      <div className="geo-sbar-track">
        <div className="geo-sbar-fill" style={{ width: `${s}%`, background: c }} />
      </div>
      <span className="geo-sbar-val" style={{ color: c }}>{s}</span>
    </div>
  )
}

const Panel = ({ title, children, actions, style = {} }) => (
  <div className="geo-panel" style={style}>
    {title && (
      <div className="geo-panel-header">
        <span className="geo-panel-title">{title}</span>
        {actions}
      </div>
    )}
    {children}
  </div>
)

const Metric = ({ label, val, sub, accent = "gold" }) => {
  const cols = { gold: "var(--color-secondary)", red: "var(--color-error)", green: "var(--color-success)", blue: "var(--color-primary)", purple: "var(--color-primary-container)", cyan: "var(--color-secondary)" };
  const c = cols[accent] || "var(--color-on-surface)";
  return (
    <div className="geo-metric">
      <div className="geo-metric-label">{label}</div>
      <div className="geo-metric-val" style={{ color: c }}>{val}</div>
      {sub && <div className="geo-metric-sub">{sub}</div>}
      <div className="geo-metric-bot" style={{ background: c }} />
    </div>
  )
}

const PageHeader = ({ tag, title, sub }) => (
  <div className="geo-ph">
    {tag && <div className="geo-ph-tag">◈ {tag}</div>}
    <h1 className="geo-ph-title">{title}</h1>
    {sub && <p className="geo-ph-sub">{sub}</p>}
  </div>
)

const OBtn = ({ children, onClick, disabled, small }) => (
  <button onClick={onClick} disabled={disabled} className={`geo-obtn ${small ? 'small' : ''}`}>
    {children}
  </button>
)

const AiBadge = () => <Tag label="◈ AI" color="gold"/>

const Spinner = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--color-on-surface-variant)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
    Processing...
  </div>
)

/* ── Data ─────────────────────────────────────────────────────────────────── */
const GEO = [
  { id: "can", label: "Canada", x: 195, y: 112, v: 91, practice: "M&A + Regulatory", drivers: "OSC enforcement wave, energy transition mandates, Indigenous consultation law" },
  { id: "usa", label: "USA", x: 188, y: 172, v: 88, practice: "Securities + Litigation", drivers: "DOJ tech enforcement, climate litigation, cross-border M&A clearance" },
  { id: "eu",  label: "EU", x: 448, y: 148, v: 79, practice: "Regulatory + Data", drivers: "EU AI Act enforcement, CSRD mandates, antitrust wave" },
  { id: "uk",  label: "UK", x: 420, y: 134, v: 72, practice: "Finance + Sanctions", drivers: "Post-Brexit disputes, OFSI sanctions compliance, crypto regulation" },
  { id: "uae", label: "UAE", x: 552, y: 214, v: 68, practice: "Arbitration + M&A", drivers: "DIFC arbitration surge, sovereign wealth structuring" },
  { id: "aus", label: "Australia", x: 698, y: 312, v: 61, practice: "Mining + Environmental", drivers: "Critical minerals law, native title litigation, ESG disclosure" },
  { id: "sgp", label: "Singapore", x: 670, y: 250, v: 74, practice: "Dispute + Finance", drivers: "Fintech disputes, family office structuring, supply chain arbitration" },
  { id: "ind", label: "India", x: 610, y: 222, v: 66, practice: "Corporate + Arbitration", drivers: "FDI disputes, infrastructure arbitration, data localisation" },
  { id: "jpn", label: "Japan", x: 715, y: 172, v: 63, practice: "M&A + IP", drivers: "Inbound M&A, semiconductor IP disputes, carbon credit structuring" },
];

const JETS = [
  { co: "Arctis Mining Corp", tail: "C-FMTX", exec: "CEO Marcus Reid", from: "Calgary YYC", to: "Toronto Billy Bishop", date: "Nov 14 · 09:22", sig: "3rd Bay Street trip in 10 days", mandate: "M&A — Sell-Side", conf: 91, warmth: 18 },
  { co: "Stellex Infrastructure", tail: "C-GXLP", exec: "CFO Jana Obi", from: "Toronto Pearson", to: "New York JFK", date: "Nov 13 · 14:05", sig: "2nd NYC trip — Lazard HQ proximate", mandate: "Fund Restructuring", conf: 74, warmth: 44 },
  { co: "Vesta Retail REIT", tail: "C-HRTV", exec: "CEO + COO", from: "Toronto YYZ", to: "Vancouver YVR", date: "Nov 12 · 07:44", sig: "Unscheduled — no investor event listed", mandate: "Asset Sale", conf: 68, warmth: 5 },
  { co: "Caldwell Steel Works", tail: "N821PW", exec: "Board Chair", from: "Detroit DTW", to: "Hamilton YHM", date: "Nov 11 · 16:30", sig: "Same-day return — restructuring counsel", mandate: "Insolvency / CCAA", conf: 55, warmth: 12 },
  { co: "Borealis Genomics", tail: "C-FVXQ", exec: "CFO + VP BD", from: "Waterloo YKF", to: "Boston BOS", date: "Nov 10 · 08:15", sig: "3rd Boston trip — Kendall Square biotech", mandate: "Series C / Licensing", conf: 62, warmth: 38 },
];

const FOOT = [
  { target: "Aurelia Capital Group", loc: "Davies Ward Phillips — 155 Wellington St W", dev: 14, dur: "2.5 hrs avg", date: "Nov 13", threat: "RFP or active pitch in progress at rival firm", sev: "critical", action: "Counter-pitch today. Use conflict arbitrage angle — Davies has CIBC retainer." },
  { target: "Meridian Logistics", loc: "Blake Cassels CLE event space", dev: 6, dur: "Full day", date: "Nov 12", threat: "Competitor relationship-building CLE event", sev: "high", action: "M. Webb to arrange direct 1:1 with GC this week before Blake creates loyalty." },
  { target: "Centurion Pharma", loc: "Osler offices — 100 King St W", dev: 8, dur: "3.1 hrs avg", date: "Nov 10", threat: "Potential mandate evaluation — multiple visits in 21 days", sev: "high", action: "D. Park to call Deputy GC immediately. IP matter is vulnerable." },
  { target: "Vantage Rail Corp", loc: "Transport Canada Ottawa HQ", dev: 22, dur: "All day", date: "Nov 09", threat: "Regulatory examination — personnel on-site all day", sev: "medium", action: "Regulatory audit likely. Offer pre-response counsel before file opens." },
];

const SAT = [
  { co: "Caldwell Steel Works", loc: "Hamilton, ON", sig: "Parking lot occupancy: 94% → 31% over 4 weeks", inf: "Mass layoff forming — employment law mandate imminent within 2–3 weeks", conf: 88, type: "Workforce", urg: "high", lead: null },
  { co: "Northfield Energy", loc: "Fort McMurray, AB", sig: "Excavation equipment appeared at previously idle pad", inf: "Capital project resuming — construction, environmental, financing counsel needed", conf: 76, type: "Construction", urg: "medium", lead: "J. Okafor" },
  { co: "Arctis Mining Corp", loc: "Timmins, ON", sig: "Shipping container accumulation +340% vs 12-month avg", inf: "Supply chain disruption or shutdown preparation — restructuring signal", conf: 71, type: "Supply Chain", urg: "medium", lead: null },
  { co: "Unknown Industrial", loc: "Sarnia, ON corridor", sig: "Thermal plume detected — 3.2 km NE drift from facility", inf: "Environmental violation pre-enforcement — call before regulator does", conf: 83, type: "Environmental", urg: "high", lead: null },
  { co: "Borealis Genomics", loc: "Waterloo, ON", sig: "Structural steel erected — new building footprint visible", inf: "Lab expansion confirmed — construction, employment, IP licensing counsel", conf: 91, type: "Construction", urg: "low", lead: "D. Park" },
];

const PERMITS = [
  { co: "Northfield Energy Partners", permit: "Environmental Assessment Application", loc: "Fort McMurray, AB", filed: "Nov 10", type: "New pipeline — 480 km corridor", work: ["Environmental", "Indigenous", "Regulatory"], urg: "high", rev: "$420K", lead: "J. Okafor" },
  { co: "Unknown Applicant", permit: "Demolition Permit — Class A tower", loc: "King & Bay, Toronto", filed: "Nov 08", type: "Full commercial tower demolition", work: ["Real Estate", "Construction", "Lender Counsel"], urg: "medium", rev: "$180K", lead: null },
  { co: "Borealis Genomics", permit: "Building Permit — Lab expansion", loc: "Waterloo Research Park", filed: "Nov 06", type: "22,000 sq ft R&D facility", work: ["Construction", "Employment", "IP Licensing"], urg: "medium", rev: "$140K", lead: "D. Park" },
  { co: "Caldwell Steel Works", permit: "Change of Use — Industrial to Storage", loc: "Hamilton, ON", filed: "Nov 03", type: "Major facility conversion + rezoning", work: ["Restructuring", "Real Estate", "Environmental"], urg: "high", rev: "$220K", lead: null },
  { co: "Stellex Infrastructure", permit: "Environmental Impact Assessment", loc: "Kitchener-Waterloo", filed: "Oct 28", type: "Solar farm — 1,200 acres", work: ["Environmental", "Land Use", "Indigenous", "Finance"], urg: "medium", rev: "$310K", lead: "J. Okafor" },
];

/* ── 1. GEOPOLITICAL HEAT MAP ───────────────────────────────────────────── */
export const GeoMap = () => {
  const [sel, setSel] = useState(GEO[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const intCol = v => v >= 80 ? "var(--color-error)" : v >= 65 ? "var(--color-warning)" : v >= 50 ? "var(--color-secondary)" : "var(--color-primary)";

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const token = sessionStorage.getItem('bdforlaw_token')
      const r = await fetch(`/api/v1/signals?limit=10&category=geo`, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) throw new Error(`${r.status}`)
      const data = await r.json()
      const list = Array.isArray(data) ? data : []
      setBrief(list.length > 0 ? `${list.length} geo signals active.\\n` + list.slice(0, 5).map(s => `• ${s.signal_type || 'signal'}: ${s.raw_company_name || s.signal_text?.slice(0, 60) || 'event'}`).join('\\n') : 'No geo signals yet — scrapers accumulate data over 24–72 hours.')
    } catch (e) { setBrief("API error.") }
    setLoading(false);
  }

  return (
    <div className="geo-page-root">
      <PageHeader tag="Geopolitical Intelligence" title="Mandate Heat Map" sub="Legal demand intensity by jurisdiction."/>
      <div className="geo-grid-4">
        <Metric label="Jurisdictions Tracked" val={GEO.length} sub="active monitors" accent="blue"/>
        <Metric label="High Demand" val={GEO.filter(g => g.v >= 75).length} sub="≥75 intensity" accent="red"/>
        <Metric label="Peak Jurisdiction" val="Canada" sub="91/100 intensity" accent="gold"/>
        <Metric label="Practice Overlap" val="M&A + Reg" sub="top cross-border need" accent="green"/>
      </div>
      <Panel title="Legal Demand by Jurisdiction" style={{ marginBottom: 12 }}>
        <div style={{ padding: "16px", position: "relative" }}>
          <svg viewBox="0 0 900 420" style={{ width: "100%", height: "auto", background: "transparent" }}>
            <path d="M80,80 L280,80 L310,120 L290,180 L250,220 L180,230 L140,200 L100,160 L80,120 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            <path d="M180,250 L240,245 L255,290 L250,360 L220,390 L195,380 L170,340 L160,290 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            <path d="M390,90 L480,85 L490,140 L470,165 L440,160 L400,145 L385,120 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            <path d="M400,175 L470,170 L490,200 L485,300 L460,340 L430,340 L405,310 L390,260 L395,210 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            <path d="M490,180 L560,175 L565,225 L545,240 L510,235 L488,215 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            <path d="M565,80 L760,75 L775,140 L760,190 L730,210 L700,200 L660,215 L630,210 L600,200 L570,175 L555,140 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            <path d="M650,270 L760,265 L775,310 L760,360 L720,370 L685,360 L660,330 L645,300 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            {GEO.map(g => {
              const c = intCol(g.v);
              const isSelected = sel.id === g.id;
              return (
                <g key={g.id} onClick={() => { setSel(g); setBrief(""); }} style={{ cursor: "pointer" }}>
                  <circle cx={g.x} cy={g.y} r={isSelected ? 22 : 16} fill={`${c}18`} stroke={`${c}40`} strokeWidth="1">
                    {isSelected && <animate attributeName="r" values="16;22;16" dur="2s" repeatCount="indefinite"/>}
                  </circle>
                  <circle cx={g.x} cy={g.y} r={isSelected ? 9 : 7} fill={c} opacity={isSelected ? 1 : 0.85}/>
                  <text x={g.x} y={g.y + 22} textAnchor="middle" fill="var(--color-on-surface-variant)" fontSize="9" fontFamily="var(--font-mono)">{g.label}</text>
                  <text x={g.x} y={g.y + 4} textAnchor="middle" fill="var(--color-on-primary)" fontSize="8" fontFamily="var(--font-mono)" fontWeight="600">{g.v}</text>
                </g>
              )
            })}
          </svg>
        </div>
      </Panel>
      <div className="geo-grid-2">
        <Panel title={`${sel.label} — Jurisdiction Intelligence`}>
          <div style={{ padding: "14px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <div>
                <div className="geo-detail-title">{sel.label}</div>
                <Tag label={sel.practice} color="blue"/>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="geo-detail-val" style={{ color: intCol(sel.v) }}>{sel.v}</div>
                <div className="geo-detail-sub">DEMAND INDEX</div>
              </div>
            </div>
            <SBar s={sel.v} color={intCol(sel.v)}/>
            <div style={{ marginTop: 14, padding: "10px 12px", background: "var(--color-surface-container-low)", borderRadius: 3 }}>
              <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 6 }}>KEY DRIVERS</div>
              <div style={{ fontSize: 12, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-data)", lineHeight: 1.6 }}>{sel.drivers}</div>
            </div>
          </div>
        </Panel>
        <Panel title="AI Market Intelligence Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Brief"}</OBtn></div>}>
          <div style={{ padding: "14px 16px" }}>
            {loading ? <Spinner/> : brief ? <div className="geo-brief-box">{brief}</div> : <div className="geo-brief-empty">Select a jurisdiction to generate a tactical brief.</div>}
          </div>
        </Panel>
      </div>
    </div>
  )
}

/* ── 2. JET TRACKER ─────────────────────────────────────────────────────── */
export const JetTracker = () => {
  const [sel, setSel] = useState(JETS[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const sc = c => c >= 80 ? "var(--color-error)" : c >= 65 ? "var(--color-warning)" : "var(--color-secondary)";

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const token = sessionStorage.getItem('bdforlaw_token')
      const r = await fetch(`/api/v1/signals?signal_type=geo_flight_corporate_jet&limit=10`, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) throw new Error(`${r.status}`)
      const data = await r.json()
      const list = Array.isArray(data) ? data : []
      setBrief(list.length > 0 ? list.slice(0, 5).map(s => `• ${s.raw_company_name || 'Unknown'}: ${s.signal_text?.slice(0, 80) || 'Jet movement detected'}`).join('\\n') : 'No corporate jet signals yet.')
    } catch (e) { setBrief("API error.") }
    setLoading(false);
  }

  return (
    <div className="geo-page-root">
      <PageHeader tag="Geospatial Intelligence" title="Corporate Jet Tracker" sub="Monitors public ADS-B transponder signals to predict M&A mandates."/>
      <div className="geo-grid-4">
        <Metric label="Active Tracks" val={JETS.length} accent="blue"/>
        <Metric label="High Confidence" val={JETS.filter(j => j.conf >= 75).length} accent="red"/>
        <Metric label="Est. Total Value" val="$2.6M" accent="gold"/>
        <Metric label="Avg Days to Close" val="14–28" accent="green"/>
      </div>
      <div className="geo-grid-sidebar" style={{ gridTemplateColumns: '320px 1fr' }}>
        <Panel>
          <div className="geo-list-header">SORTED BY CONFIDENCE</div>
          {JETS.sort((a, b) => b.conf - a.conf).map((j, i) => (
            <div key={i} onClick={() => { setSel(j); setBrief(""); }} className={`geo-list-item ${sel.co === j.co ? 'active' : ''}`}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <div className="geo-item-title">{j.co}</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 17, fontWeight: 700, color: sc(j.conf) }}>{j.conf}%</div>
              </div>
              <div className="geo-item-meta">✈ {j.from} → {j.to}</div>
              <div style={{ display: "flex", gap: 5 }}>
                <Tag label={j.mandate} color="gold"/>
                <Tag label={j.tail} color="default"/>
              </div>
            </div>
          ))}
        </Panel>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Panel>
            <div style={{ padding: "16px 18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
                <div>
                  <div className="geo-detail-title">{sel.co}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <Tag label={sel.mandate} color="red"/>
                    <Tag label={sel.tail} color="blue"/>
                    <Tag label={sel.exec} color="default"/>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="geo-detail-val" style={{ color: sc(sel.conf) }}>{sel.conf}%</div>
                  <div className="geo-detail-sub">CONFIDENCE</div>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, padding: "12px 0", borderTop: "1px solid var(--color-outline-variant)" }}>
                {[["Route", `${sel.from} → ${sel.to}`], ["Detected", sel.date], ["Relationship", `${sel.warmth}/100`]].map(([l, v]) => (
                  <div key={l}>
                    <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 3 }}>{l}</div>
                    <div style={{ fontSize: 12, color: "var(--color-on-surface)", fontFamily: "var(--font-data)", fontWeight: 500 }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>
          <Panel title="AI Tactical Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Brief"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : brief ? <div className="geo-brief-box">{brief}</div> : <div className="geo-brief-empty">Generate a tactical action brief based on jet travel.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

/* ── 3. FOOT TRAFFIC ────────────────────────────────────────────────────── */
export const FootTraffic = () => {
  const [sel, setSel] = useState(FOOT[0]);
  const [resp, setResp] = useState("");
  const [loading, setLoading] = useState(false);
  const sc = s => ({ critical: "var(--color-error)", high: "var(--color-warning)", medium: "var(--color-secondary)", low: "var(--color-success)" }[s] || "var(--color-on-surface-variant)");

  async function gen() {
    setLoading(true); setResp("");
    try {
      const token = sessionStorage.getItem('bdforlaw_token')
      const r = await fetch(`/api/v1/signals?category=geo&limit=10`, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) throw new Error(`${r.status}`)
      const data = await r.json()
      const list = Array.isArray(data) ? data : []
      setResp(list.length > 0 ? list.slice(0, 5).map(s => `• ${s.raw_company_name || 'Company'}: ${s.signal_text?.slice(0, 80) || 'Activity detected'}`).join('\\n') : 'No foot traffic signals yet.')
    } catch (e) { setResp("API error.") }
    setLoading(false);
  }

  return (
    <div className="geo-page-root">
      <PageHeader tag="Geospatial Intelligence" title="Foot Traffic Intelligence" sub="Detects when your clients visit competitor law firms."/>
      <div className="geo-grid-4">
        <Metric label="Active Detections" val={FOOT.length} accent="red"/>
        <Metric label="Critical Threats" val={FOOT.filter(f => f.sev === "critical").length} accent="red"/>
        <Metric label="Revenue at Risk" val="$2.3M" accent="gold"/>
        <Metric label="Locations Monitored" val="47" accent="blue"/>
      </div>
      <div className="geo-grid-2">
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {FOOT.map((f, i) => {
            const c = sc(f.sev);
            const isSelected = sel.target === f.target;
            return (
              <div key={i} onClick={() => { setSel(f); setResp(""); }} style={{ background: isSelected ? `${c}08` : "var(--color-surface-container-lowest)", border: `1px solid ${isSelected ? `${c}35` : "var(--color-surface-container-high)"}`, borderLeft: `3px solid ${c}`, borderRadius: 4, padding: "14px 16px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, color: "var(--color-on-surface)", fontFamily: "var(--font-data)" }}>{f.target}</div>
                  <span style={{ fontSize: 8, fontFamily: "var(--font-mono)", background: `${c}18`, border: `1px solid ${c}35`, color: c, padding: "2px 7px", borderRadius: 2 }}>{f.sev.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: 11, color: c, fontFamily: "var(--font-mono)", marginBottom: 6 }}>📍 {f.loc}</div>
                <div style={{ display: "flex", gap: 10, marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-data)" }}>📱 {f.dev} devices</div>
                  <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-data)" }}>⏳ {f.dur}</div>
                </div>
                <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", padding: "8px 10px", background: "var(--color-surface-container-low)" }}>
                  <span style={{ color: "var(--color-on-surface-variant)", fontSize: 9, fontFamily: "var(--font-mono)" }}>THREAT: </span><span style={{ fontFamily: "var(--font-data)" }}>{f.threat}</span>
                </div>
              </div>
            )
          })}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Panel title="AI Counter-Strategy" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Strategy"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : resp ? <div className="geo-brief-box">{resp}</div> : <div className="geo-brief-empty">Generate a counter-strategy for this detection.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

/* ── 4. SATELLITE ───────────────────────────────────────────────────────── */
export const Satellite = () => {
  const [sel, setSel] = useState(SAT[0]);
  const [analysis, setAnalysis] = useState("");
  const [loading, setLoading] = useState(false);
  const uc = u => ({ high: "var(--color-error)", medium: "var(--color-warning)", low: "var(--color-success)" }[u] || "var(--color-secondary)");
  const tc = { "Workforce": "red", "Construction": "blue", "Supply Chain": "gold", "Environmental": "green" };

  async function gen() {
    setLoading(true); setAnalysis("");
    try {
      const token = sessionStorage.getItem('bdforlaw_token')
      const r = await fetch(`/api/v1/signals?category=geo&limit=10`, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) throw new Error(`${r.status}`)
      const data = await r.json()
      const list = Array.isArray(data) ? data : []
      setAnalysis(list.length > 0 ? list.slice(0, 5).map(s => `• ${s.raw_company_name || 'Company'}: ${s.signal_type || 'signal'}`).join('\\n') : 'No satellite signals yet.')
    } catch (e) { setAnalysis("API error.") }
    setLoading(false);
  }

  return (
    <div className="geo-page-root">
      <PageHeader tag="Geospatial Intelligence" title="Satellite Signal Intelligence" sub="Commercial satellite imagery to detect construction anomalies before public disclosure."/>
      <div className="geo-grid-4">
        <Metric label="Active Signals" val={SAT.length} accent="blue"/>
        <Metric label="High Urgency" val={SAT.filter(s => s.urg === "high").length} accent="red"/>
        <Metric label="Avg Confidence" val={`${Math.round(SAT.reduce((s, i) => s + i.conf, 0) / SAT.length)}%`} accent="gold"/>
        <Metric label="Est. Pipeline" val="$960K" accent="green"/>
      </div>
      <div className="geo-grid-sidebar" style={{ gridTemplateColumns: '320px 1fr' }}>
        <Panel>
          {SAT.map((s, i) => {
            const c = uc(s.urg);
            return (
              <div key={i} onClick={() => { setSel(s); setAnalysis(""); }} className={`geo-list-item ${sel.co === s.co ? 'active' : ''}`}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                  <div className="geo-item-title">{s.co}</div>
                  <Tag label={s.type} color={tc[s.type] || "default"}/>
                </div>
                <div className="geo-item-meta">📍 {s.loc}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 8, fontFamily: "var(--font-mono)", color: c, background: `${c}15`, border: `1px solid ${c}30`, padding: "2px 6px", borderRadius: 2 }}>{s.urg.toUpperCase()}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700, color: c }}>{s.conf}%</span>
                </div>
              </div>
            )
          })}
        </Panel>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Panel>
            <div style={{ padding: "16px 18px" }}>
              <div className="geo-detail-title">{sel.co}</div>
              <div style={{ fontSize: 12, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-data)", marginBottom: 12 }}>{sel.sig}</div>
              <div style={{ background: "rgba(212,168,67,.04)", border: "1px solid rgba(212,168,67,.2)", borderRadius: 3, padding: "10px 12px" }}>
                <div style={{ fontSize: 9, color: "var(--color-secondary)", fontFamily: "var(--font-mono)", marginBottom: 5 }}>LEGAL INFERENCE</div>
                <div style={{ fontSize: 12, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-data)", lineHeight: 1.6 }}>{sel.inf}</div>
              </div>
            </div>
          </Panel>
          <Panel title="AI Legal Exposure Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Assess Exposure"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : analysis ? <div className="geo-brief-box">{analysis}</div> : <div className="geo-brief-empty">Generate a legal exposure brief for this observation.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

/* ── 5. PERMIT RADAR ────────────────────────────────────────────────────── */
export const PermitRadar = () => {
  const [sel, setSel] = useState(PERMITS[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const uc = u => ({ high: "var(--color-error)", medium: "var(--color-secondary)", low: "var(--color-success)" }[u] || "var(--color-primary)");

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const token = sessionStorage.getItem('bdforlaw_token')
      const r = await fetch(`/api/v1/signals?signal_type=geo_municipal_permit_issued&limit=10`, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) throw new Error(`${r.status}`)
      const data = await r.json()
      const list = Array.isArray(data) ? data : []
      setBrief(list.length > 0 ? list.slice(0, 5).map(s => `• ${s.raw_company_name || 'Applicant'}: ${s.signal_text?.slice(0, 100) || 'Permit filed'}`).join('\\n') : 'No permit signals yet.')
    } catch (e) { setBrief("API error.") }
    setLoading(false);
  }

  return (
    <div className="geo-page-root">
      <PageHeader tag="Geospatial Intelligence" title="Permit Radar" sub="Aggregates construction and demolition permits to trigger real estate and restructuring."/>
      <div className="geo-grid-4">
        <Metric label="Active Permits" val={PERMITS.length} accent="blue"/>
        <Metric label="High Urgency" val={PERMITS.filter(p => p.urg === "high").length} accent="red"/>
        <Metric label="Est. Fee Value" val={`$${(PERMITS.reduce((s, p) => s + parseInt(p.rev.replace(/\\$|K/g, "")), 0))}K`} accent="gold"/>
        <Metric label="Unmatched Prospects" val={PERMITS.filter(p => !p.lead).length} accent="green"/>
      </div>
      <div className="geo-grid-sidebar" style={{ gridTemplateColumns: '320px 1fr' }}>
        <Panel>
          <div className="geo-list-header">SORTED BY URGENCY</div>
          {PERMITS.sort((a, b) => a.urg === "high" ? -1 : 1).map((p, i) => (
            <div key={i} onClick={() => { setSel(p); setBrief(""); }} className={`geo-list-item ${sel.co === p.co ? 'active' : ''}`}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <div className="geo-item-title">{p.co}</div>
                <span style={{ fontSize: 8, background: `${uc(p.urg)}18`, color: uc(p.urg), padding: "2px 6px", borderRadius: 2, fontFamily: "var(--font-mono)" }}>{p.urg.toUpperCase()}</span>
              </div>
              <div className="geo-item-meta">{p.permit}</div>
            </div>
          ))}
        </Panel>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Panel>
            <div style={{ padding: "16px 18px" }}>
               <div className="geo-detail-title">{sel.co}</div>
               <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-data)", marginBottom: 12 }}>{sel.loc} · Filed {sel.filed}</div>
               <div style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-outline-variant)", borderRadius: 3, padding: "12px 14px", marginBottom: 12 }}>
                 <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 5 }}>PERMIT TYPE</div>
                 <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-on-surface)", fontFamily: "var(--font-data)", marginBottom: 4 }}>{sel.permit}</div>
                 <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-data)" }}>{sel.type}</div>
               </div>
            </div>
          </Panel>
          <Panel title="AI Outreach Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Brief"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : brief ? <div className="geo-brief-box">{brief}</div> : <div className="geo-brief-empty">Generate an outreach brief.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

/* ── Wrapper ────────────────────────────────────────────────────────────── */
const GEO_TABS = [
  { key: 'heatmap',  label: 'Mandate Heat Map', Component: GeoMap },
  { key: 'jets',     label: 'Jet Tracker',       Component: JetTracker },
  { key: 'foot',     label: 'Foot Traffic',      Component: FootTraffic },
  { key: 'sat',      label: 'Satellite Intel',   Component: Satellite },
  { key: 'permits',  label: 'Permit Radar',      Component: PermitRadar },
]

export default function GeoPagesWrapper() {
  injectCSS()
  const [tab, setTab] = useState('heatmap')
  const active = GEO_TABS.find(t => t.key === tab) || GEO_TABS[0]

  return (
    <AppShell>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{
          display: 'flex', gap: 4, padding: '12px 20px',
          background: 'var(--color-surface-container-low)',
          borderBottom: '1px solid rgba(197,198,206,0.15)',
        }}>
          {GEO_TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{
              padding: '6px 16px', borderRadius: 'var(--radius-md)',
              fontFamily: 'var(--font-data)', fontSize: '0.75rem', fontWeight: 700,
              letterSpacing: '0.04em', cursor: 'pointer', border: 'none',
              background: tab === t.key ? 'var(--color-surface-container-lowest)' : 'transparent',
              color: tab === t.key ? 'var(--color-on-surface)' : 'var(--color-on-surface-variant)',
              boxShadow: tab === t.key ? 'var(--shadow-ambient)' : 'none',
              transition: 'background 150ms ease-out',
            }}>
              {t.label}
            </button>
          ))}
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <active.Component />
        </div>
      </div>
    </AppShell>
  )
}
