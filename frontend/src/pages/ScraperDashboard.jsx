// src/pages/ScraperDashboard.jsx — Phase 1B live scraper health dashboard
// Polls GET /api/scrapers/summary and GET /api/scrapers/health every 60 seconds.

import { useState, useEffect, useCallback } from "react";

/* ─── Shared primitives (same design language as NewModules.jsx) ─────────── */

const StatusTag = ({ status }) => {
  const map = {
    healthy:  { bg: "rgba(61,186,122,.1)",  br: "rgba(61,186,122,.3)",   tx: "var(--green, #3dba7a)" },
    degraded: { bg: "rgba(212,168,67,.1)",  br: "rgba(212,168,67,.3)",   tx: "var(--gold,  #d4a843)" },
    failing:  { bg: "rgba(224,82,82,.1)",   br: "rgba(224,82,82,.3)",    tx: "var(--red,   #e05252)" },
    disabled: { bg: "rgba(106,137,180,.1)", br: "rgba(106,137,180,.25)", tx: "#6a89b4" },
  };
  const s = map[status] || map.disabled;
  return (
    <span style={{
      background: s.bg, border: `1px solid ${s.br}`, color: s.tx,
      fontSize: 9, fontFamily: "'JetBrains Mono',monospace", letterSpacing: ".07em",
      padding: "2px 8px", borderRadius: 2, whiteSpace: "nowrap", textTransform: "uppercase",
    }}>{status}</span>
  );
};

const Panel = ({ title, children, actions, style = {} }) => (
  <div style={{ background: "var(--card,#1a1d23)", border: "1px solid var(--border,#2a2d35)", borderRadius: 4, ...style }}>
    {title && (
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border,#2a2d35)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: "var(--t2,#8892a4)", letterSpacing: ".08em", textTransform: "uppercase" }}>{title}</span>
        {actions}
      </div>
    )}
    {children}
  </div>
);

const MetricCard = ({ label, value, color = "#7fb3ff", sub }) => (
  <div style={{ background: "var(--card,#1a1d23)", border: "1px solid var(--border,#2a2d35)", borderRadius: 4, padding: "16px 20px", minWidth: 120 }}>
    <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: "var(--t2,#8892a4)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
    <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 28, color, fontWeight: 700, lineHeight: 1 }}>{value ?? "—"}</div>
    {sub && <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: "var(--t2,#8892a4)", marginTop: 4 }}>{sub}</div>}
  </div>
);

/* ─── Helpers ────────────────────────────────────────────────────────────── */

const fmtTs = (ts) => {
  if (!ts) return "—";
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
  return `${Math.floor(diffMin / 1440)}d ago`;
};

