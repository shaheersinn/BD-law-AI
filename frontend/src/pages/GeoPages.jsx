import * as apiClient from "../api/client.js";
// src/pages/GeoPages.jsx
// Five geospatial intelligence modules:
// GeoMap Â· JetTracker Â· FootTraffic Â· Satellite Â· PermitRadar

import { useState } from "react";

/* â”€â”€â”€ Shared primitives (inlined so this file is self-contained) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const Tag = ({ label, color = "default" }) => {
  const map = {
    default: { bg: "rgba(106,137,180,.1)", br: "rgba(106,137,180,.25)", tx: "var(--color-on-surface-variant)" },
    red:     { bg: "rgba(224,82,82,.1)",   br: "rgba(224,82,82,.3)",    tx: "var(--color-error)" },
    gold:    { bg: "rgba(212,168,67,.1)",  br: "rgba(212,168,67,.3)",   tx: "var(--color-secondary)" },
    green:   { bg: "rgba(61,186,122,.1)",  br: "rgba(61,186,122,.3)",   tx: "var(--color-success)" },
    blue:    { bg: "rgba(74,143,255,.1)",  br: "rgba(74,143,255,.3)",   tx: "var(--color-primary)" },
    cyan:    { bg: "rgba(34,201,212,.1)",  br: "rgba(34,201,212,.3)",   tx: "var(--color-secondary)" },
    purple:  { bg: "rgba(155,109,255,.1)", br: "rgba(155,109,255,.3)",  tx: "var(--color-primary-container)" },
  };
  const s = map[color] || map.default;
  return (
    <span style={{
      background: s.bg, border: `1px solid ${s.br}`, color: s.tx,
      fontSize: 9, fontFamily: "var(--font-mono)", letterSpacing: ".07em",
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
  const c = color || (s >= 75 ? "var(--color-error)" : s >= 50 ? "var(--color-warning)" : s >= 30 ? "var(--color-secondary)" : "var(--color-success)");
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 3, background: "var(--color-surface-container-high)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${s}%`, height: "100%", background: c, borderRadius: 2, transition: "width .8s ease" }}/>
      </div>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: c, width: 26, textAlign: "right" }}>{s}</span>
    </div>
  );
};

const Panel = ({ title, children, actions, style = {} }) => (
  <div style={{ background: "var(--color-surface-container-lowest)", border: "0 0 0 1px var(--color-outline-variant)", borderRadius: 4, ...style }}>
    {title && (
      <div style={{ padding: "12px 16px", borderBottom: "0 0 0 1px var(--color-outline-variant)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--color-on-surface-variant)", letterSpacing: ".08em", textTransform: "uppercase" }}>{title}</span>
        {actions}
      </div>
    )}
    {children}
  </div>
);

const Metric = ({ label, val, sub, accent = "gold" }) => {
  const cols = { gold: "var(--color-secondary)", red: "var(--color-error)", green: "var(--color-success)", blue: "var(--color-primary)", purple: "var(--color-primary-container)", cyan: "var(--color-secondary)" };
  return (
    <div style={{ background: "var(--color-surface-container-lowest)", border: "0 0 0 1px var(--color-outline-variant)", borderRadius: 4, padding: "16px 18px", position: "relative", overflow: "hidden" }}>
      <div style={{ fontSize: 9, fontFamily: "var(--font-mono)", color: "var(--color-on-surface-variant)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 26, fontWeight: 600, color: cols[accent] || "var(--color-on-surface)", lineHeight: 1 }}>{val}</div>
      {sub && <div style={{ marginTop: 6, fontSize: 10, color: "var(--color-on-surface-variant)" }}>{sub}</div>}
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 2, background: cols[accent] || "var(--color-on-surface)", opacity: .3 }}/>
    </div>
  );
};

const PageHeader = ({ tag, title, sub }) => (
  <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: "0 0 0 1px var(--color-outline-variant)" }}>
    {tag && <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-secondary)", letterSpacing: ".14em", marginBottom: 6, textTransform: "uppercase" }}>â—ˆ {tag}</div>}
    <h1 style={{ fontFamily: "'Newsreader',serif", fontWeight: 800, fontSize: 22, letterSpacing: "-.03em", marginBottom: 4, color: "var(--color-on-surface)" }}>{title}</h1>
    {sub && <p style={{ color: "var(--color-on-surface-variant)", fontSize: 12, lineHeight: 1.6 }}>{sub}</p>}
  </div>
);

const OBtn = ({ children, onClick, disabled, secondary, small }) => (
  <button onClick={onClick} disabled={disabled} style={{
    padding: small ? "5px 12px" : "7px 16px", borderRadius: 3,
    fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 500,
    letterSpacing: ".06em", textTransform: "uppercase",
    border: secondary ? "1px solid var(--border2)" : "none",
    background: secondary ? "transparent" : disabled ? "rgba(212,168,67,.2)" : "var(--color-secondary)",
    color: secondary ? "var(--color-on-surface-variant)" : disabled ? "var(--color-on-surface-variant)" : "var(--color-on-primary)",
    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? .6 : 1,
  }}>{children}</button>
);

const AiBadge = () => <Tag label="â—ˆ AI" color="gold"/>;

const Spinner = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--color-on-surface-variant)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
    <div style={{ width: 13, height: 13, border: "2px solid var(--border2)", borderTopColor: "var(--color-secondary)", borderRadius: "50%", animation: "spin .7s linear infinite" }}/>
    Processingâ€¦
  </div>
);

/* â”€â”€â”€ Data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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
  { co: "Arctis Mining Corp",      tail: "C-FMTX", exec: "CEO Marcus Reid",   from: "Calgary YYC",     to: "Toronto Billy Bishop", date: "Nov 14 Â· 09:22", sig: "3rd Bay Street trip in 10 days",          mandate: "M&A â€” Sell-Side",       conf: 91, warmth: 18 },
  { co: "Stellex Infrastructure",  tail: "C-GXLP", exec: "CFO Jana Obi",      from: "Toronto Pearson", to: "New York JFK",         date: "Nov 13 Â· 14:05", sig: "2nd NYC trip â€” Lazard HQ proximate",      mandate: "Fund Restructuring",    conf: 74, warmth: 44 },
  { co: "Vesta Retail REIT",       tail: "C-HRTV", exec: "CEO + COO",         from: "Toronto YYZ",     to: "Vancouver YVR",        date: "Nov 12 Â· 07:44", sig: "Unscheduled â€” no investor event listed",  mandate: "Asset Sale",            conf: 68, warmth: 5  },
  { co: "Caldwell Steel Works",    tail: "N821PW",  exec: "Board Chair",       from: "Detroit DTW",     to: "Hamilton YHM",         date: "Nov 11 Â· 16:30", sig: "Same-day return â€” restructuring counsel", mandate: "Insolvency / CCAA",     conf: 55, warmth: 12 },
  { co: "Borealis Genomics",       tail: "C-FVXQ", exec: "CFO + VP BD",       from: "Waterloo YKF",    to: "Boston BOS",           date: "Nov 10 Â· 08:15", sig: "3rd Boston trip â€” Kendall Square biotech", mandate: "Series C / Licensing",  conf: 62, warmth: 38 },
];

const FOOT = [
  { target: "Aurelia Capital Group",  loc: "Davies Ward Phillips â€” 155 Wellington St W", dev: 14, dur: "2.5 hrs avg", date: "Nov 13", threat: "RFP or active pitch in progress at rival firm",              sev: "critical", action: "Counter-pitch today. Use conflict arbitrage angle â€” Davies has CIBC retainer." },
  { target: "Meridian Logistics",     loc: "Blake Cassels CLE event space",              dev: 6,  dur: "Full day",     date: "Nov 12", threat: "Competitor relationship-building CLE event",                 sev: "high",     action: "M. Webb to arrange direct 1:1 with GC this week before Blake creates loyalty." },
  { target: "Centurion Pharma",       loc: "Osler offices â€” 100 King St W",              dev: 8,  dur: "3.1 hrs avg",  date: "Nov 10", threat: "Potential mandate evaluation â€” multiple visits in 21 days",  sev: "high",     action: "D. Park to call Deputy GC immediately. IP matter is vulnerable." },
  { target: "Vantage Rail Corp",      loc: "Transport Canada Ottawa HQ",                 dev: 22, dur: "All day",       date: "Nov 09", threat: "Regulatory examination â€” personnel on-site all day",         sev: "medium",   action: "Regulatory audit likely. Offer pre-response counsel before file opens." },
];

const SAT = [
  { co: "Caldwell Steel Works",   loc: "Hamilton, ON",        sig: "Parking lot occupancy: 94% â†’ 31% over 4 weeks",          inf: "Mass layoff forming â€” employment law mandate imminent within 2â€“3 weeks",         conf: 88, type: "Workforce",     urg: "high",   lead: null },
  { co: "Northfield Energy",      loc: "Fort McMurray, AB",   sig: "Excavation equipment appeared at previously idle pad",     inf: "Capital project resuming â€” construction, environmental, financing counsel needed", conf: 76, type: "Construction", urg: "medium", lead: "J. Okafor" },
  { co: "Arctis Mining Corp",     loc: "Timmins, ON",         sig: "Shipping container accumulation +340% vs 12-month avg",    inf: "Supply chain disruption or shutdown preparation â€” restructuring signal",         conf: 71, type: "Supply Chain", urg: "medium", lead: null },
  { co: "Unknown Industrial",     loc: "Sarnia, ON corridor", sig: "Thermal plume detected â€” 3.2 km NE drift from facility",   inf: "Environmental violation pre-enforcement â€” call before regulator does",          conf: 83, type: "Environmental", urg: "high",   lead: null },
  { co: "Borealis Genomics",      loc: "Waterloo, ON",        sig: "Structural steel erected â€” new building footprint visible", inf: "Lab expansion confirmed â€” construction, employment, IP licensing counsel",       conf: 91, type: "Construction", urg: "low",    lead: "D. Park" },
];

const PERMITS = [
  { co: "Northfield Energy Partners", permit: "Environmental Assessment Application", loc: "Fort McMurray, AB",   filed: "Nov 10", type: "New pipeline â€” 480 km corridor",        work: ["Environmental", "Indigenous", "Regulatory"],         urg: "high",   rev: "$420K", lead: "J. Okafor" },
  { co: "Unknown Applicant",          permit: "Demolition Permit â€” Class A tower",   loc: "King & Bay, Toronto", filed: "Nov 08", type: "Full commercial tower demolition",        work: ["Real Estate", "Construction", "Lender Counsel"],      urg: "medium", rev: "$180K", lead: null },
  { co: "Borealis Genomics",          permit: "Building Permit â€” Lab expansion",     loc: "Waterloo Research Park", filed: "Nov 06", type: "22,000 sq ft R&D facility",          work: ["Construction", "Employment", "IP Licensing"],         urg: "medium", rev: "$140K", lead: "D. Park" },
  { co: "Caldwell Steel Works",       permit: "Change of Use â€” Industrial to Storage", loc: "Hamilton, ON",      filed: "Nov 03", type: "Major facility conversion + rezoning",    work: ["Restructuring", "Real Estate", "Environmental"],      urg: "high",   rev: "$220K", lead: null },
  { co: "Stellex Infrastructure",     permit: "Environmental Impact Assessment",     loc: "Kitchener-Waterloo",  filed: "Oct 28", type: "Solar farm â€” 1,200 acres",               work: ["Environmental", "Land Use", "Indigenous", "Finance"], urg: "medium", rev: "$310K", lead: "J. Okafor" },
];

/* â”€â”€â”€ 1. GEOPOLITICAL MANDATE HEAT MAP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export const GeoMap = () => {
  const [sel, setSel] = useState(GEO[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);

  const intCol = v => v >= 80 ? "var(--color-error)" : v >= 65 ? "var(--color-warning)" : v >= 50 ? "var(--color-secondary)" : "var(--color-primary)";

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 600,
          messages: [{ role: "user", content: `BigLaw BD AI. Write a 130-word market intelligence brief for a Canadian law firm considering a BD push into ${sel.label}.\n\nCurrent legal demand index: ${sel.v}/100\nTop practice areas: ${sel.practice}\nKey drivers: ${sel.drivers}\n\nProvide: (1) The single highest-value opportunity for a Canadian firm right now (2) Which existing client relationships have cross-border exposure here (3) One concrete BD action this quarter â€” event, thought leadership, or referral network to activate. Plain text, direct, no headers.` }]
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
        <Metric label="High Demand" val={GEO.filter(g => g.v >= 75).length} sub="â‰¥75 intensity" accent="red"/>
        <Metric label="Peak Jurisdiction" val="Canada" sub="91/100 intensity" accent="gold"/>
        <Metric label="Practice Overlap" val="M&A + Reg" sub="top cross-border need" accent="green"/>
      </div>

      {/* SVG World Map */}
      <Panel title="Legal Demand by Jurisdiction â€” Click to Drill Down" style={{ marginBottom: 12 }}>
        <div style={{ padding: "16px", position: "relative" }}>
          <svg viewBox="0 0 900 420" style={{ width: "100%", height: "auto", background: "transparent" }}>
            {/* Simplified continent outlines */}
            {/* North America */}
            <path d="M80,80 L280,80 L310,120 L290,180 L250,220 L180,230 L140,200 L100,160 L80,120 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            {/* South America */}
            <path d="M180,250 L240,245 L255,290 L250,360 L220,390 L195,380 L170,340 L160,290 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            {/* Europe */}
            <path d="M390,90 L480,85 L490,140 L470,165 L440,160 L400,145 L385,120 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            {/* Africa */}
            <path d="M400,175 L470,170 L490,200 L485,300 L460,340 L430,340 L405,310 L390,260 L395,210 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            {/* Middle East */}
            <path d="M490,180 L560,175 L565,225 L545,240 L510,235 L488,215 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            {/* Asia */}
            <path d="M565,80 L760,75 L775,140 L760,190 L730,210 L700,200 L660,215 L630,210 L600,200 L570,175 L555,140 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>
            {/* Australia */}
            <path d="M650,270 L760,265 L775,310 L760,360 L720,370 L685,360 L660,330 L645,300 Z" fill="rgba(26,40,64,.6)" stroke="var(--color-surface-container-high)" strokeWidth="1"/>

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
                  <text x={g.x} y={g.y + 22} textAnchor="middle" fill="var(--color-on-surface-variant)" fontSize="9" fontFamily="var(--font-mono)">{g.label}</text>
                  {/* Score */}
                  <text x={g.x} y={g.y + 4} textAnchor="middle" fill="var(--color-on-primary)" fontSize="8" fontFamily="var(--font-mono)" fontWeight="600">{g.v}</text>
                </g>
              );
            })}

            {/* Legend */}
            {[{ c: "var(--color-error)", l: "High â‰¥80" }, { c: "var(--color-warning)", l: "Med-High 65-79" }, { c: "var(--color-secondary)", l: "Medium 50-64" }, { c: "var(--color-primary)", l: "Emerging <50" }].map((item, i) => (
              <g key={i} transform={`translate(${620 + i * 0}, ${370 + i * 14})`}>
                <circle cx="6" cy="6" r="4" fill={item.c}/>
                <text x="14" y="10" fill="var(--color-on-surface-variant)" fontSize="8" fontFamily="var(--font-mono)">{item.l}</text>
              </g>
            ))}
          </svg>
        </div>
      </Panel>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Selected jurisdiction detail */}
        <Panel title={`${sel.label} â€” Jurisdiction Intelligence`}>
          <div style={{ padding: "14px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <div style={{ fontFamily: "'Newsreader',serif", fontWeight: 800, fontSize: 20, color: "var(--color-on-surface)", marginBottom: 6 }}>{sel.label}</div>
                <Tag label={sel.practice} color="blue"/>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 44, fontWeight: 700, color: intCol(sel.v), lineHeight: 1 }}>{sel.v}</div>
                <div style={{ fontSize: 8, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>DEMAND INDEX</div>
              </div>
            </div>
            <SBar s={sel.v} color={intCol(sel.v)}/>
            <div style={{ marginTop: 14, padding: "10px 12px", background: "var(--color-surface-container-low)", borderRadius: 3, border: "0 0 0 1px var(--color-outline-variant)" }}>
              <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 6 }}>KEY DRIVERS</div>
              <div style={{ fontSize: 12, color: "var(--color-on-surface-variant)", lineHeight: 1.6 }}>{sel.drivers}</div>
            </div>
          </div>
        </Panel>

        {/* AI Brief */}
        <Panel title="AI Market Intelligence Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "â€¦" : "Generate Brief"}</OBtn></div>}>
          <div style={{ padding: "14px 16px" }}>
            {loading ? <Spinner/> : brief
              ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--color-on-surface-variant)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{brief}</div>
              : <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontStyle: "italic" }}>Select a jurisdiction on the map, then generate a market intelligence brief â€” opportunity analysis, cross-border exposure, and one concrete BD action for this quarter.</div>}
          </div>
        </Panel>
      </div>

      {/* Jurisdiction ranking table */}
      <Panel title="All Jurisdictions â€” Demand Ranking" style={{ marginTop: 12 }}>
        <div style={{ padding: "10px 14px" }}>
          {[...GEO].sort((a, b) => b.v - a.v).map((g, i) => (
            <div key={g.id} onClick={() => { setSel(g); setBrief(""); }}
              style={{ display: "grid", gridTemplateColumns: "24px 1fr 180px 60px", gap: 12, alignItems: "center", padding: "9px 10px", borderBottom: "0 0 0 1px var(--color-outline-variant)", cursor: "pointer", borderRadius: 3, background: sel.id === g.id ? "var(--color-surface-container-low)" : "transparent" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--color-on-surface-variant)" }}>{i + 1}</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-on-surface)" }}>{g.label}</div>
                <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)" }}>{g.practice}</div>
              </div>
              <SBar s={g.v} color={intCol(g.v)}/>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 700, color: intCol(g.v), textAlign: "right" }}>{g.v}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
};

