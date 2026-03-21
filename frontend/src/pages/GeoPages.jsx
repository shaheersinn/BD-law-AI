import * as apiClient from "../api/client.js";
// src/pages/GeoPages.jsx
// Five geospatial intelligence modules:
// GeoMap · JetTracker · FootTraffic · Satellite · PermitRadar

import { useState } from "react";

/* ─── Shared primitives (inlined so this file is self-contained) ─────────── */
const Tag = ({ label, color = "default" }) => {
  const map = {
    default: { bg: "rgba(106,137,180,.1)", br: "rgba(106,137,180,.25)", tx: "var(--t2)" },
    red:     { bg: "rgba(224,82,82,.1)",   br: "rgba(224,82,82,.3)",    tx: "var(--red)" },
    gold:    { bg: "rgba(212,168,67,.1)",  br: "rgba(212,168,67,.3)",   tx: "var(--gold)" },
    green:   { bg: "rgba(61,186,122,.1)",  br: "rgba(61,186,122,.3)",   tx: "var(--green)" },
    blue:    { bg: "rgba(74,143,255,.1)",  br: "rgba(74,143,255,.3)",   tx: "#7fb3ff" },
    cyan:    { bg: "rgba(34,201,212,.1)",  br: "rgba(34,201,212,.3)",   tx: "var(--cyan)" },
    purple:  { bg: "rgba(155,109,255,.1)", br: "rgba(155,109,255,.3)",  tx: "var(--purple)" },
  };
  const s = map[color] || map.default;
  return (
    <span style={{
      background: s.bg, border: `1px solid ${s.br}`, color: s.tx,
      fontSize: 9, fontFamily: "'JetBrains Mono',monospace", letterSpacing: ".07em",
      padding: "2px 8px", borderRadius: 2, whiteSpace: "nowrap",
    }}>{label}</span>
  );
};

const Dot = ({ c, pulse }) => (
  <span style={{
    width: 7, height: 7, borderRadius: "50%", background: c,
    display: "inline-block", flexShrink: 0,
    animation: pulse ? "pulse 2s ease-in-out infinite" : "",
  }}/>
);

