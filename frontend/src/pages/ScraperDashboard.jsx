// src/pages/ScraperDashboard.jsx — Digital Atelier scraper health dashboard
// Polls GET /api/scrapers/summary and GET /api/scrapers/health every 60 seconds.

import { useState, useEffect, useCallback } from "react";
import AppShell from "../components/layout/AppShell";

/* ── Shared primitives (Digital Atelier design system) ──────────────────── */

const StatusTag = ({ status }) => {
  const map = {
    healthy:  { bg: "var(--color-success-bg)",  tx: "var(--color-success)" },
    degraded: { bg: "var(--color-warning-bg)",  tx: "var(--color-warning)" },
    failing:  { bg: "var(--color-error-bg)",    tx: "var(--color-error)" },
    disabled: { bg: "var(--color-surface-container-high)", tx: "var(--color-on-surface-variant)" },
  };
  const s = map[status] || map.disabled;
  return (
    <span style={{
      background: s.bg, color: s.tx,
      fontSize: "0.6875rem", fontFamily: "var(--font-data)", fontWeight: 700,
      letterSpacing: ".05em",
      padding: "2px 8px", borderRadius: "var(--radius-full)", whiteSpace: "nowrap", textTransform: "uppercase",
    }}>{status}</span>
  );
};

const Panel = ({ title, children, actions, style = {} }) => (
  <div style={{
    background: "var(--color-surface-container-lowest)",
    borderRadius: "var(--radius-xl)",
    boxShadow: "var(--shadow-ambient)",
    ...style,
  }}>
    {title && (
      <div style={{
        padding: "12px 16px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        background: "var(--color-surface-container-low)",
        borderRadius: "var(--radius-xl) var(--radius-xl) 0 0",
      }}>
        <span style={{
          fontFamily: "var(--font-data)",
          fontSize: "0.6875rem",
          fontWeight: 700,
          color: "var(--color-on-surface-variant)",
          letterSpacing: ".05em",
          textTransform: "uppercase",
        }}>{title}</span>
        {actions}
      </div>
    )}
    {children}
  </div>
);

const MetricCard = ({ label, value, color = "var(--color-primary)", sub }) => (
  <div style={{
    background: "var(--color-surface-container-lowest)",
    borderRadius: "var(--radius-xl)",
    boxShadow: "var(--shadow-ambient)",
    padding: "16px 20px",
    minWidth: 120,
  }}>
    <div style={{
      fontFamily: "var(--font-data)",
      fontSize: "0.6875rem",
      fontWeight: 700,
      color: "var(--color-on-surface-variant)",
      letterSpacing: ".05em",
      textTransform: "uppercase",
      marginBottom: 8,
    }}>{label}</div>
    <div style={{
      fontFamily: "var(--font-editorial)",
      fontSize: "1.75rem",
      color,
      fontWeight: 500,
      lineHeight: 1,
      letterSpacing: "-0.01em",
    }}>{value ?? "—"}</div>
    {sub && <div style={{
      fontFamily: "var(--font-data)",
      fontSize: "0.6875rem",
      color: "var(--color-on-surface-variant)",
      marginTop: 4,
    }}>{sub}</div>}
  </div>
);

/* ── Helpers ──────────────────────────────────────────────────────────── */

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