/* â”€â”€â”€ 2. CORPORATE JET TRACKER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export const JetTracker = () => {
  const [sel, setSel] = useState(JETS[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const sc = c => c >= 80 ? "var(--color-error)" : c >= 65 ? "var(--color-warning)" : "var(--color-secondary)";

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 500,
          messages: [{ role: "user", content: `BigLaw M&A BD. A corporate jet track has fired a mandate signal.\n\nCompany: ${sel.co}\nAircraft: ${sel.tail}\nExecutive: ${sel.exec}\nRoute: ${sel.from} â†’ ${sel.to}\nDate: ${sel.date}\nSignal: ${sel.sig}\nPredicted mandate: ${sel.mandate}\nConfidence: ${sel.conf}%\nRelationship warmth: ${sel.warmth}/100\n\nWrite a 120-word tactical action brief:\n1. Why this jet track means a mandate is imminent\n2. Exactly which partner should call and why\n3. The opening line for the call that demonstrates intelligence without revealing surveillance\n4. What to pitch in the first 5 minutes\n\nDirect, plain text. No headers.` }]
        })
      });
      const d = await r.json(); setBrief(d.content?.[0]?.text || "Error.");
    } catch { setBrief("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Geospatial Intelligence" title="Corporate Jet Tracker" sub="Monitors public ADS-B transponder signals from aircraft registered to prospect company executives. Unusual Bay Street / Wall Street patterns predict M&A mandates 2â€“10 weeks in advance."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Active Tracks" val={JETS.length} sub="monitored aircraft" accent="blue"/>
        <Metric label="High Confidence" val={JETS.filter(j => j.conf >= 75).length} sub="â‰¥75% confidence" accent="red"/>
        <Metric label="Est. Total Value" val="$2.6M" sub="across active signals" accent="gold"/>
        <Metric label="Avg Days to Close" val="14â€“28" sub="historical avg" accent="green"/>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 12 }}>
        {/* Track list */}
        <Panel>
          <div style={{ padding: "10px 14px", borderBottom: "0 0 0 1px var(--color-outline-variant)", fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-on-surface-variant)", letterSpacing: ".1em" }}>SORTED BY CONFIDENCE</div>
          {[...JETS].sort((a, b) => b.conf - a.conf).map((j, i) => (
            <div key={i} onClick={() => { setSel(j); setBrief(""); }}
              style={{ padding: "12px 14px", borderBottom: "0 0 0 1px var(--color-outline-variant)", cursor: "pointer", background: sel.co === j.co ? "var(--color-surface-container-low)" : "transparent", borderLeft: sel.co === j.co ? "2px solid var(--gold)" : "2px solid transparent" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-on-surface)" }}>{j.co}</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 17, fontWeight: 700, color: sc(j.conf), lineHeight: 1 }}>{j.conf}%</div>
              </div>
              <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)", marginBottom: 4 }}>âœˆ {j.from} â†’ {j.to}</div>
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
                  <div style={{ fontFamily: "'Newsreader',serif", fontWeight: 800, fontSize: 20, color: "var(--color-on-surface)", marginBottom: 6 }}>{sel.co}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <Tag label={sel.mandate} color="red"/>
                    <Tag label={sel.tail} color="blue"/>
                    <Tag label={sel.exec} color="default"/>
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 44, fontWeight: 700, color: sc(sel.conf), lineHeight: 1 }}>{sel.conf}%</div>
                  <div style={{ fontSize: 8, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>CONFIDENCE</div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, padding: "12px 0", borderTop: "0 0 0 1px var(--color-outline-variant)", borderBottom: "0 0 0 1px var(--color-outline-variant)", marginBottom: 14 }}>
                {[["Route", `${sel.from} â†’ ${sel.to}`], ["Detected", sel.date], ["Relationship", `${sel.warmth}/100`]].map(([l, v]) => (
                  <div key={l}>
                    <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 3 }}>{l}</div>
                    <div style={{ fontSize: 12, color: "var(--color-on-surface)", fontWeight: 500 }}>{v}</div>
                  </div>
                ))}
              </div>

              {/* Signal banner */}
              <div style={{ background: "rgba(212,168,67,.06)", border: "1px solid rgba(212,168,67,.25)", borderRadius: 3, padding: "10px 13px" }}>
                <div style={{ fontSize: 9, color: "var(--color-secondary)", fontFamily: "var(--font-mono)", marginBottom: 5 }}>â—ˆ SIGNAL INTERPRETATION</div>
                <div style={{ fontSize: 12, color: "var(--color-on-surface-variant)", lineHeight: 1.55 }}>{sel.sig}</div>
              </div>
            </div>
          </Panel>

          {/* AI Brief */}
          <Panel title="AI Tactical Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "â€¦" : "Generate Brief"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : brief
                ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--color-on-surface-variant)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{brief}</div>
                : <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontStyle: "italic" }}>Generate a tactical action brief â€” which partner calls, the exact opening line that demonstrates intelligence without revealing surveillance, and what to pitch in the first 5 minutes.</div>}
            </div>
          </Panel>

          {/* All tracks summary */}
          <Panel title="Flight History â€” All Monitored Aircraft">
            <div style={{ padding: "10px 14px" }}>
              {JETS.map((j, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 140px 50px", gap: 10, padding: "8px 0", borderBottom: i < JETS.length - 1 ? "0 0 0 1px var(--color-outline-variant)" : "none", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-on-surface)" }}>{j.co}</div>
                    <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)" }}>{j.date} Â· {j.tail}</div>
                  </div>
                  <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)" }}>{j.from.split(" ")[0]} â†’ {j.to.split(" ")[0]}</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700, color: sc(j.conf), textAlign: "right" }}>{j.conf}%</div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* â”€â”€â”€ 3. FOOT TRAFFIC INTELLIGENCE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export const FootTraffic = () => {
  const [sel, setSel] = useState(FOOT[0]);
  const [resp, setResp] = useState("");
  const [loading, setLoading] = useState(false);
  const sc = s => ({ critical: "var(--color-error)", high: "var(--color-warning)", medium: "var(--color-secondary)", low: "var(--color-success)" }[s] || "var(--color-on-surface-variant)");

  async function gen() {
    setLoading(true); setResp("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 400,
          messages: [{ role: "user", content: `BigLaw BD AI. A client has been detected at a competitor law firm or significant third-party location.\n\nClient: ${sel.target}\nLocation detected: ${sel.loc}\nDevice cluster: ${sel.dev} devices Â· ${sel.dur}\nDate: ${sel.date}\nThreat assessment: ${sel.threat}\nSeverity: ${sel.sev.toUpperCase()}\n\nWrite a 100-word response strategy:\n1. What this likely means (RFP, active pitch, relationship-building)\n2. Which partner acts and what they say\n3. Whether to use conflict arbitrage if applicable\n4. The exact tone â€” urgent but not panicked\n\nPlain text. Direct.` }]
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
                style={{ background: isSelected ? `${c}08` : "var(--color-surface-container-lowest)", border: `1px solid ${isSelected ? `${c}35` : "var(--color-surface-container-high)"}`, borderLeft: `3px solid ${c}`, borderRadius: 4, padding: "14px 16px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, color: "var(--color-on-surface)" }}>{f.target}</div>
                  <span style={{ fontSize: 8, fontFamily: "var(--font-mono)", background: `${c}18`, border: `1px solid ${c}35`, color: c, padding: "2px 7px", borderRadius: 2 }}>{f.sev.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: 11, color: c, fontFamily: "var(--font-mono)", marginBottom: 6 }}>ðŸ“ {f.loc}</div>
                <div style={{ display: "flex", gap: 10, marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)" }}>ðŸ“± {f.dev} devices</div>
                  <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)" }}>â± {f.dur}</div>
                  <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)" }}>ðŸ“… {f.date}</div>
                </div>
                <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", padding: "8px 10px", background: "var(--color-surface-container-low)", borderRadius: 3 }}>
                  <span style={{ color: "var(--color-on-surface-variant)", fontSize: 9, fontFamily: "var(--font-mono)" }}>THREAT: </span>{f.threat}
                </div>
              </div>
            );
          })}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Action recommendation */}
          <Panel>
            <div style={{ padding: "14px 16px" }}>
              <div style={{ fontFamily: "'Newsreader',serif", fontWeight: 800, fontSize: 16, color: "var(--color-on-surface)", marginBottom: 4 }}>{sel.target}</div>
              <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginBottom: 12 }}>RECOMMENDED ACTION</div>
              <div style={{ background: "rgba(212,168,67,.05)", border: "1px solid rgba(212,168,67,.2)", borderRadius: 3, padding: "12px 14px", marginBottom: 14 }}>
                <div style={{ fontSize: 12, color: "var(--color-on-surface-variant)", lineHeight: 1.65 }}>{sel.action}</div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[["Devices Detected", `${sel.dev} clustered`], ["Duration", sel.dur], ["Detection Date", sel.date], ["Severity", sel.sev.toUpperCase()]].map(([l, v]) => (
                  <div key={l} style={{ background: "var(--color-surface-container-low)", borderRadius: 3, padding: "8px 10px" }}>
                    <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 3 }}>{l}</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-on-surface)" }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <Panel title="AI Counter-Strategy" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "â€¦" : "Generate Strategy"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : resp
                ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--color-on-surface-variant)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{resp}</div>
                : <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontStyle: "italic" }}>Generate a counter-strategy â€” who acts, what they say, whether to invoke conflict arbitrage, and the exact tone for the outreach.</div>}
            </div>
          </Panel>

          <Panel title="Detection Methodology">
            <div style={{ padding: "12px 16px" }}>
              {[
                ["Data Source", "Commercial GPS clustering (SafeGraph/Veraset)"],
                ["Detection Method", "Device concentration â‰¥5 from known client domain"],
                ["Minimum Threshold", "3+ devices Â· 45+ minute dwell time"],
                ["Update Frequency", "Near real-time Â· 15-minute lag"],
                ["False Positive Rate", "Estimated 8â€“12% (conference events, lobby meetings)"],
              ].map(([l, v]) => (
                <div key={l} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "0 0 0 1px var(--color-outline-variant)" }}>
                  <span style={{ fontSize: 10, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>{l}</span>
                  <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)", textAlign: "right", maxWidth: "55%" }}>{v}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* â”€â”€â”€ 4. SATELLITE SIGNALS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export const Satellite = () => {
  const [sel, setSel] = useState(SAT[0]);
  const [analysis, setAnalysis] = useState("");
  const [loading, setLoading] = useState(false);
  const uc = u => ({ high: "var(--color-error)", medium: "var(--color-warning)", low: "var(--color-success)" }[u] || "var(--color-secondary)");
  const tc = { "Workforce": "red", "Construction": "blue", "Supply Chain": "gold", "Environmental": "green" };

  async function gen() {
    setLoading(true); setAnalysis("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 450,
          messages: [{ role: "user", content: `BigLaw BD analyst. A satellite intelligence signal has been detected.\n\nCompany: ${sel.co}\nLocation: ${sel.loc}\nSatellite observation: ${sel.sig}\nInference: ${sel.inf}\nSignal type: ${sel.type}\nConfidence: ${sel.conf}%\nUrgency: ${sel.urg.toUpperCase()}\n\nWrite a 120-word legal exposure brief:\n1. What this satellite observation legally means for the company\n2. Which specific legal matter is almost certainly forming (be specific â€” e.g. "WSIB mass layoff filing, mandatory 8-week notice period begins")\n3. Exactly which practice group should call, what they offer, and the opening line\n4. Timeline â€” how many days until this becomes a public event\n\nDirect, specific, plain text.` }]
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
                style={{ padding: "13px 14px", borderBottom: "0 0 0 1px var(--color-outline-variant)", cursor: "pointer", background: sel.co === s.co ? "var(--color-surface-container-low)" : "transparent", borderLeft: sel.co === s.co ? "2px solid var(--gold)" : "2px solid transparent" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-on-surface)" }}>{s.co}</div>
                  <Tag label={s.type} color={tc[s.type] || "default"}/>
                </div>
                <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)", marginBottom: 5 }}>ðŸ“ {s.loc}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 8, fontFamily: "var(--font-mono)", color: c, background: `${c}15`, border: `1px solid ${c}30`, padding: "2px 6px", borderRadius: 2 }}>{s.urg.toUpperCase()}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700, color: c }}>{s.conf}%</span>
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
                  <div style={{ fontFamily: "'Newsreader',serif", fontWeight: 800, fontSize: 20, color: "var(--color-on-surface)", marginBottom: 6 }}>{sel.co}</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <Tag label={sel.type} color={tc[sel.type] || "default"}/>
                    <Tag label={sel.loc} color="default"/>
                    {sel.lead && <Tag label={`Lead: ${sel.lead}`} color="green"/>}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 44, fontWeight: 700, color: uc(sel.urg), lineHeight: 1 }}>{sel.conf}%</div>
                  <div style={{ fontSize: 8, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>CONFIDENCE</div>
                </div>
              </div>

              {/* Satellite visual placeholder */}
              <div style={{ background: "var(--color-surface-container-low)", border: "0 0 0 1px var(--color-outline-variant)", borderRadius: 3, padding: "14px", marginBottom: 12, position: "relative", overflow: "hidden", height: 90 }}>
                <div style={{ position: "absolute", inset: 0, backgroundImage: "radial-gradient(circle at 30% 40%, rgba(61,186,122,.08) 0%, transparent 60%), radial-gradient(circle at 70% 60%, rgba(74,143,255,.06) 0%, transparent 50%)", pointerEvents: "none" }}/>
                <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 8 }}>â—Ž SATELLITE OBSERVATION Â· {sel.loc.toUpperCase()}</div>
                <div style={{ fontSize: 12, color: "var(--color-on-surface-variant)", lineHeight: 1.55 }}>{sel.sig}</div>
              </div>

              <div style={{ background: "rgba(212,168,67,.04)", border: "1px solid rgba(212,168,67,.2)", borderRadius: 3, padding: "10px 12px" }}>
                <div style={{ fontSize: 9, color: "var(--color-secondary)", fontFamily: "var(--font-mono)", marginBottom: 5 }}>LEGAL INFERENCE</div>
                <div style={{ fontSize: 12, color: "var(--color-on-surface-variant)", lineHeight: 1.6 }}>{sel.inf}</div>
              </div>
            </div>
          </Panel>

          <Panel title="AI Legal Exposure Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "â€¦" : "Assess Exposure"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : analysis
                ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--color-on-surface-variant)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{analysis}</div>
                : <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontStyle: "italic" }}>Generate a legal exposure brief â€” what the satellite observation means legally, which specific matter is forming, and the exact call to make.</div>}
            </div>
          </Panel>

          <Panel title="Data Sources">
            <div style={{ padding: "10px 16px" }}>
              {[["Imagery Source", "Google Earth Engine Â· Sentinel-2 Â· Copernicus Open Access"], ["Resolution", "10m (Sentinel-2) Â· 3m (Planet Labs where licensed)"], ["Update Cadence", "Weekly revisit Â· High-urgency sites daily"], ["Detection Method", "OpenCV change detection Â· Parking lot vehicle count"], ["Free Tier", "Google Earth Engine (non-commercial) Â· Copernicus (free)"]].map(([l, v]) => (
                <div key={l} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "0 0 0 1px var(--color-outline-variant)" }}>
                  <span style={{ fontSize: 10, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>{l}</span>
                  <span style={{ fontSize: 11, color: "var(--color-on-surface-variant)", textAlign: "right", maxWidth: "55%" }}>{v}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* â”€â”€â”€ 5. PERMIT RADAR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export const PermitRadar = () => {
  const [sel, setSel] = useState(PERMITS[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const uc = u => ({ high: "var(--color-error)", medium: "var(--color-secondary)", low: "var(--color-success)" }[u] || "var(--color-primary)");
  const workColors = { Environmental: "green", Indigenous: "green", Regulatory: "blue", "Real Estate": "blue", Construction: "blue", Lender: "blue", "Lender Counsel": "blue", Employment: "gold", IP: "purple", Restructuring: "red", Finance: "cyan", "Land Use": "gold" };

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 450,
          messages: [{ role: "user", content: `BigLaw BD analyst. A significant permit filing has appeared that predicts legal work.\n\nCompany: ${sel.co}\nPermit: ${sel.permit}\nLocation: ${sel.loc}\nFiled: ${sel.filed}\nProject type: ${sel.type}\nPractice areas triggered: ${sel.work.join(", ")}\nEstimated legal value: ${sel.rev}\nUrgency: ${sel.urg.toUpperCase()}\n${sel.lead ? `Existing relationship: ${sel.lead}` : "No existing relationship â€” prospect outreach"}\n\nWrite a 120-word outreach brief:\n1. Why this permit means legal work is imminent (be specific about which legal steps are legally required)\n2. The exact sequence of legal matters this project will generate and in what order\n3. Which partner calls, what they say, and when\n4. Opening line for the call\n\nDirect, plain text.` }]
        })
      });
      const d = await r.json(); setBrief(d.content?.[0]?.text || "Error.");
    } catch { setBrief("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Geospatial Intelligence" title="Permit Radar" sub="Aggregates construction, demolition, and environmental assessment permits from municipal and provincial portals. Every major permit is a legal trigger â€” mapped to practice areas and estimated fee value."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Active Permits" val={PERMITS.length} sub="filed past 30 days" accent="blue"/>
        <Metric label="High Urgency" val={PERMITS.filter(p => p.urg === "high").length} sub="immediate action" accent="red"/>
        <Metric label="Est. Fee Value" val={`$${(PERMITS.reduce((s, p) => s + parseInt(p.rev.replace(/\$|K/g, "")), 0))}K`} sub="total legal work" accent="gold"/>
        <Metric label="Unmatched Prospects" val={PERMITS.filter(p => !p.lead).length} sub="new client opps" accent="green"/>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 12 }}>
        {/* Permit list */}
        <Panel>
          <div style={{ padding: "10px 14px", borderBottom: "0 0 0 1px var(--color-outline-variant)", fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-on-surface-variant)", letterSpacing: ".1em" }}>SORTED BY URGENCY Â· {PERMITS.length} PERMITS</div>
          {[...PERMITS].sort((a, b) => a.urg === "high" ? -1 : 1).map((p, i) => (
            <div key={i} onClick={() => { setSel(p); setBrief(""); }}
              style={{ padding: "12px 14px", borderBottom: "0 0 0 1px var(--color-outline-variant)", cursor: "pointer", background: sel.co === p.co && sel.permit === p.permit ? "var(--color-surface-container-low)" : "transparent", borderLeft: sel.co === p.co && sel.permit === p.permit ? "2px solid var(--gold)" : "2px solid transparent" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-on-surface)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>{p.co}</div>
                <span style={{ fontSize: 8, background: `${uc(p.urg)}18`, border: `1px solid ${uc(p.urg)}35`, color: uc(p.urg), padding: "2px 6px", borderRadius: 2, fontFamily: "var(--font-mono)", flexShrink: 0 }}>{p.urg.toUpperCase()}</span>
              </div>
              <div style={{ fontSize: 10, color: "var(--color-on-surface-variant)", marginBottom: 5 }}>{p.permit}</div>
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
              <div style={{ fontFamily: "'Newsreader',serif", fontWeight: 800, fontSize: 18, color: "var(--color-on-surface)", marginBottom: 4 }}>{sel.co}</div>
              <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", marginBottom: 12 }}>{sel.loc} Â· Filed {sel.filed}</div>
              <div style={{ background: "var(--color-surface-container-low)", border: "0 0 0 1px var(--color-outline-variant)", borderRadius: 3, padding: "12px 14px", marginBottom: 12 }}>
                <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 5 }}>PERMIT TYPE</div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-on-surface)", marginBottom: 4 }}>{sel.permit}</div>
                <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)" }}>{sel.type}</div>
              </div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 8 }}>LEGAL WORK TRIGGERED</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {sel.work.map(w => <Tag key={w} label={w} color={workColors[w] || "default"}/>)}
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                {[["Est. Fee Value", sel.rev, "var(--color-secondary)"], ["Urgency", sel.urg.toUpperCase(), uc(sel.urg)], ["Relationship", sel.lead || "None", sel.lead ? "var(--color-success)" : "var(--color-on-surface-variant)"]].map(([l, v, c]) => (
                  <div key={l} style={{ background: "var(--color-surface-container-low)", borderRadius: 3, padding: "8px 10px" }}>
                    <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)", marginBottom: 3 }}>{l}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: c }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <Panel title="AI Outreach Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "â€¦" : "Generate Brief"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : brief
                ? <div style={{ fontSize: 13, lineHeight: 1.75, color: "var(--color-on-surface-variant)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{brief}</div>
                : <div style={{ fontSize: 11, color: "var(--color-on-surface-variant)", fontStyle: "italic" }}>Generate an outreach brief â€” the legal sequence this project will generate, which partner calls, and the exact opening line.</div>}
            </div>
          </Panel>

          <Panel title="Data Sources â€” All Free">
            {[
              { src: "Ontario Environmental Registry", url: "ero.ontario.ca", feed: "RSS + HTML", cad: "Daily" },
              { src: "IAAC Federal Projects", url: "iaac-aeic.gc.ca/050/evaluations/proj/api", feed: "REST API", cad: "Hourly" },
              { src: "City of Toronto ePlans", url: "toronto.ca/city-government/planning-development", feed: "HTML scrape", cad: "Daily" },
              { src: "BC Environmental Assessment", url: "projects.eao.gov.bc.ca", feed: "RSS", cad: "Weekly" },
              { src: "Alberta OneStop Registry", url: "alberta.ca/SPIN2/start.do", feed: "HTML scrape", cad: "Daily" },
            ].map((s, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 80px 60px", gap: 8, padding: "8px 14px", borderBottom: "0 0 0 1px var(--color-outline-variant)", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 500, color: "var(--color-on-surface)" }}>{s.src}</div>
                  <div style={{ fontSize: 9, color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>{s.url}</div>
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