const SBar = ({ s, color }) => {
  const c = color || (s >= 75 ? "#e05252" : s >= 50 ? "#e07c30" : s >= 30 ? "#d4a843" : "#3dba7a");
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 3, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${s}%`, height: "100%", background: c, borderRadius: 2, transition: "width .8s ease" }}/>
      </div>
      <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: c, width: 26, textAlign: "right" }}>{s}</span>
    </div>
  );
};

const Panel = ({ title, children, actions, style = {} }) => (
  <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4, ...style }}>
    {title && (
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: "var(--t2)", letterSpacing: ".08em", textTransform: "uppercase" }}>{title}</span>
        {actions}
      </div>
    )}
    {children}
  </div>
);

const Metric = ({ label, val, sub, accent = "gold" }) => {
  const cols = { gold: "var(--gold)", red: "var(--red)", green: "var(--green)", blue: "var(--blue)", purple: "var(--purple)", cyan: "var(--cyan)" };
  return (
    <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 4, padding: "16px 18px", position: "relative", overflow: "hidden" }}>
      <div style={{ fontSize: 9, fontFamily: "'JetBrains Mono',monospace", color: "var(--t3)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 26, fontWeight: 600, color: cols[accent] || "var(--t1)", lineHeight: 1 }}>{val}</div>
      {sub && <div style={{ marginTop: 6, fontSize: 10, color: "var(--t3)" }}>{sub}</div>}
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 2, background: cols[accent] || "var(--t1)", opacity: .3 }}/>
    </div>
  );
};

const PageHeader = ({ tag, title, sub }) => (
  <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: "1px solid var(--border)" }}>
    {tag && <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: "var(--gold)", letterSpacing: ".14em", marginBottom: 6, textTransform: "uppercase" }}>◈ {tag}</div>}
    <h1 style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 22, letterSpacing: "-.03em", marginBottom: 4, color: "var(--t1)" }}>{title}</h1>
    {sub && <p style={{ color: "var(--t2)", fontSize: 12, lineHeight: 1.6 }}>{sub}</p>}
  </div>
);

const OBtn = ({ children, onClick, disabled, secondary, small }) => (
  <button onClick={onClick} disabled={disabled} style={{
    padding: small ? "5px 12px" : "7px 16px", borderRadius: 3,
    fontFamily: "'JetBrains Mono',monospace", fontSize: 10, fontWeight: 500,
    letterSpacing: ".06em", textTransform: "uppercase",
    border: secondary ? "1px solid var(--border2)" : "none",
    background: secondary ? "transparent" : disabled ? "rgba(212,168,67,.2)" : "var(--gold)",
    color: secondary ? "var(--t2)" : disabled ? "var(--golddim)" : "#04080f",
    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? .6 : 1,
  }}>{children}</button>
);

const AiBadge = () => <Tag label="◈ AI" color="gold"/>;

const Spinner = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--t3)", fontSize: 11, fontFamily: "'JetBrains Mono',monospace" }}>
    <div style={{ width: 13, height: 13, border: "2px solid var(--border2)", borderTopColor: "var(--gold)", borderRadius: "50%", animation: "spin .7s linear infinite" }}/>
    Processing…
  </div>
);

/* ─── Data ───────────────────────────────────────────────────────────────── */
const GEO = [
  { id: "can", label: "Canada",    x: 195, y: 112, v: 91, practice: "M&A + Regulatory",       drivers: "OSC enforcement wave, energy transition mandates, Indigenous consultation law" },
  { id: "usa", label: "USA",       x: 188, y: 172, v: 88, practice: "Securities + Litigation", drivers: "DOJ tech enforcement, climate litigation, cross-border M&A clearance" },
  { id: "eu",  label: "EU",        x: 448, y: 148, v: 79, practice: "Regulatory + Data",       drivers: "EU AI Act enforcement, CSRD mandates, antitrust wave" },
  { id: "uk",  label: "UK",        x: 420, y: 134, v: 72, practice: "Finance + Sanctions",     drivers: "Post-Brexit disputes, OFSI sanctions compliance, crypto regulation" },
  { id: "uae", label: "UAE",       x: 552, y: 214, v: 68, practice: "Arbitration + M&A",       drivers: "DIFC arbitration surge, sovereign wealth structuring" },
  { id: "aus", label: "Australia", x: 698, y: 312, v: 61, practice: "Mining + Environmental",  drivers: "Critical minerals law, native title litigation, ESG disclosure" },
  { id: "sgp", label: "Singapore", x: 670, y: 250, v: 74, practice: "Dispute + Finance",       drivers: "Fintech disputes, family office structuring, supply chain arbitration" },
  { id: "ind", label: "India",     x: 610, y: 222, v: 66, practice: "Corporate + Arbitration", drivers: "FDI disputes, infrastructure arbitration, data localisation" },
  { id: "jpn", label: "Japan",     x: 715, y: 172, v: 63, practice: "M&A + IP",                drivers: "Inbound M&A, semiconductor IP disputes, carbon credit structuring" },
];

const JETS = [
  { co: "Arctis Mining Corp",      tail: "C-FMTX", exec: "CEO Marcus Reid",   from: "Calgary YYC",     to: "Toronto Billy Bishop", date: "Nov 14 · 09:22", sig: "3rd Bay Street trip in 10 days",          mandate: "M&A — Sell-Side",       conf: 91, warmth: 18 },
  { co: "Stellex Infrastructure",  tail: "C-GXLP", exec: "CFO Jana Obi",      from: "Toronto Pearson", to: "New York JFK",         date: "Nov 13 · 14:05", sig: "2nd NYC trip — Lazard HQ proximate",      mandate: "Fund Restructuring",    conf: 74, warmth: 44 },
  { co: "Vesta Retail REIT",       tail: "C-HRTV", exec: "CEO + COO",         from: "Toronto YYZ",     to: "Vancouver YVR",        date: "Nov 12 · 07:44", sig: "Unscheduled — no investor event listed",  mandate: "Asset Sale",            conf: 68, warmth: 5  },
  { co: "Caldwell Steel Works",    tail: "N821PW",  exec: "Board Chair",       from: "Detroit DTW",     to: "Hamilton YHM",         date: "Nov 11 · 16:30", sig: "Same-day return — restructuring counsel", mandate: "Insolvency / CCAA",     conf: 55, warmth: 12 },
  { co: "Borealis Genomics",       tail: "C-FVXQ", exec: "CFO + VP BD",       from: "Waterloo YKF",    to: "Boston BOS",           date: "Nov 10 · 08:15", sig: "3rd Boston trip — Kendall Square biotech", mandate: "Series C / Licensing",  conf: 62, warmth: 38 },
];

const FOOT = [
  { target: "Aurelia Capital Group",  loc: "Davies Ward Phillips — 155 Wellington St W", dev: 14, dur: "2.5 hrs avg", date: "Nov 13", threat: "RFP or active pitch in progress at rival firm",              sev: "critical", action: "Counter-pitch today. Use conflict arbitrage angle — Davies has CIBC retainer." },
  { target: "Meridian Logistics",     loc: "Blake Cassels CLE event space",              dev: 6,  dur: "Full day",     date: "Nov 12", threat: "Competitor relationship-building CLE event",                 sev: "high",     action: "M. Webb to arrange direct 1:1 with GC this week before Blake creates loyalty." },
  { target: "Centurion Pharma",       loc: "Osler offices — 100 King St W",              dev: 8,  dur: "3.1 hrs avg",  date: "Nov 10", threat: "Potential mandate evaluation — multiple visits in 21 days",  sev: "high",     action: "D. Park to call Deputy GC immediately. IP matter is vulnerable." },
  { target: "Vantage Rail Corp",      loc: "Transport Canada Ottawa HQ",                 dev: 22, dur: "All day",       date: "Nov 09", threat: "Regulatory examination — personnel on-site all day",         sev: "medium",   action: "Regulatory audit likely. Offer pre-response counsel before file opens." },
];

const SAT = [
  { co: "Caldwell Steel Works",   loc: "Hamilton, ON",        sig: "Parking lot occupancy: 94% → 31% over 4 weeks",          inf: "Mass layoff forming — employment law mandate imminent within 2–3 weeks",         conf: 88, type: "Workforce",     urg: "high",   lead: null },
  { co: "Northfield Energy",      loc: "Fort McMurray, AB",   sig: "Excavation equipment appeared at previously idle pad",     inf: "Capital project resuming — construction, environmental, financing counsel needed", conf: 76, type: "Construction", urg: "medium", lead: "J. Okafor" },
  { co: "Arctis Mining Corp",     loc: "Timmins, ON",         sig: "Shipping container accumulation +340% vs 12-month avg",    inf: "Supply chain disruption or shutdown preparation — restructuring signal",         conf: 71, type: "Supply Chain", urg: "medium", lead: null },
  { co: "Unknown Industrial",     loc: "Sarnia, ON corridor", sig: "Thermal plume detected — 3.2 km NE drift from facility",   inf: "Environmental violation pre-enforcement — call before regulator does",          conf: 83, type: "Environmental", urg: "high",   lead: null },
  { co: "Borealis Genomics",      loc: "Waterloo, ON",        sig: "Structural steel erected — new building footprint visible", inf: "Lab expansion confirmed — construction, employment, IP licensing counsel",       conf: 91, type: "Construction", urg: "low",    lead: "D. Park" },
];

const PERMITS = [
  { co: "Northfield Energy Partners", permit: "Environmental Assessment Application", loc: "Fort McMurray, AB",   filed: "Nov 10", type: "New pipeline — 480 km corridor",        work: ["Environmental", "Indigenous", "Regulatory"],         urg: "high",   rev: "$420K", lead: "J. Okafor" },
  { co: "Unknown Applicant",          permit: "Demolition Permit — Class A tower",   loc: "King & Bay, Toronto", filed: "Nov 08", type: "Full commercial tower demolition",        work: ["Real Estate", "Construction", "Lender Counsel"],      urg: "medium", rev: "$180K", lead: null },
  { co: "Borealis Genomics",          permit: "Building Permit — Lab expansion",     loc: "Waterloo Research Park", filed: "Nov 06", type: "22,000 sq ft R&D facility",          work: ["Construction", "Employment", "IP Licensing"],         urg: "medium", rev: "$140K", lead: "D. Park" },
  { co: "Caldwell Steel Works",       permit: "Change of Use — Industrial to Storage", loc: "Hamilton, ON",      filed: "Nov 03", type: "Major facility conversion + rezoning",    work: ["Restructuring", "Real Estate", "Environmental"],      urg: "high",   rev: "$220K", lead: null },
  { co: "Stellex Infrastructure",     permit: "Environmental Impact Assessment",     loc: "Kitchener-Waterloo",  filed: "Oct 28", type: "Solar farm — 1,200 acres",               work: ["Environmental", "Land Use", "Indigenous", "Finance"], urg: "medium", rev: "$310K", lead: "J. Okafor" },
];

/* ─── 1. GEOPOLITICAL MANDATE HEAT MAP ───────────────────────────────────── */
export const GeoMap = () => {
  const [sel, setSel] = useState(GEO[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);

  const intCol = v => v >= 80 ? "#e05252" : v >= 65 ? "#e07c30" : v >= 50 ? "#d4a843" : "#4a8fff";

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 600,
          messages: [{ role: "user", content: `BigLaw BD AI. Write a 130-word market intelligence brief for a Canadian law firm considering a BD push into ${sel.label}.\n\nCurrent legal demand index: ${sel.v}/100\nTop practice areas: ${sel.practice}\nKey drivers: ${sel.drivers}\n\nProvide: (1) The single highest-value opportunity for a Canadian firm right now (2) Which existing client relationships have cross-border exposure here (3) One concrete BD action this quarter — event, thought leadership, or referral network to activate. Plain text, direct, no headers.` }]
        })
      });
      const d = await r.json(); setBrief(d.content?.[0]?.text || "Error.");
    } catch { setBrief("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Geopolitical Intelligence" title="Mandate Heat Map" sub="Legal demand intensity by jurisdiction, driven by regulatory enforcement waves, political risk, macroeconomic signals, and your firm's historical matter distribution."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Jurisdictions Tracked" val={GEO.length} sub="active monitors" accent="blue"/>
        <Metric label="High Demand" val={GEO.filter(g => g.v >= 75).length} sub="≥75 intensity" accent="red"/>
        <Metric label="Peak Jurisdiction" val="Canada" sub="91/100 intensity" accent="gold"/>
        <Metric label="Practice Overlap" val="M&A + Reg" sub="top cross-border need" accent="green"/>
      </div>

      {/* SVG World Map */}
      <Panel title="Legal Demand by Jurisdiction — Click to Drill Down" style={{ marginBottom: 12 }}>
        <div style={{ padding: "16px", position: "relative" }}>
          <svg viewBox="0 0 900 420" style={{ width: "100%", height: "auto", background: "transparent" }}>
            {/* Simplified continent outlines */}
            {/* North America */}
            <path d="M80,80 L280,80 L310,120 L290,180 L250,220 L180,230 L140,200 L100,160 L80,120 Z" fill="rgba(26,40,64,.6)" stroke="var(--border2)" strokeWidth="1"/>
            {/* South America */}
            <path d="M180,250 L240,245 L255,290 L250,360 L220,390 L195,380 L170,340 L160,290 Z" fill="rgba(26,40,64,.6)" stroke="var(--border2)" strokeWidth="1"/>
            {/* Europe */}
            <path d="M390,90 L480,85 L490,140 L470,165 L440,160 L400,145 L385,120 Z" fill="rgba(26,40,64,.6)" stroke="var(--border2)" strokeWidth="1"/>
            {/* Africa */}
            <path d="M400,175 L470,170 L490,200 L485,300 L460,340 L430,340 L405,310 L390,260 L395,210 Z" fill="rgba(26,40,64,.6)" stroke="var(--border2)" strokeWidth="1"/>
            {/* Middle East */}
            <path d="M490,180 L560,175 L565,225 L545,240 L510,235 L488,215 Z" fill="rgba(26,40,64,.6)" stroke="var(--border2)" strokeWidth="1"/>
            {/* Asia */}
            <path d="M565,80 L760,75 L775,140 L760,190 L730,210 L700,200 L660,215 L630,210 L600,200 L570,175 L555,140 Z" fill="rgba(26,40,64,.6)" stroke="var(--border2)" strokeWidth="1"/>
            {/* Australia */}
            <path d="M650,270 L760,265 L775,310 L760,360 L720,370 L685,360 L660,330 L645,300 Z" fill="rgba(26,40,64,.6)" stroke="var(--border2)" strokeWidth="1"/>

            {/* Jurisdiction dots */}
            {GEO.map(g => {
              const c = intCol(g.v);
              const isSelected = sel.id === g.id;
              return (
                <g key={g.id} onClick={() => { setSel(g); setBrief(""); }} style={{ cursor: "pointer" }}>
                  {/* Pulse ring */}
                  <circle cx={g.x} cy={g.y} r={isSelected ? 22 : 16} fill={`${c}18`} stroke={`${c}40`} strokeWidth="1">
                    {isSelected && <animate attributeName="r" values="16;22;16" dur="2s" repeatCount="indefinite"/>}
                  </circle>
                  {/* Core dot */}
                  <circle cx={g.x} cy={g.y} r={isSelected ? 9 : 7} fill={c} opacity={isSelected ? 1 : 0.85}/>
                  {/* Label */}
                  <text x={g.x} y={g.y + 22} textAnchor="middle" fill="var(--t2)" fontSize="9" fontFamily="'JetBrains Mono',monospace">{g.label}</text>
                  {/* Score */}
                  <text x={g.x} y={g.y + 4} textAnchor="middle" fill="#fff" fontSize="8" fontFamily="'JetBrains Mono',monospace" fontWeight="600">{g.v}</text>
                </g>
              );
            })}

            {/* Legend */}
            {[{ c: "#e05252", l: "High ≥80" }, { c: "#e07c30", l: "Med-High 65-79" }, { c: "#d4a843", l: "Medium 50-64" }, { c: "#4a8fff", l: "Emerging <50" }].map((item, i) => (
              <g key={i} transform={`translate(${620 + i * 0}, ${370 + i * 14})`}>
                <circle cx="6" cy="6" r="4" fill={item.c}/>
                <text x="14" y="10" fill="var(--t3)" fontSize="8" fontFamily="'JetBrains Mono',monospace">{item.l}</text>
              </g>
            ))}
          </svg>
        </div>
      </Panel>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Selected jurisdiction detail */}
        <Panel title={`${sel.label} — Jurisdiction Intelligence`}>
          <div style={{ padding: "14px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <div style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 20, color: "var(--t1)", marginBottom: 6 }}>{sel.label}</div>
                <Tag label={sel.practice} color="blue"/>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 44, fontWeight: 700, color: intCol(sel.v), lineHeight: 1 }}>{sel.v}</div>
                <div style={{ fontSize: 8, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>DEMAND INDEX</div>
              </div>
            </div>
            <SBar s={sel.v} color={intCol(sel.v)}/>
            <div style={{ marginTop: 14, padding: "10px 12px", background: "var(--elevated)", borderRadius: 3, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 6 }}>KEY DRIVERS</div>
              <div style={{ fontSize: 12, color: "var(--t2)", lineHeight: 1.6 }}>{sel.drivers}</div>
            </div>
          </div>
        </Panel>

        {/* AI Brief */}
        <Panel title="AI Market Intelligence Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Brief"}</OBtn></div>}>
          <div style={{ padding: "14px 16px" }}>
            {loading ? <Spinner/> : brief
              ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--t2)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{brief}</div>
              : <div style={{ fontSize: 11, color: "var(--t3)", fontStyle: "italic" }}>Select a jurisdiction on the map, then generate a market intelligence brief — opportunity analysis, cross-border exposure, and one concrete BD action for this quarter.</div>}
          </div>
        </Panel>
      </div>

      {/* Jurisdiction ranking table */}
      <Panel title="All Jurisdictions — Demand Ranking" style={{ marginTop: 12 }}>
        <div style={{ padding: "10px 14px" }}>
          {[...GEO].sort((a, b) => b.v - a.v).map((g, i) => (
            <div key={g.id} onClick={() => { setSel(g); setBrief(""); }}
              style={{ display: "grid", gridTemplateColumns: "24px 1fr 180px 60px", gap: 12, alignItems: "center", padding: "9px 10px", borderBottom: "1px solid var(--border)", cursor: "pointer", borderRadius: 3, background: sel.id === g.id ? "var(--elevated)" : "transparent" }}>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: "var(--t3)" }}>{i + 1}</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--t1)" }}>{g.label}</div>
                <div style={{ fontSize: 10, color: "var(--t3)" }}>{g.practice}</div>
              </div>
              <SBar s={g.v} color={intCol(g.v)}/>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 16, fontWeight: 700, color: intCol(g.v), textAlign: "right" }}>{g.v}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
};

/* ─── 2. CORPORATE JET TRACKER ───────────────────────────────────────────── */
export const JetTracker = () => {
  const [sel, setSel] = useState(JETS[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const sc = c => c >= 80 ? "#e05252" : c >= 65 ? "#e07c30" : "#d4a843";

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 500,
          messages: [{ role: "user", content: `BigLaw M&A BD. A corporate jet track has fired a mandate signal.\n\nCompany: ${sel.co}\nAircraft: ${sel.tail}\nExecutive: ${sel.exec}\nRoute: ${sel.from} → ${sel.to}\nDate: ${sel.date}\nSignal: ${sel.sig}\nPredicted mandate: ${sel.mandate}\nConfidence: ${sel.conf}%\nRelationship warmth: ${sel.warmth}/100\n\nWrite a 120-word tactical action brief:\n1. Why this jet track means a mandate is imminent\n2. Exactly which partner should call and why\n3. The opening line for the call that demonstrates intelligence without revealing surveillance\n4. What to pitch in the first 5 minutes\n\nDirect, plain text. No headers.` }]
        })
      });
      const d = await r.json(); setBrief(d.content?.[0]?.text || "Error.");
    } catch { setBrief("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Geospatial Intelligence" title="Corporate Jet Tracker" sub="Monitors public ADS-B transponder signals from aircraft registered to prospect company executives. Unusual Bay Street / Wall Street patterns predict M&A mandates 2–10 weeks in advance."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Active Tracks" val={JETS.length} sub="monitored aircraft" accent="blue"/>
        <Metric label="High Confidence" val={JETS.filter(j => j.conf >= 75).length} sub="≥75% confidence" accent="red"/>
        <Metric label="Est. Total Value" val="$2.6M" sub="across active signals" accent="gold"/>
        <Metric label="Avg Days to Close" val="14–28" sub="historical avg" accent="green"/>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 12 }}>
        {/* Track list */}
        <Panel>
          <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: "var(--t3)", letterSpacing: ".1em" }}>SORTED BY CONFIDENCE</div>
          {[...JETS].sort((a, b) => b.conf - a.conf).map((j, i) => (
            <div key={i} onClick={() => { setSel(j); setBrief(""); }}
              style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)", cursor: "pointer", background: sel.co === j.co ? "var(--elevated)" : "transparent", borderLeft: sel.co === j.co ? "2px solid var(--gold)" : "2px solid transparent" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: "var(--t1)" }}>{j.co}</div>
                <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 17, fontWeight: 700, color: sc(j.conf), lineHeight: 1 }}>{j.conf}%</div>
              </div>
              <div style={{ fontSize: 10, color: "var(--t3)", marginBottom: 4 }}>✈ {j.from} → {j.to}</div>
              <div style={{ display: "flex", gap: 5 }}>
                <Tag label={j.mandate} color="gold"/>
                <Tag label={j.tail} color="default"/>
              </div>
            </div>
          ))}
        </Panel>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Detail card */}
          <Panel>
            <div style={{ padding: "16px 18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
                <div>
                  <div style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 20, color: "var(--t1)", marginBottom: 6 }}>{sel.co}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <Tag label={sel.mandate} color="red"/>
                    <Tag label={sel.tail} color="blue"/>
                    <Tag label={sel.exec} color="default"/>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 44, fontWeight: 700, color: sc(sel.conf), lineHeight: 1 }}>{sel.conf}%</div>
                  <div style={{ fontSize: 8, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>CONFIDENCE</div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, padding: "12px 0", borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)", marginBottom: 14 }}>
                {[["Route", `${sel.from} → ${sel.to}`], ["Detected", sel.date], ["Relationship", `${sel.warmth}/100`]].map(([l, v]) => (
                  <div key={l}>
                    <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 3 }}>{l}</div>
                    <div style={{ fontSize: 12, color: "var(--t1)", fontWeight: 500 }}>{v}</div>
                  </div>
                ))}
              </div>

              {/* Signal banner */}
              <div style={{ background: "rgba(212,168,67,.06)", border: "1px solid rgba(212,168,67,.25)", borderRadius: 3, padding: "10px 13px" }}>
                <div style={{ fontSize: 9, color: "var(--gold)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 5 }}>◈ SIGNAL INTERPRETATION</div>
                <div style={{ fontSize: 12, color: "var(--t2)", lineHeight: 1.55 }}>{sel.sig}</div>
              </div>
            </div>
          </Panel>

          {/* AI Brief */}
          <Panel title="AI Tactical Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Brief"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : brief
                ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--t2)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{brief}</div>
                : <div style={{ fontSize: 11, color: "var(--t3)", fontStyle: "italic" }}>Generate a tactical action brief — which partner calls, the exact opening line that demonstrates intelligence without revealing surveillance, and what to pitch in the first 5 minutes.</div>}
            </div>
          </Panel>

          {/* All tracks summary */}
          <Panel title="Flight History — All Monitored Aircraft">
            <div style={{ padding: "10px 14px" }}>
              {JETS.map((j, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 140px 50px", gap: 10, padding: "8px 0", borderBottom: i < JETS.length - 1 ? "1px solid var(--border)" : "none", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: "var(--t1)" }}>{j.co}</div>
                    <div style={{ fontSize: 9, color: "var(--t3)" }}>{j.date} · {j.tail}</div>
                  </div>
                  <div style={{ fontSize: 10, color: "var(--t3)" }}>{j.from.split(" ")[0]} → {j.to.split(" ")[0]}</div>
                  <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 14, fontWeight: 700, color: sc(j.conf), textAlign: "right" }}>{j.conf}%</div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── 3. FOOT TRAFFIC INTELLIGENCE ──────────────────────────────────────── */
export const FootTraffic = () => {
  const [sel, setSel] = useState(FOOT[0]);
  const [resp, setResp] = useState("");
  const [loading, setLoading] = useState(false);
  const sc = s => ({ critical: "#e05252", high: "#e07c30", medium: "#d4a843", low: "#3dba7a" }[s] || "#6a89b4");

  async function gen() {
    setLoading(true); setResp("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 400,
          messages: [{ role: "user", content: `BigLaw BD AI. A client has been detected at a competitor law firm or significant third-party location.\n\nClient: ${sel.target}\nLocation detected: ${sel.loc}\nDevice cluster: ${sel.dev} devices · ${sel.dur}\nDate: ${sel.date}\nThreat assessment: ${sel.threat}\nSeverity: ${sel.sev.toUpperCase()}\n\nWrite a 100-word response strategy:\n1. What this likely means (RFP, active pitch, relationship-building)\n2. Which partner acts and what they say\n3. Whether to use conflict arbitrage if applicable\n4. The exact tone — urgent but not panicked\n\nPlain text. Direct.` }]
        })
      });
      const d = await r.json(); setResp(d.content?.[0]?.text || "Error.");
    } catch { setResp("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Geospatial Intelligence" title="Foot Traffic Intelligence" sub="Detects when your clients visit competitor law firms or regulators by analysing GPS device clustering at known office addresses. A 14-device cluster at a rival firm for 2+ hours is almost certainly an RFP meeting."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Active Detections" val={FOOT.length} sub="events in 7 days" accent="red"/>
        <Metric label="Critical Threats" val={FOOT.filter(f => f.sev === "critical").length} sub="RFP likely in progress" accent="red"/>
        <Metric label="Revenue at Risk" val="$2.3M" sub="from at-risk clients" accent="gold"/>
        <Metric label="Locations Monitored" val="47" sub="competitor + regulator sites" accent="blue"/>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Detection feed */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {FOOT.map((f, i) => {
            const c = sc(f.sev);
            const isSelected = sel.target === f.target;
            return (
              <div key={i} onClick={() => { setSel(f); setResp(""); }}
                style={{ background: isSelected ? `${c}08` : "var(--card)", border: `1px solid ${isSelected ? `${c}35` : "var(--border)"}`, borderLeft: `3px solid ${c}`, borderRadius: 4, padding: "14px 16px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, color: "var(--t1)" }}>{f.target}</div>
                  <span style={{ fontSize: 8, fontFamily: "'JetBrains Mono',monospace", background: `${c}18`, border: `1px solid ${c}35`, color: c, padding: "2px 7px", borderRadius: 2 }}>{f.sev.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: 11, color: c, fontFamily: "'JetBrains Mono',monospace", marginBottom: 6 }}>📍 {f.loc}</div>
                <div style={{ display: "flex", gap: 10, marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: "var(--t3)" }}>📱 {f.dev} devices</div>
                  <div style={{ fontSize: 10, color: "var(--t3)" }}>⏱ {f.dur}</div>
                  <div style={{ fontSize: 10, color: "var(--t3)" }}>📅 {f.date}</div>
                </div>
                <div style={{ fontSize: 11, color: "var(--t2)", padding: "8px 10px", background: "var(--elevated)", borderRadius: 3 }}>
                  <span style={{ color: "var(--t3)", fontSize: 9, fontFamily: "'JetBrains Mono',monospace" }}>THREAT: </span>{f.threat}
                </div>
              </div>
            );
          })}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Action recommendation */}
          <Panel>
            <div style={{ padding: "14px 16px" }}>
              <div style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 16, color: "var(--t1)", marginBottom: 4 }}>{sel.target}</div>
              <div style={{ fontSize: 11, color: "var(--t3)", marginBottom: 12 }}>RECOMMENDED ACTION</div>
              <div style={{ background: "rgba(212,168,67,.05)", border: "1px solid rgba(212,168,67,.2)", borderRadius: 3, padding: "12px 14px", marginBottom: 14 }}>
                <div style={{ fontSize: 12, color: "var(--t2)", lineHeight: 1.65 }}>{sel.action}</div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[["Devices Detected", `${sel.dev} clustered`], ["Duration", sel.dur], ["Detection Date", sel.date], ["Severity", sel.sev.toUpperCase()]].map(([l, v]) => (
                  <div key={l} style={{ background: "var(--elevated)", borderRadius: 3, padding: "8px 10px" }}>
                    <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 3 }}>{l}</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--t1)" }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <Panel title="AI Counter-Strategy" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Strategy"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : resp
                ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--t2)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{resp}</div>
                : <div style={{ fontSize: 11, color: "var(--t3)", fontStyle: "italic" }}>Generate a counter-strategy — who acts, what they say, whether to invoke conflict arbitrage, and the exact tone for the outreach.</div>}
            </div>
          </Panel>

          <Panel title="Detection Methodology">
            <div style={{ padding: "12px 16px" }}>
              {[
                ["Data Source", "Commercial GPS clustering (SafeGraph/Veraset)"],
                ["Detection Method", "Device concentration ≥5 from known client domain"],
                ["Minimum Threshold", "3+ devices · 45+ minute dwell time"],
                ["Update Frequency", "Near real-time · 15-minute lag"],
                ["False Positive Rate", "Estimated 8–12% (conference events, lobby meetings)"],
              ].map(([l, v]) => (
                <div key={l} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 10, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>{l}</span>
                  <span style={{ fontSize: 11, color: "var(--t2)", textAlign: "right", maxWidth: "55%" }}>{v}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── 4. SATELLITE SIGNALS ───────────────────────────────────────────────── */
export const Satellite = () => {
  const [sel, setSel] = useState(SAT[0]);
  const [analysis, setAnalysis] = useState("");
  const [loading, setLoading] = useState(false);
  const uc = u => ({ high: "#e05252", medium: "#e07c30", low: "#3dba7a" }[u] || "#d4a843");
  const tc = { "Workforce": "red", "Construction": "blue", "Supply Chain": "gold", "Environmental": "green" };

  async function gen() {
    setLoading(true); setAnalysis("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 450,
          messages: [{ role: "user", content: `BigLaw BD analyst. A satellite intelligence signal has been detected.\n\nCompany: ${sel.co}\nLocation: ${sel.loc}\nSatellite observation: ${sel.sig}\nInference: ${sel.inf}\nSignal type: ${sel.type}\nConfidence: ${sel.conf}%\nUrgency: ${sel.urg.toUpperCase()}\n\nWrite a 120-word legal exposure brief:\n1. What this satellite observation legally means for the company\n2. Which specific legal matter is almost certainly forming (be specific — e.g. "WSIB mass layoff filing, mandatory 8-week notice period begins")\n3. Exactly which practice group should call, what they offer, and the opening line\n4. Timeline — how many days until this becomes a public event\n\nDirect, specific, plain text.` }]
        })
      });
      const d = await r.json(); setAnalysis(d.content?.[0]?.text || "Error.");
    } catch { setAnalysis("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Geospatial Intelligence" title="Satellite Signal Intelligence" sub="Analyses commercial satellite imagery of target company facilities to detect workforce changes (parking lot occupancy), construction activity, and environmental anomalies before public disclosure."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Active Signals" val={SAT.length} sub="facilities monitored" accent="blue"/>
        <Metric label="High Urgency" val={SAT.filter(s => s.urg === "high").length} sub="immediate action" accent="red"/>
        <Metric label="Avg Confidence" val={`${Math.round(SAT.reduce((s, i) => s + i.conf, 0) / SAT.length)}%`} sub="signal accuracy" accent="gold"/>
        <Metric label="Est. Pipeline" val="$960K" sub="from sat signals" accent="green"/>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 12 }}>
        {/* Signal list */}
        <Panel>
          {SAT.map((s, i) => {
            const c = uc(s.urg);
            return (
              <div key={i} onClick={() => { setSel(s); setAnalysis(""); }}
                style={{ padding: "13px 14px", borderBottom: "1px solid var(--border)", cursor: "pointer", background: sel.co === s.co ? "var(--elevated)" : "transparent", borderLeft: sel.co === s.co ? "2px solid var(--gold)" : "2px solid transparent" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "var(--t1)" }}>{s.co}</div>
                  <Tag label={s.type} color={tc[s.type] || "default"}/>
                </div>
                <div style={{ fontSize: 10, color: "var(--t3)", marginBottom: 5 }}>📍 {s.loc}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 8, fontFamily: "'JetBrains Mono',monospace", color: c, background: `${c}15`, border: `1px solid ${c}30`, padding: "2px 6px", borderRadius: 2 }}>{s.urg.toUpperCase()}</span>
                  <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 13, fontWeight: 700, color: c }}>{s.conf}%</span>
                </div>
              </div>
            );
          })}
        </Panel>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Panel>
            <div style={{ padding: "16px 18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                <div>
                  <div style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 20, color: "var(--t1)", marginBottom: 6 }}>{sel.co}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <Tag label={sel.type} color={tc[sel.type] || "default"}/>
                    <Tag label={sel.loc} color="default"/>
                    {sel.lead && <Tag label={`Lead: ${sel.lead}`} color="green"/>}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 44, fontWeight: 700, color: uc(sel.urg), lineHeight: 1 }}>{sel.conf}%</div>
                  <div style={{ fontSize: 8, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>CONFIDENCE</div>
                </div>
              </div>

              {/* Satellite visual placeholder */}
              <div style={{ background: "var(--elevated)", border: "1px solid var(--border)", borderRadius: 3, padding: "14px", marginBottom: 12, position: "relative", overflow: "hidden", height: 90 }}>
                <div style={{ position: "absolute", inset: 0, backgroundImage: "radial-gradient(circle at 30% 40%, rgba(61,186,122,.08) 0%, transparent 60%), radial-gradient(circle at 70% 60%, rgba(74,143,255,.06) 0%, transparent 50%)", pointerEvents: "none" }}/>
                <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 8 }}>◎ SATELLITE OBSERVATION · {sel.loc.toUpperCase()}</div>
                <div style={{ fontSize: 12, color: "var(--t2)", lineHeight: 1.55 }}>{sel.sig}</div>
              </div>

              <div style={{ background: "rgba(212,168,67,.04)", border: "1px solid rgba(212,168,67,.2)", borderRadius: 3, padding: "10px 12px" }}>
                <div style={{ fontSize: 9, color: "var(--gold)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 5 }}>LEGAL INFERENCE</div>
                <div style={{ fontSize: 12, color: "var(--t2)", lineHeight: 1.6 }}>{sel.inf}</div>
              </div>
            </div>
          </Panel>

          <Panel title="AI Legal Exposure Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Assess Exposure"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : analysis
                ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--t2)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{analysis}</div>
                : <div style={{ fontSize: 11, color: "var(--t3)", fontStyle: "italic" }}>Generate a legal exposure brief — what the satellite observation means legally, which specific matter is forming, and the exact call to make.</div>}
            </div>
          </Panel>

          <Panel title="Data Sources">
            <div style={{ padding: "10px 16px" }}>
              {[["Imagery Source", "Google Earth Engine · Sentinel-2 · Copernicus Open Access"], ["Resolution", "10m (Sentinel-2) · 3m (Planet Labs where licensed)"], ["Update Cadence", "Weekly revisit · High-urgency sites daily"], ["Detection Method", "OpenCV change detection · Parking lot vehicle count"], ["Free Tier", "Google Earth Engine (non-commercial) · Copernicus (free)"]].map(([l, v]) => (
                <div key={l} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ fontSize: 10, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>{l}</span>
                  <span style={{ fontSize: 11, color: "var(--t2)", textAlign: "right", maxWidth: "55%" }}>{v}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── 5. PERMIT RADAR ────────────────────────────────────────────────────── */
export const PermitRadar = () => {
  const [sel, setSel] = useState(PERMITS[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const uc = u => ({ high: "#e05252", medium: "#d4a843", low: "#3dba7a" }[u] || "#4a8fff");
  const workColors = { Environmental: "green", Indigenous: "green", Regulatory: "blue", "Real Estate": "blue", Construction: "blue", Lender: "blue", "Lender Counsel": "blue", Employment: "gold", IP: "purple", Restructuring: "red", Finance: "cyan", "Land Use": "gold" };

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 450,
          messages: [{ role: "user", content: `BigLaw BD analyst. A significant permit filing has appeared that predicts legal work.\n\nCompany: ${sel.co}\nPermit: ${sel.permit}\nLocation: ${sel.loc}\nFiled: ${sel.filed}\nProject type: ${sel.type}\nPractice areas triggered: ${sel.work.join(", ")}\nEstimated legal value: ${sel.rev}\nUrgency: ${sel.urg.toUpperCase()}\n${sel.lead ? `Existing relationship: ${sel.lead}` : "No existing relationship — prospect outreach"}\n\nWrite a 120-word outreach brief:\n1. Why this permit means legal work is imminent (be specific about which legal steps are legally required)\n2. The exact sequence of legal matters this project will generate and in what order\n3. Which partner calls, what they say, and when\n4. Opening line for the call\n\nDirect, plain text.` }]
        })
      });
      const d = await r.json(); setBrief(d.content?.[0]?.text || "Error.");
    } catch { setBrief("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Geospatial Intelligence" title="Permit Radar" sub="Aggregates construction, demolition, and environmental assessment permits from municipal and provincial portals. Every major permit is a legal trigger — mapped to practice areas and estimated fee value."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Active Permits" val={PERMITS.length} sub="filed past 30 days" accent="blue"/>
        <Metric label="High Urgency" val={PERMITS.filter(p => p.urg === "high").length} sub="immediate action" accent="red"/>
        <Metric label="Est. Fee Value" val={`$${(PERMITS.reduce((s, p) => s + parseInt(p.rev.replace(/\$|K/g, "")), 0))}K`} sub="total legal work" accent="gold"/>
        <Metric label="Unmatched Prospects" val={PERMITS.filter(p => !p.lead).length} sub="new client opps" accent="green"/>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 12 }}>
        {/* Permit list */}
        <Panel>
          <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: "var(--t3)", letterSpacing: ".1em" }}>SORTED BY URGENCY · {PERMITS.length} PERMITS</div>
          {[...PERMITS].sort((a, b) => a.urg === "high" ? -1 : 1).map((p, i) => (
            <div key={i} onClick={() => { setSel(p); setBrief(""); }}
              style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)", cursor: "pointer", background: sel.co === p.co && sel.permit === p.permit ? "var(--elevated)" : "transparent", borderLeft: sel.co === p.co && sel.permit === p.permit ? "2px solid var(--gold)" : "2px solid transparent" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: "var(--t1)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>{p.co}</div>
                <span style={{ fontSize: 8, background: `${uc(p.urg)}18`, border: `1px solid ${uc(p.urg)}35`, color: uc(p.urg), padding: "2px 6px", borderRadius: 2, fontFamily: "'JetBrains Mono',monospace", flexShrink: 0 }}>{p.urg.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: 10, color: "var(--t3)", marginBottom: 5 }}>{p.permit}</div>
              <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                <Tag label={p.rev} color="gold"/>
                {p.lead ? <Tag label={p.lead} color="green"/> : <Tag label="New Prospect" color="blue"/>}
              </div>
            </div>
          ))}
        </Panel>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Panel>
            <div style={{ padding: "16px 18px" }}>
              <div style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 18, color: "var(--t1)", marginBottom: 4 }}>{sel.co}</div>
              <div style={{ fontSize: 11, color: "var(--t3)", marginBottom: 12 }}>{sel.loc} · Filed {sel.filed}</div>
              <div style={{ background: "var(--elevated)", border: "1px solid var(--border)", borderRadius: 3, padding: "12px 14px", marginBottom: 12 }}>
                <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 5 }}>PERMIT TYPE</div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--t1)", marginBottom: 4 }}>{sel.permit}</div>
                <div style={{ fontSize: 11, color: "var(--t2)" }}>{sel.type}</div>
              </div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 8 }}>LEGAL WORK TRIGGERED</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {sel.work.map(w => <Tag key={w} label={w} color={workColors[w] || "default"}/>)}
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                {[["Est. Fee Value", sel.rev, "var(--gold)"], ["Urgency", sel.urg.toUpperCase(), uc(sel.urg)], ["Relationship", sel.lead || "None", sel.lead ? "var(--green)" : "var(--t3)"]].map(([l, v, c]) => (
                  <div key={l} style={{ background: "var(--elevated)", borderRadius: 3, padding: "8px 10px" }}>
                    <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 3 }}>{l}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: c }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <Panel title="AI Outreach Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Brief"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : brief
                ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--t2)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{brief}</div>
                : <div style={{ fontSize: 11, color: "var(--t3)", fontStyle: "italic" }}>Generate an outreach brief — the legal sequence this project will generate, which partner calls, and the exact opening line.</div>}
            </div>
          </Panel>

          <Panel title="Data Sources — All Free">
            {[
              { src: "Ontario Environmental Registry", url: "ero.ontario.ca", feed: "RSS + HTML", cad: "Daily" },
              { src: "IAAC Federal Projects", url: "iaac-aeic.gc.ca/050/evaluations/proj/api", feed: "REST API", cad: "Hourly" },
              { src: "City of Toronto ePlans", url: "toronto.ca/city-government/planning-development", feed: "HTML scrape", cad: "Daily" },
              { src: "BC Environmental Assessment", url: "projects.eao.gov.bc.ca", feed: "RSS", cad: "Weekly" },
              { src: "Alberta OneStop Registry", url: "alberta.ca/SPIN2/start.do", feed: "HTML scrape", cad: "Daily" },
            ].map((s, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 80px 60px", gap: 8, padding: "8px 14px", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 500, color: "var(--t1)" }}>{s.src}</div>
                  <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>{s.url}</div>
                </div>
                <Tag label={s.feed} color="default"/>
                <Tag label={s.cad} color="green"/>
              </div>
            ))}
          </Panel>
        </div>
      </div>
    </div>
  );
};
