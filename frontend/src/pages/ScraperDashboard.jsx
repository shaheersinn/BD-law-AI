/**
 * pages/ScraperDashboard.jsx — P25 Redesign
 * 
 * Digital Atelier scraper health dashboard
 * Polls GET /api/scrapers/summary and GET /api/scrapers/health every 60 seconds.
 * 
 * Redesigned to use injected CSS layout architecture. Eliminates inline styles.
 */

import { useState, useEffect, useCallback } from "react";
import AppShell from "../components/layout/AppShell";

const SCRAPER_CSS = `
.scrap-root {
  padding: 2.5rem 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
.scrap-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 20px;
}
.scrap-title {
  font-family: var(--font-editorial);
  font-size: 1.75rem;
  font-weight: 500;
  color: var(--color-primary);
  margin: 0;
  letter-spacing: -0.01em;
}
.scrap-subtitle {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-primary-container);
  letter-spacing: .05em;
  text-transform: uppercase;
  margin-top: 4px;
}
.scrap-btn-refresh {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  background: var(--color-surface-container-high);
  border-radius: var(--radius-md);
  padding: 6px 14px;
  cursor: pointer;
  letter-spacing: .05em;
  text-transform: uppercase;
  transition: background var(--transition-fast);
  border: none;
}
.scrap-btn-refresh:hover {
  background: var(--color-outline-variant);
}

.scrap-error {
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  padding: 10px 16px;
  margin-bottom: 16px;
  font-family: var(--font-data);
  font-size: 0.75rem;
  color: var(--color-error);
}

.scrap-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  align-items: center;
  flex-wrap: wrap;
}
.scrap-filter-label {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  letter-spacing: .05em;
  text-transform: uppercase;
}
.scrap-filter-group {
  display: flex;
  gap: 4px;
  background: var(--color-surface-container-low);
  border-radius: var(--radius-xl);
  padding: 4px;
}
.scrap-filter-btn {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: var(--radius-md);
  cursor: pointer;
  letter-spacing: .05em;
  text-transform: uppercase;
  border: none;
  transition: background var(--transition-fast);
}

.scrap-select {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  background: var(--color-surface-container-lowest);
  outline: 1px solid rgba(197, 198, 206, 0.15);
  border: none;
  color: var(--color-on-surface);
  border-radius: var(--radius-md);
  padding: 4px 8px;
  cursor: pointer;
}

/* Status Tag */
.scrap-tag {
  font-size: 0.6875rem;
  font-family: var(--font-data);
  font-weight: 700;
  letter-spacing: .05em;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  text-transform: uppercase;
}

/* Metric / Panel */
.scrap-panel {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-ambient);
}
.scrap-panel-title {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-surface-container-low);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  letter-spacing: .05em;
  text-transform: uppercase;
}

.scrap-metric {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-ambient);
  padding: 16px 20px;
  min-width: 120px;
  flex: 1;
}
.scrap-metric-label {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  letter-spacing: .05em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.scrap-metric-val {
  font-family: var(--font-editorial);
  font-size: 1.75rem;
  fontWeight: 500;
  line-height: 1;
  letter-spacing: -0.01em;
}
.scrap-metric-sub {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  color: var(--color-on-surface-variant);
  margin-top: 4px;
}

/* Table */
.scrap-table {
  width: 100%;
  border-collapse: collapse;
}
.scrap-th {
  padding: 8px 12px;
  text-align: left;
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  letter-spacing: .05em;
  text-transform: uppercase;
  white-space: nowrap;
  font-family: var(--font-data);
}
.scrap-td {
  padding: 10px 12px;
  font-size: 0.8125rem;
  font-family: var(--font-data);
  white-space: nowrap;
}
.scrap-tr {
  transition: background var(--transition-fast);
}
.scrap-empty-td {
  padding: 24px 12px;
  text-align: center;
  color: var(--color-on-surface-variant);
  font-size: 0.8125rem;
  font-family: var(--font-data);
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('scrap-styles')) {
    const el = document.createElement('style')
    el.id = 'scrap-styles'
    el.textContent = SCRAPER_CSS
    document.head.appendChild(el)
  }
}

const StatusTag = ({ status }) => {
  const map = {
    healthy:  { bg: "var(--color-success-bg)",  tx: "var(--color-success)" },
    degraded: { bg: "var(--color-warning-bg)",  tx: "var(--color-warning)" },
    failing:  { bg: "var(--color-error-bg)",    tx: "var(--color-error)" },
    disabled: { bg: "var(--color-surface-container-high)", tx: "var(--color-on-surface-variant)" },
  };
  const s = map[status] || map.disabled;
  return (
    <span className="scrap-tag" style={{ background: s.bg, color: s.tx }}>
      {status}
    </span>
  );
};

const Panel = ({ title, children, actions, style = {} }) => (
  <div className="scrap-panel" style={style}>
    {title && (
      <div className="scrap-panel-title">
        <span>{title}</span>
        {actions}
      </div>
    )}
    {children}
  </div>
);

const MetricCard = ({ label, value, color = "var(--color-primary)", sub }) => (
  <div className="scrap-metric">
    <div className="scrap-metric-label">{label}</div>
    <div className="scrap-metric-val" style={{ color }}>{value ?? "—"}</div>
    {sub && <div className="scrap-metric-sub">{sub}</div>}
  </div>
);

const fmtTs = (ts) => {
  if (!ts) return "—";
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return \`\${diffMin}m ago\`;
  if (diffMin < 1440) return \`\${Math.floor(diffMin / 60)}h ago\`;
  return \`\${Math.floor(diffMin / 1440)}d ago\`;
};

const fmtDur = (ms) => {
  if (ms == null) return "—";
  if (ms < 1000) return \`\${Math.round(ms)}ms\`;
  return \`\${(ms / 1000).toFixed(1)}s\`;
};

const fmtPct = (f) => (f == null ? "—" : \`\${(f * 100).toFixed(0)}%\`);

const STATUS_PRIORITY = { failing: 0, degraded: 1, disabled: 2, healthy: 3 };

export default function ScraperDashboard() {
  injectCSS()
  const [summary, setSummary] = useState(null);
  const [health, setHealth] = useState([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const token = sessionStorage.getItem('bdforlaw_token')
      const authHeaders = token ? { Authorization: \`Bearer \${token}\` } : {}
      const [sumRes, healthRes] = await Promise.all([
        fetch("/api/scrapers/summary", { headers: authHeaders }),
        fetch("/api/scrapers/health?limit=200", { headers: authHeaders }),
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

  const categories = [...new Set(health.map((h) => h.scraper_category))].sort();
  const filtered = health
    .filter((h) => statusFilter === "all" || h.status === statusFilter)
    .filter((h) => categoryFilter === "all" || h.scraper_category === categoryFilter)
    .sort((a, b) => (STATUS_PRIORITY[a.status] ?? 9) - (STATUS_PRIORITY[b.status] ?? 9));

  if (loading) {
    return (
      <AppShell>
        <div style={{ padding: 32, fontFamily: "var(--font-data)", color: "var(--color-on-surface-variant)", fontSize: 12 }}>
          Loading scraper health...
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="scrap-root">
        {/* Header */}
        <div className="scrap-header">
          <div>
            <h1 className="scrap-title">Scraper Health</h1>
            <div className="scrap-subtitle">
              {summary?.registry_count ?? "?"} registered sources
              {lastRefresh && \` · refreshed \${fmtTs(lastRefresh.toISOString())}\`}
            </div>
          </div>
          <button className="scrap-btn-refresh" onClick={fetchData}>REFRESH</button>
        </div>

        {error && <div className="scrap-error">Error: {error}</div>}

        {/* Summary Metrics */}
        {summary && (
          <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
            <MetricCard label="Total Scrapers" value={summary.total} color="var(--color-primary)" sub={\`\${summary.registry_count} in registry\`} />
            <MetricCard label="Healthy" value={summary.healthy} color="var(--color-success)" />
            <MetricCard label="Degraded" value={summary.degraded} color="var(--color-warning)" />
            <MetricCard label="Failing" value={summary.failing} color="var(--color-error)" />
            <MetricCard label="Disabled" value={summary.disabled} color="var(--color-on-surface-variant)" />
          </div>
        )}

        {/* Filters */}
        <div className="scrap-filters">
          <span className="scrap-filter-label">STATUS:</span>
          <div className="scrap-filter-group">
            {["all", "healthy", "degraded", "failing", "disabled"].map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)} className="scrap-filter-btn" style={{
                background: statusFilter === s ? "var(--color-surface-container-lowest)" : "transparent",
                color: statusFilter === s ? "var(--color-on-surface)" : "var(--color-on-surface-variant)",
                boxShadow: statusFilter === s ? "var(--shadow-ambient)" : "none",
              }}>
                {s}
              </button>
            ))}
          </div>
          <span className="scrap-filter-label" style={{ marginLeft: 8 }}>CATEGORY:</span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="scrap-select"
          >
            <option value="all">All</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <span className="scrap-filter-label" style={{ marginLeft: 8, textTransform: 'none', fontWeight: 600 }}>
            {filtered.length} scrapers
          </span>
        </div>

        {/* Health Table */}
        <Panel title={\`Scraper Health (\${filtered.length})\`}>
          <div style={{ overflowX: "auto" }}>
            <table className="scrap-table">
              <thead>
                <tr>
                  {["Scraper", "Category", "Status", "Last Run", "Last Success", "Records", "7d Rate", "Avg Dur", "Failures"].map((h) => (
                    <th key={h} className="scrap-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="scrap-empty-td">
                      No health records found. Run scrapers to populate.
                    </td>
                  </tr>
                ) : filtered.map((row, i) => (
                  <tr key={row.id} className="scrap-tr" style={{ background: i % 2 === 1 ? "var(--color-surface-container-low)" : "transparent" }}>
                    <td className="scrap-td" style={{ color: "var(--color-on-surface)", fontWeight: 600 }}>{row.scraper_name}</td>
                    <td className="scrap-td" style={{ color: "var(--color-on-surface-variant)" }}>{row.scraper_category}</td>
                    <td className="scrap-td"><StatusTag status={row.status} /></td>
                    <td className="scrap-td" style={{ color: "var(--color-on-surface-variant)" }}>{fmtTs(row.last_run_at)}</td>
                    <td className="scrap-td" style={{ color: "var(--color-on-surface-variant)" }}>{fmtTs(row.last_success_at)}</td>
                    <td className="scrap-td" style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>{row.records_last_run ?? "—"}</td>
                    <td className="scrap-td" style={{ color: row.success_rate_7d < 0.8 ? "var(--color-error)" : "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>{fmtPct(row.success_rate_7d)}</td>
                    <td className="scrap-td" style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>{fmtDur(row.avg_run_duration_ms)}</td>
                    <td className="scrap-td" style={{ color: row.consecutive_failures > 0 ? "var(--color-error)" : "var(--color-on-surface-variant)", fontFamily: "var(--font-mono)" }}>{row.consecutive_failures}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