/* ── Main Component ──────────────────────────────────────────────────── */

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
      const token = sessionStorage.getItem('bdforlaw_token')
      const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}
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
        <div style={{
          padding: 32,
          fontFamily: "var(--font-data)",
          color: "var(--color-on-surface-variant)",
          fontSize: 12,
        }}>
          Loading scraper health...
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div style={{ padding: "2.5rem 2rem", maxWidth: 1200, margin: "0 auto" }}>
        {/* ── Header ── */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20 }}>
          <div>
            <h1 style={{
              fontFamily: "var(--font-editorial)",
              fontSize: "1.5rem",
              fontWeight: 500,
              color: "var(--color-primary)",
              margin: 0,
              letterSpacing: "-0.01em",
            }}>
              Scraper Health
            </h1>
            <div style={{
              fontFamily: "var(--font-data)",
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "var(--color-on-primary-container)",
              letterSpacing: ".05em",
              textTransform: "uppercase",
              marginTop: 4,
            }}>
              {summary?.registry_count ?? "?"} registered sources
              {lastRefresh && ` · refreshed ${fmtTs(lastRefresh.toISOString())}`}
            </div>
          </div>
          <button
            onClick={fetchData}
            style={{
              fontFamily: "var(--font-data)",
              fontSize: "0.6875rem",
              fontWeight: 700,
              color: "var(--color-on-surface-variant)",
              background: "var(--color-surface-container-high)",
              borderRadius: "var(--radius-md)",
              padding: "6px 14px",
              cursor: "pointer",
              letterSpacing: ".05em",
              textTransform: "uppercase",
              transition: "background 150ms ease-out",
            }}
          >
            REFRESH
          </button>
        </div>

        {error && (
          <div style={{
            background: "var(--color-error-bg)",
            borderRadius: "var(--radius-md)",
            padding: "10px 16px",
            marginBottom: 16,
            fontFamily: "var(--font-data)",
            fontSize: 11,
            color: "var(--color-error)",
          }}>
            Error: {error}
          </div>
        )}

        {/* ── Summary Metrics ── */}
        {summary && (
          <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
            <MetricCard label="Total Scrapers" value={summary.total} color="var(--color-primary)" sub={`${summary.registry_count} in registry`} />
            <MetricCard label="Healthy" value={summary.healthy} color="var(--color-success)" />
            <MetricCard label="Degraded" value={summary.degraded} color="var(--color-warning)" />
            <MetricCard label="Failing" value={summary.failing} color="var(--color-error)" />
            <MetricCard label="Disabled" value={summary.disabled} color="var(--color-on-surface-variant)" />
          </div>
        )}

        {/* ── Filters ── */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{
            fontFamily: "var(--font-data)",
            fontSize: "0.6875rem",
            fontWeight: 700,
            color: "var(--color-on-surface-variant)",
            letterSpacing: ".05em",
            textTransform: "uppercase",
          }}>STATUS:</span>
          <div style={{
            display: "flex", gap: 4,
            background: "var(--color-surface-container-low)",
            borderRadius: "var(--radius-xl)",
            padding: 4,
          }}>
            {["all", "healthy", "degraded", "failing", "disabled"].map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)} style={{
                fontFamily: "var(--font-data)",
                fontSize: "0.6875rem",
                fontWeight: 700,
                padding: "4px 10px",
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                letterSpacing: ".05em",
                textTransform: "uppercase",
                background: statusFilter === s ? "var(--color-surface-container-lowest)" : "transparent",
                color: statusFilter === s ? "var(--color-on-surface)" : "var(--color-on-surface-variant)",
                boxShadow: statusFilter === s ? "var(--shadow-ambient)" : "none",
                transition: "background 150ms ease-out",
              }}>
                {s}
              </button>
            ))}
          </div>
          <span style={{
            fontFamily: "var(--font-data)",
            fontSize: "0.6875rem",
            fontWeight: 700,
            color: "var(--color-on-surface-variant)",
            letterSpacing: ".05em",
            textTransform: "uppercase",
            marginLeft: 8,
          }}>CATEGORY:</span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{
              fontFamily: "var(--font-data)",
              fontSize: "0.6875rem",
              background: "var(--color-surface-container-lowest)",
              outline: "1px solid rgba(197, 198, 206, 0.15)",
              color: "var(--color-on-surface)",
              borderRadius: "var(--radius-md)",
              padding: "4px 8px",
              cursor: "pointer",
            }}
          >
            <option value="all">All</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <span style={{
            fontFamily: "var(--font-data)",
            fontSize: "0.6875rem",
            color: "var(--color-on-surface-variant)",
            marginLeft: 8,
          }}>
            {filtered.length} scrapers
          </span>
        </div>

        {/* ── Health Table ── */}
        <Panel title={`Scraper Health (${filtered.length})`}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-data)", fontSize: 11 }}>
              <thead>
                <tr>
                  {["Scraper", "Category", "Status", "Last Run", "Last Success", "Records", "7d Rate", "Avg Dur", "Failures"].map((h) => (
                    <th key={h} style={{
                      padding: "8px 12px",
                      textAlign: "left",
                      fontSize: "0.6875rem",
                      fontWeight: 700,
                      color: "var(--color-on-surface-variant)",
                      letterSpacing: ".05em",
                      textTransform: "uppercase",
                      whiteSpace: "nowrap",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{
                      padding: "24px 12px",
                      textAlign: "center",
                      color: "var(--color-on-surface-variant)",
                      fontSize: 11,
                    }}>
                      No health records found. Run scrapers to populate.
                    </td>
                  </tr>
                ) : filtered.map((row, i) => (
                  <tr key={row.id} style={{
                    background: i % 2 === 1 ? "var(--color-surface-container-low)" : "transparent",
                    transition: "background 150ms ease-out",
                  }}>
                    <td style={{ padding: "10px 12px", color: "var(--color-on-surface)", fontWeight: 600 }}>{row.scraper_name}</td>
                    <td style={{ padding: "10px 12px", color: "var(--color-on-surface-variant)" }}>{row.scraper_category}</td>
                    <td style={{ padding: "10px 12px" }}><StatusTag status={row.status} /></td>
                    <td style={{ padding: "10px 12px", color: "var(--color-on-surface-variant)" }}>{fmtTs(row.last_run_at)}</td>
                    <td style={{ padding: "10px 12px", color: "var(--color-on-surface-variant)" }}>{fmtTs(row.last_success_at)}</td>
                    <td style={{ padding: "10px 12px", color: "var(--color-on-surface-variant)" }}>{row.records_last_run ?? "—"}</td>
                    <td style={{ padding: "10px 12px", color: row.success_rate_7d < 0.8 ? "var(--color-error)" : "var(--color-on-surface-variant)" }}>{fmtPct(row.success_rate_7d)}</td>
                    <td style={{ padding: "10px 12px", color: "var(--color-on-surface-variant)" }}>{fmtDur(row.avg_run_duration_ms)}</td>
                    <td style={{ padding: "10px 12px", color: row.consecutive_failures > 0 ? "var(--color-error)" : "var(--color-on-surface-variant)" }}>{row.consecutive_failures}</td>
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
