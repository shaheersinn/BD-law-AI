import * as apiClient from "../api/client.js";
// src/pages/NewModules.jsx
// Three modules from the Missing Features guide:
// LiveTriggers · BDCoaching · GhostStudio

import { useState } from "react";

/* ─── Shared primitives ──────────────────────────────────────────────────── */
const Tag = ({ label, color = "default" }) => {
  const map = {
    default: { bg: "rgba(106,137,180,.1)", br: "rgba(106,137,180,.25)", tx: "var(--t2)" },
    red:     { bg: "rgba(224,82,82,.1)",   br: "rgba(224,82,82,.3)",    tx: "var(--red)" },
    gold:    { bg: "rgba(212,168,67,.1)",  br: "rgba(212,168,67,.3)",   tx: "var(--gold)" },
    green:   { bg: "rgba(61,186,122,.1)",  br: "rgba(61,186,122,.3)",   tx: "var(--green)" },
    blue:    { bg: "rgba(74,143,255,.1)",  br: "rgba(74,143,255,.3)",   tx: "#7fb3ff" },
    purple:  { bg: "rgba(155,109,255,.1)", br: "rgba(155,109,255,.3)",  tx: "var(--purple)" },
    cyan:    { bg: "rgba(34,201,212,.1)",  br: "rgba(34,201,212,.3)",   tx: "var(--cyan)" },
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
const TRIGGERS = [
  { id: "T001", source: "SEDAR", type: "Material Change Report",       company: "Arctis Mining Corp",       pa: "Corporate / M&A",              urgency: 88, filed: "Nov 14 · 08:45", desc: "Material change report filed — transaction underway or board-level restructuring in progress.", practice_conf: 91 },
  { id: "T002", source: "EDGAR", type: "Confidential Treatment Request",company: "Westbrook Digital Corp",   pa: "M&A — Deal Forming",           urgency: 89, filed: "Nov 14 · 06:12", desc: "CTR filed on recent 8-K — deal terms being redacted. Typically 2–8 weeks before announcement.", practice_conf: 87 },
  { id: "T003", source: "CANLII", type: "Class Action — Defendant",    company: "Caldwell Steel Works",     pa: "Litigation — Defense",          urgency: 91, filed: "Nov 13 · 14:30", desc: "Class action certification application filed. 847-person plaintiff class. Ontario Superior Court.", practice_conf: 94 },
  { id: "T004", source: "JOBS",  type: "Chief Compliance Officer — urgent", company: "Ember Financial",    pa: "Regulatory / AML",             urgency: 85, filed: "Nov 13 · 09:00", desc: "CCO role posted with 'immediate start' — compliance crisis almost certainly already underway.", practice_conf: 82 },
  { id: "T005", source: "OSC",   type: "Enforcement Notice",           company: "Centurion Pharma",         pa: "Securities / Regulatory",       urgency: 90, filed: "Nov 12 · 16:00", desc: "OSC enforcement proceeding commenced. Penalty exposure up to $5M. Counsel must be retained.", practice_conf: 95 },
  { id: "T006", source: "SEDAR", type: "Auditor Change",               company: "Vesta Retail REIT",        pa: "Governance / Fraud",           urgency: 79, filed: "Nov 12 · 11:20", desc: "Auditor changed without disclosed reason — governance dispute, fraud, or material disagreement.", practice_conf: 76 },
  { id: "T007", source: "JOBS",  type: "Senior M&A Counsel — in-house", company: "Borealis Genomics",       pa: "M&A (window closing)",          urgency: 80, filed: "Nov 11 · 07:30", desc: "In-house M&A counsel role posted. Company building internal capacity — 4–6 week window to pitch.", practice_conf: 78 },
  { id: "T008", source: "CANLII", type: "CCAA Filing",                 company: "Stellex Infrastructure",   pa: "Restructuring / Insolvency",    urgency: 94, filed: "Nov 11 · 04:15", desc: "CCAA protection filed. Monitor appointment imminent. Counsel required for all major parties.", practice_conf: 97 },
];

const PARTNERS = [
  { id: "chen",  name: "S. Chen",      role: "Partner — M&A / Securities",     topSource: "accountant_referral", topCount: 4,  staleReferrers: [{ name: "David Chen", firm: "MNP Advisory", days: 94, matters: 2, revenue: 340000 }, { name: "Sarah Park", firm: "KPMG Corporate Finance", days: 71, matters: 1, revenue: 180000 }], openFollowups: 3, fastWinRate: 74, slowWinRate: 31, lastContent: 22, bestContentType: "linkedin_post", talks6m: 1, activities: [5,3,7,4,6,8,5,4,3,7,6,9], pipeline: [1.2,1.4,1.8,1.3,2.1,1.9,2.4,1.8,2.6,2.9,3.1,3.4] },
  { id: "webb",  name: "M. Webb",      role: "Partner — Regulatory / Employment", topSource: "event",           topCount: 3,  staleReferrers: [{ name: "Tom Ross", firm: "Bennett Jones", days: 88, matters: 1, revenue: 220000 }], openFollowups: 1, fastWinRate: 81, slowWinRate: 44, lastContent: 8,  bestContentType: "article",      talks6m: 3, activities: [4,6,5,7,8,4,3,6,7,5,4,8], pipeline: [0.8,1.1,0.9,1.3,1.4,1.2,1.6,1.4,1.8,2.0,1.9,2.2] },
  { id: "park",  name: "D. Park",      role: "Partner — IP / Litigation",       topSource: "existing_client",  topCount: 6,  staleReferrers: [{ name: "Maria Santos", firm: "Deloitte Legal", days: 112, matters: 3, revenue: 510000 }, { name: "Kevin Wu", firm: "BDO Advisory", days: 78, matters: 2, revenue: 290000 }], openFollowups: 5, fastWinRate: 68, slowWinRate: 22, lastContent: 45, bestContentType: "cle_talk",     talks6m: 2, activities: [7,5,4,6,3,5,8,6,4,7,5,3], pipeline: [1.5,1.3,1.7,1.4,1.9,2.1,1.8,2.3,2.0,2.4,2.2,2.7] },
  { id: "okafor",name: "J. Okafor",    role: "Partner — Finance / Environmental", topSource: "cold_outreach",  topCount: 2,  staleReferrers: [{ name: "Angela Kim", firm: "EY Transaction Advisory", days: 67, matters: 1, revenue: 160000 }], openFollowups: 2, fastWinRate: 77, slowWinRate: 38, lastContent: 14, bestContentType: "linkedin_post", talks6m: 4, activities: [3,4,6,5,7,4,5,6,4,3,5,7], pipeline: [2.1,1.9,2.4,2.2,2.8,2.6,3.1,2.9,3.4,3.2,3.6,3.9] },
];

const WRITING_SAMPLES = {
  chen:   "The OSC's latest guidance on crypto asset disclosure isn't just a compliance checkbox — it redefines how boards think about digital asset risk. Three things every GC should flag before their next audit committee meeting.",
  webb:   "Transport Canada's new drone corridor regulations took effect this week. What most operators don't realise: the liability exposure for near-miss incidents has tripled under the new framework. Here's what your legal team needs to brief your board on.",
  park:   "We just resolved a cross-border IP dispute that took 4 years and touched 7 jurisdictions. The biggest lesson wasn't about the law — it was about which conversations to have in the first 90 days before positions harden.",
  okafor: "The Clean Electricity Regulations aren't just about electrons. Every major project financing in this sector now requires Indigenous partnership agreements before a single turbine goes up. The legal timeline on that is longer than most developers think.",
};

/* ─── 1. LIVE TRIGGERS FEED ──────────────────────────────────────────────── */
export const LiveTriggers = () => {
  const [sel, setSel] = useState(TRIGGERS[0]);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("ALL");
  const sources = ["ALL", "SEDAR", "EDGAR", "CANLII", "JOBS", "OSC"];
  const uc = u => u >= 88 ? "#e05252" : u >= 75 ? "#e07c30" : "#d4a843";
  const sc = { SEDAR: "gold", EDGAR: "blue", CANLII: "red", JOBS: "green", OSC: "red", FINTRAC: "purple" };
  const filtered = filter === "ALL" ? TRIGGERS : TRIGGERS.filter(t => t.source === filter);

  async function gen() {
    setLoading(true); setBrief("");
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 450,
          messages: [{ role: "user", content: `BigLaw BD analyst. A legal trigger signal just fired.\n\nSource: ${sel.source}\nSignal type: ${sel.type}\nCompany: ${sel.company}\nPractice area: ${sel.pa}\nUrgency: ${sel.urgency}/100\nDescription: ${sel.desc}\nFiled: ${sel.filed}\n\nWrite a 120-word partner action brief:\n1. What this signal almost certainly means for the company\n2. The specific legal matter type predicted and approximate fee\n3. Which partner should call and why them specifically\n4. The exact opening line for the call — demonstrates knowledge without revealing surveillance\n\nDirect, plain text. Partner reads on phone.` }]
        })
      });
      const d = await r.json(); setBrief(d.content?.[0]?.text || "Error.");
    } catch { setBrief("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Signal Intelligence" title="Live Trigger Feed" sub="Real-time monitoring of SEDAR+, SEC EDGAR, CanLII, job boards, and regulatory enforcement databases. Every event classified by practice area, scored for urgency, and mapped to partner action."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Live Signals" val={TRIGGERS.length} sub="past 72 hours" accent="red"/>
        <Metric label="Critical Urgency" val={TRIGGERS.filter(t => t.urgency >= 88).length} sub="≥88 — call today" accent="red"/>
        <Metric label="Sources Active" val={new Set(TRIGGERS.map(t => t.source)).size} sub="regulatory + court + jobs" accent="blue"/>
        <Metric label="Est. Pipeline" val="$4.2M" sub="if all engaged" accent="gold"/>
      </div>

      {/* Source filter */}
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {sources.map(s => (
          <button key={s} onClick={() => setFilter(s)} style={{
            padding: "4px 12px", borderRadius: 2,
            fontFamily: "'JetBrains Mono',monospace", fontSize: 9, fontWeight: 500, letterSpacing: ".07em",
            border: `1px solid ${filter === s ? "rgba(212,168,67,.4)" : "var(--border2)"}`,
            background: filter === s ? "rgba(212,168,67,.08)" : "transparent",
            color: filter === s ? "var(--gold)" : "var(--t3)", cursor: "pointer",
          }}>{s}</button>
        ))}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#3dba7a", animation: "pulse 2s ease-in-out infinite", display: "inline-block" }}/>
          <span style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>LIVE · Updated 4 min ago</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 12 }}>
        {/* Trigger feed */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {filtered.map((t) => {
            const c = uc(t.urgency);
            const isSelected = sel.id === t.id;
            return (
              <div key={t.id} onClick={() => { setSel(t); setBrief(""); }}
                style={{ background: isSelected ? `${c}06` : "var(--card)", border: `1px solid ${isSelected ? `${c}30` : "var(--border)"}`, borderLeft: `3px solid ${c}`, borderRadius: 4, padding: "13px 15px", cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <Tag label={t.source} color={sc[t.source] || "default"}/>
                    <Tag label={t.pa} color="blue"/>
                    <Tag label={t.filed} color="default"/>
                  </div>
                  <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 18, fontWeight: 700, color: c, lineHeight: 1, flexShrink: 0, marginLeft: 10 }}>{t.urgency}</div>
                </div>
                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--t1)", marginBottom: 3 }}>{t.company}</div>
                <div style={{ fontSize: 11, color: "var(--t3)", marginBottom: 6 }}>{t.type}</div>
                <div style={{ fontSize: 11, color: "var(--t2)", lineHeight: 1.5 }}>{t.desc}</div>
              </div>
            );
          })}
        </div>

        {/* Detail + AI brief */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Panel>
            <div style={{ padding: "14px 16px" }}>
              <div style={{ fontFamily: "'Syne',sans-serif", fontWeight: 800, fontSize: 16, color: "var(--t1)", marginBottom: 4 }}>{sel.company}</div>
              <div style={{ marginBottom: 10, display: "flex", gap: 5, flexWrap: "wrap" }}>
                <Tag label={sel.source} color={sc[sel.source] || "default"}/>
                <Tag label={sel.type} color="gold"/>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
                {[["Practice Area", sel.pa], ["Urgency Score", `${sel.urgency}/100`], ["PA Confidence", `${sel.practice_conf}%`], ["Filed", sel.filed]].map(([l, v]) => (
                  <div key={l} style={{ background: "var(--elevated)", borderRadius: 3, padding: "8px 10px" }}>
                    <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 2 }}>{l}</div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: "var(--t1)" }}>{v}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 11, color: "var(--t2)", lineHeight: 1.6, padding: "10px 12px", background: "var(--elevated)", borderRadius: 3 }}>{sel.desc}</div>
            </div>
          </Panel>

          <Panel title="AI Partner Brief" actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading ? "…" : "Generate Brief"}</OBtn></div>}>
            <div style={{ padding: "12px 16px" }}>
              {loading ? <Spinner/> : brief
                ? <div style={{ fontSize: 12, lineHeight: 1.75, color: "var(--t2)", borderLeft: "2px solid var(--gold)", paddingLeft: 14 }}>{brief}</div>
                : <div style={{ fontSize: 11, color: "var(--t3)", fontStyle: "italic" }}>Select a trigger and generate a partner brief — what this signal means, which matter is forming, who calls, and the exact opening line.</div>}
            </div>
          </Panel>

          <Panel title="Urgency Scale">
            <div style={{ padding: "10px 14px" }}>
              {[["95–100", "CRITICAL", "#e05252", "Call today — mandate almost certainly forming"],["80–94", "HIGH", "#e07c30", "Call this week — strong signal convergence"],["65–79", "MODERATE", "#d4a843", "Monitor — add to weekly BD meeting"],["50–64", "WATCH", "#4a8fff", "Emerging — begin relationship warming"]].map(([r, l, c, d]) => (
                <div key={r} style={{ display: "grid", gridTemplateColumns: "60px 80px 1fr", gap: 8, padding: "7px 0", borderBottom: "1px solid var(--border)", alignItems: "center" }}>
                  <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: c }}>{r}</span>
                  <span style={{ fontSize: 9, background: `${c}15`, border: `1px solid ${c}30`, color: c, padding: "2px 6px", borderRadius: 2, textAlign: "center", fontFamily: "'JetBrains Mono',monospace" }}>{l}</span>
                  <span style={{ fontSize: 10, color: "var(--t3)" }}>{d}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── 2. BD BEHAVIOURAL COACHING ENGINE ──────────────────────────────────── */
export const BDCoaching = () => {
  const [selPartner, setSelPartner] = useState(PARTNERS[0]);
  const [coaching, setCoaching] = useState("");
  const [loading, setLoading] = useState(false);

  async function gen() {
    setLoading(true); setCoaching("");
    const p = selPartner;
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 600,
          messages: [{ role: "user", content: `You are a BigLaw BD performance coach. Analyse this partner's data and write 4 specific coaching observations. Each must cite the actual numbers. Each must end with a concrete action for THIS WEEK — not 'consider', not 'you might want to', but a specific directive.\n\nPartner: ${p.name} (${p.role})\n\nTop referral source: ${p.topSource} (${p.topCount} matters)\nStale referral contacts: ${p.staleReferrers.map(r => `${r.name} at ${r.firm} — ${r.days} days silent, sent ${r.matters} matter(s) worth $${(r.revenue/1000).toFixed(0)}K`).join("; ")}\nOpen follow-ups unresolved: ${p.openFollowups}\nFast follow-up win rate (within 48h): ${p.fastWinRate}%\nSlow follow-up win rate (>48h): ${p.slowWinRate}%\nDays since last content published: ${p.lastContent}\nBest performing content type: ${p.bestContentType}\nConference/CLE talks in 6 months: ${p.talks6m}\n\nStyle: direct, specific, respectful. Like a great coach, not a consultant. Max 280 words. Plain text, no headers.` }]
        })
      });
      const d = await r.json(); setCoaching(d.content?.[0]?.text || "Error.");
    } catch { setCoaching("API error."); }
    setLoading(false);
  }

  const p = selPartner;
  const maxAct = Math.max(...p.activities);
  const maxPipe = Math.max(...p.pipeline);
  const months = ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May"];

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="BD Performance" title="BD Behavioural Coaching Engine" sub="Tracks what BD activities each partner actually does and correlates them with revenue. Like a Whoop ring for business development — not 'do more BD' but 'your last four matters came from accountants and you haven't met one in 94 days.'"/>
      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 14 }}>
        {/* Partner selector */}
        <div>
          <Panel style={{ marginBottom: 12 }}>
            <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)", fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: "var(--t3)", letterSpacing: ".1em" }}>SELECT PARTNER</div>
            {PARTNERS.map(p => (
              <div key={p.id} onClick={() => { setSelPartner(p); setCoaching(""); }}
                style={{ padding: "11px 13px", borderBottom: "1px solid var(--border)", cursor: "pointer", background: selPartner.id === p.id ? "var(--elevated)" : "transparent", borderLeft: selPartner.id === p.id ? "2px solid var(--gold)" : "2px solid transparent" }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--t1)" }}>{p.name}</div>
                <div style={{ fontSize: 9, color: "var(--t3)", marginTop: 2 }}>{p.role}</div>
              </div>
            ))}
          </Panel>

          <Panel title="BD Activity Score" style={{ marginBottom: 12 }}>
            <div style={{ padding: "12px 14px" }}>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 32, fontWeight: 700, color: "var(--gold)", lineHeight: 1, marginBottom: 4 }}>{p.activities[p.activities.length - 1]}</div>
              <div style={{ fontSize: 9, color: "var(--t3)" }}>activities this month</div>
              <div style={{ marginTop: 12, height: 40, display: "flex", alignItems: "flex-end", gap: 3 }}>
                {p.activities.map((a, i) => (
                  <div key={i} style={{ flex: 1, height: `${(a / maxAct) * 100}%`, background: i === p.activities.length - 1 ? "var(--gold)" : "var(--border2)", borderRadius: 1, transition: "height .4s" }}/>
                ))}
              </div>
              <div style={{ fontSize: 8, color: "var(--t4)", fontFamily: "'JetBrains Mono',monospace", marginTop: 4 }}>12-month activity</div>
            </div>
          </Panel>

          <Panel title="Follow-Up Speed Impact">
            <div style={{ padding: "12px 14px" }}>
              {[["Within 48 hrs", p.fastWinRate, "var(--green)"], ["After 48 hrs", p.slowWinRate, "var(--red)"]].map(([l, v, c]) => (
                <div key={l} style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 10, color: "var(--t3)" }}>{l}</span>
                    <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: c, fontWeight: 600 }}>{v}% win rate</span>
                  </div>
                  <div style={{ height: 4, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
                    <div style={{ width: `${v}%`, height: "100%", background: c, borderRadius: 2 }}/>
                  </div>
                </div>
              ))}
              <div style={{ fontSize: 10, color: "var(--t3)", marginTop: 4, lineHeight: 1.5 }}>
                Δ {p.fastWinRate - p.slowWinRate}pp advantage — fast follow-up is the single highest-impact behaviour.
              </div>
            </div>
          </Panel>
        </div>

        {/* Main coaching panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {/* Stale referrers — most important insight */}
          <Panel title="Referral Relationships Gone Cold">
            <div style={{ padding: "12px 16px" }}>
              {p.staleReferrers.map((ref, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "rgba(224,82,82,.04)", border: "1px solid rgba(224,82,82,.2)", borderRadius: 3, marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--t1)" }}>{ref.name}</div>
                    <div style={{ fontSize: 10, color: "var(--t3)" }}>{ref.firm} · {ref.matters} matter(s) sent · ${(ref.revenue / 1000).toFixed(0)}K revenue</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 22, fontWeight: 700, color: "var(--red)", lineHeight: 1 }}>{ref.days}d</div>
                    <div style={{ fontSize: 8, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>SINCE CONTACT</div>
                  </div>
                </div>
              ))}
              {p.staleReferrers.length === 0 && <div style={{ fontSize: 11, color: "var(--t3)", fontStyle: "italic" }}>No stale referral relationships detected.</div>}
            </div>
          </Panel>

          {/* Stats grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 }}>
            <Metric label="Top Source" val={p.topSource.replace("_", " ").toUpperCase().slice(0,12)} sub={`${p.topCount} matters via this channel`} accent="gold"/>
            <Metric label="Open Follow-Ups" val={p.openFollowups} sub="unresolved past meetings" accent={p.openFollowups >= 4 ? "red" : "gold"}/>
            <Metric label="Last Content" val={`${p.lastContent}d`} sub={`best type: ${p.bestContentType.replace("_", " ")}`} accent={p.lastContent > 30 ? "red" : "green"}/>
            <Metric label="CLE Talks" val={p.talks6m} sub="past 6 months" accent={p.talks6m >= 3 ? "green" : "gold"}/>
          </div>

          {/* Pipeline trend */}
          <Panel title={`${p.name} — Pipeline Trend (12 Months)`}>
            <div style={{ padding: "12px 16px" }}>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 80 }}>
                {p.pipeline.map((v, i) => (
                  <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                    <div style={{ width: "100%", height: `${(v / maxPipe) * 70}px`, background: i === p.pipeline.length - 1 ? "var(--gold)" : "var(--border2)", borderRadius: "2px 2px 0 0", transition: "height .5s" }}/>
                    <span style={{ fontSize: 7, color: "var(--t4)", fontFamily: "'JetBrains Mono',monospace" }}>{months[i]}</span>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          {/* AI Coaching Brief */}
          <Panel title={`AI Coaching Brief — ${p.name}`} actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/><OBtn onClick={gen} disabled={loading}>{loading ? "Processing…" : "◈ Generate Coaching Brief"}</OBtn></div>}>
            <div style={{ padding: "14px 16px" }}>
              {loading ? <Spinner/> : coaching
                ? <div style={{ fontSize: 13, lineHeight: 1.85, color: "var(--t2)" }}>{coaching}</div>
                : <div style={{ fontSize: 11, color: "var(--t3)", fontStyle: "italic", lineHeight: 1.7 }}>Generate a personalised coaching brief — 4 specific observations, each citing actual numbers, each ending with a concrete action for this week. Like a great coach, not a consultant.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── 3. THOUGHT LEADERSHIP GHOST STUDIO ─────────────────────────────────── */
export const GhostStudio = () => {
  const [selPartner, setSelPartner] = useState(PARTNERS[0]);
  const [topic, setTopic] = useState("");
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("draft");
  const [inquiry, setInquiry] = useState({ date: "", company: "", industry: "", source: "linkedin" });
  const [saved, setSaved] = useState(false);

  const NEWS_TOPICS = [
    { title: "OSC guidance on AI-generated disclosure documents", area: "Securities", hot: true },
    { title: "OSFI finalises Basel IV capital framework for Schedule I banks", area: "Banking", hot: true },
    { title: "Competition Bureau blocks Couche-Tard merger — new threshold guidance", area: "M&A", hot: false },
    { title: "Federal Carbon Tax ruling — constitutional implications for provinces", area: "Environmental", hot: false },
    { title: "PIPEDA reform passes second reading — new breach notification timelines", area: "Privacy", hot: true },
    { title: "TSX proposes new listing standards for crypto-adjacent issuers", area: "Securities", hot: false },
  ];

  async function genDraft() {
    if (!topic.trim()) return;
    setLoading(true); setDraft("");
    const p = selPartner;
    try {
      const r = await fetch("/api/anthropic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 550,
          messages: [{ role: "user", content: `You are ghostwriting a LinkedIn post for ${p.name}, ${p.role} at a leading Canadian law firm.\n\nTheir writing style — match this exactly:\n"${WRITING_SAMPLES[p.id]}"\n\nDevelopment to write about:\n${topic}\n\nRules:\n- 200 to 260 words exactly\n- Open with the practical business implication for GCs and CLOs — NOT with 'I am pleased to share' or 'Excited to announce'\n- One concrete takeaway or action for the reader\n- End with a question that prompts comments\n- Maximum 3 hashtags, placed at the very end\n- Sound like a senior practitioner writing to peers — not a law firm press release\n- Do not use: 'game-changer', 'exciting', 'thrilled', 'proud to', 'unpacking', 'deep dive'\n\nOutput the post only. No preamble.` }]
        })
      });
      const d = await r.json(); setDraft(d.content?.[0]?.text || "Error.");
    } catch { setDraft("API error."); }
    setLoading(false);
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "20px 24px" }}>
      <PageHeader tag="Thought Leadership" title="Ghost Studio" sub="AI-powered content production tied to a visibility attribution loop. Monitors what GCs are reading, drafts posts in each partner's voice, and tracks which content generates actual client inquiries."/>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10, marginBottom: 16 }}>
        <Metric label="Partners Active" val={PARTNERS.length} sub="content profiles built" accent="blue"/>
        <Metric label="Drafts This Week" val="11" sub="sent to partners 6am" accent="gold"/>
        <Metric label="Attributed Inquiries" val="3" sub="content → client call" accent="green"/>
        <Metric label="Avg Time to Post" val="4 min" sub="review + publish" accent="cyan"/>
      </div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {[{ k: "draft", l: "Draft Generator" }, { k: "news", l: "GC Topic Intelligence" }, { k: "attribution", l: "Attribution Log" }].map(t => (
          <button key={t.k} onClick={() => setTab(t.k)} style={{
            padding: "5px 14px", borderRadius: 2,
            fontFamily: "'JetBrains Mono',monospace", fontSize: 9, fontWeight: 500, letterSpacing: ".07em",
            border: `1px solid ${tab === t.k ? "rgba(212,168,67,.35)" : "transparent"}`,
            background: tab === t.k ? "rgba(212,168,67,.08)" : "transparent",
            color: tab === t.k ? "var(--gold)" : "var(--t2)", cursor: "pointer",
          }}>{t.l}</button>
        ))}
      </div>

      {tab === "draft" && (
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 12 }}>
          {/* Partner + topic selector */}
          <div>
            <Panel style={{ marginBottom: 12 }}>
              <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)", fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: "var(--t3)", letterSpacing: ".1em" }}>PARTNER VOICE</div>
              {PARTNERS.map(p => (
                <div key={p.id} onClick={() => { setSelPartner(p); setDraft(""); }}
                  style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)", cursor: "pointer", background: selPartner.id === p.id ? "var(--elevated)" : "transparent", borderLeft: selPartner.id === p.id ? "2px solid var(--gold)" : "2px solid transparent" }}>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "var(--t1)" }}>{p.name}</div>
                  <div style={{ fontSize: 9, color: "var(--t3)", marginTop: 1 }}>{p.role.split(" — ")[1]}</div>
                </div>
              ))}
            </Panel>
            <Panel title="Writing Sample">
              <div style={{ padding: "10px 12px" }}>
                <div style={{ fontSize: 11, color: "var(--t2)", lineHeight: 1.65, fontStyle: "italic" }}>"{WRITING_SAMPLES[selPartner.id]}"</div>
              </div>
            </Panel>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Panel title="Topic Input — Paste Any Regulatory Update or Legal Development" actions={<AiBadge/>}>
              <div style={{ padding: "14px 16px" }}>
                <textarea
                  value={topic}
                  onChange={e => { setTopic(e.target.value); setDraft(""); }}
                  placeholder="Paste a regulatory update, court decision, or legal development. Or click one of the trending topics below..."
                  style={{ width: "100%", background: "var(--elevated)", border: "1px solid var(--border2)", color: "var(--t1)", padding: "10px 12px", borderRadius: 3, fontSize: 12, outline: "none", resize: "none", lineHeight: 1.65, marginBottom: 10 }}
                  rows={5}
                />
                {/* Quick-select trending topics */}
                <div style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginBottom: 8 }}>TRENDING IN YOUR PRACTICE AREAS</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 5, marginBottom: 12 }}>
                  {NEWS_TOPICS.map((n, i) => (
                    <div key={i} onClick={() => { setTopic(n.title); setDraft(""); }}
                      style={{ display: "flex", gap: 8, alignItems: "center", padding: "7px 9px", background: "var(--elevated)", border: "1px solid var(--border)", borderRadius: 3, cursor: "pointer" }}>
                      {n.hot && <span style={{ fontSize: 8, color: "var(--red)", fontFamily: "'JetBrains Mono',monospace", flexShrink: 0 }}>HOT</span>}
                      <span style={{ fontSize: 11, color: "var(--t2)" }}>{n.title}</span>
                      <Tag label={n.area} color="blue" style={{ marginLeft: "auto", flexShrink: 0 }}/>
                    </div>
                  ))}
                </div>
                <OBtn onClick={genDraft} disabled={loading || !topic.trim()} style={{ width: "100%" }}>
                  {loading ? "Drafting in Voice…" : `◈ Draft Post for ${selPartner.name}`}
                </OBtn>
              </div>
            </Panel>

            {(loading || draft) && (
              <Panel title={`Draft Post — ${selPartner.name}'s Voice`} actions={<div style={{ display: "flex", gap: 6 }}><AiBadge/>{draft && <OBtn small secondary onClick={genDraft}>Regenerate</OBtn>}{draft && <OBtn small onClick={() => navigator.clipboard?.writeText(draft)}>Copy</OBtn>}</div>}>
                <div style={{ padding: "14px 16px" }}>
                  {loading ? <Spinner/> : (
                    <div>
                      <div style={{ background: "var(--elevated)", border: "1px solid var(--border)", borderRadius: 3, padding: "14px 16px", marginBottom: 10 }}>
                        <pre style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 13, lineHeight: 1.8, color: "var(--t2)", whiteSpace: "pre-wrap", margin: 0 }}>{draft}</pre>
                      </div>
                      <div style={{ fontSize: 10, color: "var(--t3)" }}>
                        ~{draft.split(/\s+/).length} words · Review, personalise the opening if needed, then post
                      </div>
                    </div>
                  )}
                </div>
              </Panel>
            )}
          </div>
        </div>
      )}

      {tab === "news" && (
        <Panel title="What GCs and CLOs Are Actually Reading This Week">
          <div style={{ padding: "14px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--t3)", marginBottom: 14, lineHeight: 1.65 }}>
              Partners typically write about what impresses other lawyers. GCs want to read about what keeps them up at night — regulatory pressure, board risk, cost control. The topics below are drawn from ACC and CCCA feeds, sourced to what in-house counsel are engaging with.
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {[
                { topic: "AI liability in contract disputes — who's responsible when the model gets it wrong?", src: "ACC CLO Survey", eng: "High", pa: "Technology / Litigation" },
                { topic: "Outside counsel cost reduction — what's actually working in 2025", src: "CCCA Insights", eng: "Very High", pa: "All Practice Areas" },
                { topic: "Board ESG disclosure liability — when does oversight become negligence?", src: "ACC Docket", eng: "High", pa: "Securities / Governance" },
                { topic: "Cybersecurity incident response — why your 72-hour window starts earlier than you think", src: "CCCA Webinar", eng: "Very High", pa: "Privacy / Cyber" },
                { topic: "Cross-border enforcement coordination — US DOJ + EU DG Competition joint cases", src: "ACC Global", eng: "Medium", pa: "Competition / Litigation" },
                { topic: "Workforce AI tools — employment law exposure your HR team isn't thinking about", src: "CCCA Survey", eng: "High", pa: "Employment" },
              ].map((item, i) => (
                <div key={i} style={{ background: "var(--elevated)", border: "1px solid var(--border)", borderRadius: 3, padding: "12px 13px" }}>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "var(--t1)", marginBottom: 6, lineHeight: 1.45 }}>{item.topic}</div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <Tag label={item.src} color="default"/>
                    <Tag label={item.pa} color="blue"/>
                    <span style={{ fontSize: 9, color: item.eng === "Very High" ? "var(--green)" : item.eng === "High" ? "var(--gold)" : "var(--t3)", fontFamily: "'JetBrains Mono',monospace", marginLeft: "auto" }}>↑ {item.eng}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      )}

      {tab === "attribution" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Panel title="Log New Client Inquiry" actions={<AiBadge/>}>
            <div style={{ padding: "14px 16px" }}>
              <div style={{ fontSize: 11, color: "var(--t3)", lineHeight: 1.7, marginBottom: 14 }}>
                When a new inquiry arrives, log it here. The system checks whether any content was published in the 14 days before the inquiry and attributes accordingly. Over time this builds a content-to-revenue attribution dataset.
              </div>
              {[["Inquiry Date", "date", "2025-11-14", "date"], ["Company", "text", "e.g. Arctis Mining Corp", "company"], ["Industry", "text", "e.g. Oil & Gas", "industry"]].map(([l, t, p, k]) => (
                <div key={k} style={{ marginBottom: 10 }}>
                  <label style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", display: "block", marginBottom: 4, letterSpacing: ".07em" }}>{l.toUpperCase()}</label>
                  <input type={t} placeholder={p} value={inquiry[k]} onChange={e => setInquiry(i => ({ ...i, [k]: e.target.value }))}
                    style={{ width: "100%", background: "var(--elevated)", border: "1px solid var(--border2)", color: "var(--t1)", padding: "7px 10px", borderRadius: 3, fontSize: 12, outline: "none" }}/>
                </div>
              ))}
              <div style={{ marginBottom: 14 }}>
                <label style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace", display: "block", marginBottom: 4 }}>HOW DID THEY REACH OUT?</label>
                <div style={{ display: "flex", gap: 6 }}>
                  {["linkedin", "article", "referral", "cold", "event"].map(s => (
                    <button key={s} onClick={() => setInquiry(i => ({ ...i, source: s }))} style={{
                      padding: "4px 10px", borderRadius: 2, fontSize: 9,
                      fontFamily: "'JetBrains Mono',monospace",
                      border: `1px solid ${inquiry.source === s ? "rgba(212,168,67,.4)" : "var(--border2)"}`,
                      background: inquiry.source === s ? "rgba(212,168,67,.08)" : "transparent",
                      color: inquiry.source === s ? "var(--gold)" : "var(--t3)", cursor: "pointer",
                    }}>{s}</button>
                  ))}
                </div>
              </div>
              <OBtn onClick={() => setSaved(true)} style={{ width: "100%" }}>Log Inquiry</OBtn>
              {saved && <div style={{ marginTop: 10, padding: "8px 10px", background: "rgba(61,186,122,.06)", border: "1px solid rgba(61,186,122,.25)", borderRadius: 3, fontSize: 11, color: "var(--green)" }}>✓ Logged. Checked for content attribution in 14-day lookback window.</div>}
            </div>
          </Panel>

          <Panel title="Attribution Report — Content → Revenue">
            <div style={{ padding: "14px 16px" }}>
              {[
                { title: "OSFI B-20 amendment take — what it means for your mortgage portfolio", type: "linkedin_post", partner: "S. Chen", inquiries: 2, date: "Nov 01" },
                { title: "Clean Electricity Regulations — what project sponsors are missing on Indigenous consultation", type: "linkedin_post", partner: "J. Okafor", inquiries: 1, date: "Oct 22" },
                { title: "CBA Annual — Cross-border IP enforcement panel recap", type: "cle_talk", partner: "D. Park", inquiries: 1, date: "Oct 15" },
              ].map((p, i) => (
                <div key={i} style={{ padding: "10px 12px", background: "var(--elevated)", border: "1px solid var(--border)", borderRadius: 3, marginBottom: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, color: "var(--t1)", marginBottom: 4 }}>{p.title}</div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <Tag label={p.type.replace("_", " ")} color="blue"/>
                    <Tag label={p.partner} color="gold"/>
                    <span style={{ fontSize: 9, color: "var(--t3)", fontFamily: "'JetBrains Mono',monospace" }}>{p.date}</span>
                    <span style={{ marginLeft: "auto", fontFamily: "'JetBrains Mono',monospace", fontSize: 14, fontWeight: 700, color: "var(--green)" }}>{p.inquiries} inquiry</span>
                  </div>
                </div>
              ))}
              <div style={{ padding: "10px 12px", background: "rgba(212,168,67,.04)", border: "1px solid rgba(212,168,67,.15)", borderRadius: 3, fontSize: 11, color: "var(--t3)", lineHeight: 1.65 }}>
                Content to which no inquiry has been attributed will appear here as you log more inquiries. Attribution window: 14 days before each inquiry date.
              </div>
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
};