const fmtDur = (ms) => {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

const fmtPct = (f) => (f == null ? "—" : `${(f * 100).toFixed(0)}%`);

const STATUS_PRIORITY = { failing: 0, degraded: 1, disabled: 2, healthy: 3 };

/* ─── Main Component ─────────────────────────────────────────────────────── */

export default function ScraperDashboard() {
  const [summary, setSummary] = useState(null);
  const [health, setHealth] = useState([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [sumRes, healthRes] = await Promise.all([
        fetch("/api/scrapers/summary"),
        fetch("/api/scrapers/health?limit=200"),
      ]);
      if (!sumRes.ok || !healthRes.ok) throw new Error("API error");
      const [sumJson, healthJson] = await Promise.all([sumRes.json(), healthRes.json()]);
      setSummary(sumJson);
      setHealth(healthJson);
      setError(null);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Filtered + sorted rows
  const categories = [...new Set(health.map((h) => h.scraper_category))].sort();
  const filtered = health
    .filter((h) => statusFilter === "all" || h.status === statusFilter)
    .filter((h) => categoryFilter === "all" || h.scraper_category === categoryFilter)
    .sort((a, b) => (STATUS_PRIORITY[a.status] ?? 9) - (STATUS_PRIORITY[b.status] ?? 9));

  if (loading) {
    return (
      <div style={{ padding: 32, fontFamily: "'JetBrains Mono',monospace", color: "var(--t2,#8892a4)", fontSize: 12 }}>
        Loading scraper health...
      </div>
    );
  }

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1600 }}>
      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 16, color: "var(--t1,#e8ecf4)", margin: 0, letterSpacing: ".05em" }}>
            SCRAPER HEALTH DASHBOARD
          </h1>
          <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: "var(--t2,#8892a4)", marginTop: 4 }}>
            Phase 1B · {summary?.registry_count ?? "?"} registered sources
            {lastRefresh && ` · refreshed ${fmtTs(lastRefresh.toISOString())}`}
          </div>
        </div>
        <button
          onClick={fetchData}
          style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: "var(--t2,#8892a4)", background: "transparent", border: "1px solid var(--border,#2a2d35)", borderRadius: 3, padding: "6px 14px", cursor: "pointer", letterSpacing: ".06em" }}>
          REFRESH
        </button>
      </div>

      {error && (
        <div style={{ background: "rgba(224,82,82,.1)", border: "1px solid rgba(224,82,82,.3)", borderRadius: 4, padding: "10px 16px", marginBottom: 16, fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: "#e05252" }}>
          Error: {error}
        </div>
      )}

      {/* ── Summary Metrics ── */}
      {summary && (
        <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
          <MetricCard label="Total Scrapers" value={summary.total} color="#7fb3ff" sub={`${summary.registry_count} in registry`} />
          <MetricCard label="Healthy" value={summary.healthy} color="#3dba7a" />
          <MetricCard label="Degraded" value={summary.degraded} color="#d4a843" />
          <MetricCard label="Failing" value={summary.failing} color="#e05252" />
          <MetricCard label="Disabled" value={summary.disabled} color="#6a89b4" />
        </div>
      )}

      {/* ── Filters ── */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: "var(--t2,#8892a4)" }}>STATUS:</span>
        {["all", "healthy", "degraded", "failing", "disabled"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)} style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, padding: "4px 10px", borderRadius: 2, cursor: "pointer", letterSpacing: ".06em", textTransform: "uppercase", background: statusFilter === s ? "rgba(106,137,180,.2)" : "transparent", border: `1px solid ${statusFilter === s ? "#6a89b4" : "var(--border,#2a2d35)"}`, color: statusFilter === s ? "#7fb3ff" : "var(--t2,#8892a4)" }}>
            {s}
          </button>
        ))}
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: "var(--t2,#8892a4)", marginLeft: 12 }}>CATEGORY:</span>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, background: "var(--card,#1a1d23)", border: "1px solid var(--border,#2a2d35)", color: "var(--t1,#e8ecf4)", borderRadius: 2, padding: "4px 8px", cursor: "pointer" }}>
          <option value="all">All</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: "var(--t2,#8892a4)", marginLeft: 8 }}>
          {filtered.length} scrapers
        </span>
      </div>

      {/* ── Health Table ── */}
      <Panel title={`Scraper Health (${filtered.length})`}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "'JetBrains Mono',monospace", fontSize: 11 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border,#2a2d35)" }}>
                {["Scraper", "Category", "Status", "Last Run", "Last Success", "Records", "7d Rate", "Avg Dur", "Failures"].map((h) => (
                  <th key={h} style={{ padding: "8px 12px", textAlign: "left", fontSize: 9, color: "var(--t2,#8892a4)", letterSpacing: ".07em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ padding: "24px 12px", textAlign: "center", color: "var(--t2,#8892a4)", fontSize: 11 }}>
                    No health records found. Run scrapers to populate.
                  </td>
                </tr>
              ) : filtered.map((row) => (
                <tr key={row.id} style={{ borderBottom: "1px solid rgba(42,45,53,.5)" }}>
                  <td style={{ padding: "10px 12px", color: "var(--t1,#e8ecf4)", fontWeight: 500 }}>{row.scraper_name}</td>
                  <td style={{ padding: "10px 12px", color: "var(--t2,#8892a4)" }}>{row.scraper_category}</td>
                  <td style={{ padding: "10px 12px" }}><StatusTag status={row.status} /></td>
                  <td style={{ padding: "10px 12px", color: "var(--t2,#8892a4)" }}>{fmtTs(row.last_run_at)}</td>
                  <td style={{ padding: "10px 12px", color: "var(--t2,#8892a4)" }}>{fmtTs(row.last_success_at)}</td>
                  <td style={{ padding: "10px 12px", color: "var(--t2,#8892a4)" }}>{row.records_last_run ?? "—"}</td>
                  <td style={{ padding: "10px 12px", color: row.success_rate_7d < 0.8 ? "#e05252" : "var(--t2,#8892a4)" }}>{fmtPct(row.success_rate_7d)}</td>
                  <td style={{ padding: "10px 12px", color: "var(--t2,#8892a4)" }}>{fmtDur(row.avg_run_duration_ms)}</td>
                  <td style={{ padding: "10px 12px", color: row.consecutive_failures > 0 ? "#e05252" : "var(--t2,#8892a4)" }}>{row.consecutive_failures}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
