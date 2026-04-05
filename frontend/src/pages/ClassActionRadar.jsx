/**
 * pages/ClassActionRadar.jsx — P6 Redesign
 *
 * Module #23 — risk ranking, signal convergence, live cases, and counsel matching.
 * DM Serif Display + DM Sans, tonal surfaces, no inline styles.
 */

import { useEffect, useMemo, useState } from 'react'
import AppShell from '../components/layout/AppShell'
import { classActions as classActionsApi } from '../api/client'

const RADAR_CSS = `
.car-root {
  max-width: 1320px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.car-header { margin-bottom: 2rem; }
.car-title {
  font-family: var(--font-editorial);
  font-size: 1.6rem;
  font-weight: 400;
  color: var(--color-primary);
  margin: 0 0 4px;
}
.car-subtitle {
  font-family: var(--font-data);
  color: var(--color-on-surface-variant);
  font-size: 0.875rem;
  margin: 0;
}

/* Stats */
.car-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.car-stat-card {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  padding: 16px;
  box-shadow: var(--shadow-ambient);
}
.car-stat-label {
  font-family: var(--font-data);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-on-surface-variant);
  margin-bottom: 8px;
}
.car-stat-val {
  font-family: var(--font-editorial);
  font-size: 1.8rem;
  font-weight: 400;
  color: var(--color-primary);
}

/* Sections */
.car-section {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-ambient);
}
.car-section-padded {
  padding: 18px;
}
.car-section-title {
  font-family: var(--font-data);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-on-surface-variant);
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--color-surface-container-high);
}

/* Tables */
.car-table { width: 100%; border-collapse: collapse; }
.car-th {
  text-align: left;
  padding: 12px 14px;
  font-family: var(--font-data);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-on-surface-variant);
  background: var(--color-surface-container-low);
}
.car-tr {
  cursor: pointer;
  transition: background var(--transition-fast);
  border-bottom: 1px solid var(--color-surface-container-low);
}
.car-tr:last-child { border-bottom: none; }
.car-tr:hover { background: var(--color-surface-container-high) !important; }
.car-tr.selected { background: var(--color-surface-container-low); }

.car-td {
  padding: 12px 14px;
  font-family: var(--font-data);
  font-size: 0.875rem;
  color: var(--color-on-surface);
}
.car-td-strong {
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--color-primary);
}

/* Badges & Items */
.car-badge {
  padding: 3px 8px;
  border-radius: var(--radius-full);
  background: var(--color-surface-container-high);
  color: var(--color-on-surface-variant);
  font-family: var(--font-data);
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 700;
}
.car-item {
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 8px;
  transition: background var(--transition-fast);
}
.car-item:hover { background: var(--color-surface-container-high); }
.car-item-title {
  font-family: var(--font-data);
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 4px;
}
.car-item-sub {
  font-family: var(--font-data);
  font-size: 0.75rem;
  color: var(--color-on-surface-variant);
}
.car-item-mono {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--color-secondary);
}

/* Heatmap */
.car-hm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
}
.car-hm-cell {
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  padding: 14px;
}
.car-hm-sector {
  font-family: var(--font-data);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-on-surface-variant);
  margin-bottom: 8px;
}
.car-hm-val {
  font-family: var(--font-editorial);
  font-size: 1.4rem;
  font-weight: 400;
  color: var(--color-primary);
  line-height: 1;
}
.car-hm-pct {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--color-secondary);
  margin-top: 4px;
}

@media (max-width: 980px) {
  .car-grid-main, .car-grid-sub { grid-template-columns: 1fr !important; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('car-styles')) {
    const el = document.createElement('style')
    el.id = 'car-styles'
    el.textContent = RADAR_CSS
    document.head.appendChild(el)
  }
}

function pct(value) {
  return `${((value || 0) * 100).toFixed(1)}%`
}

function TypeBadge({ type }) {
  const label = type ? type.replace(/_/g, ' ') : 'unknown'
  return <span className="car-badge">{label}</span>
}

export default function ClassActionRadar() {
  injectCSS()
  const [loading, setLoading] = useState(true)
  const [risks, setRisks] = useState([])
  const [cases, setCases] = useState([])
  const [dashboard, setDashboard] = useState(null)
  const [selectedCompanyId, setSelectedCompanyId] = useState(null)
  const [riskDetail, setRiskDetail] = useState(null)
  const [firmMatches, setFirmMatches] = useState(null)
  const [matchLoading, setMatchLoading] = useState(false)

  useEffect(() => {
    Promise.all([
      classActionsApi.risks(20),
      classActionsApi.cases(100),
      classActionsApi.dashboard(),
    ])
      .then(([riskRows, caseRows, dash]) => {
        setRisks(riskRows || [])
        setCases(caseRows || [])
        setDashboard(dash || null)
        if (riskRows?.length) setSelectedCompanyId(riskRows[0].company_id)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedCompanyId) return
    setMatchLoading(true)
    Promise.all([
      classActionsApi.riskDetail(selectedCompanyId),
      classActionsApi.match(selectedCompanyId, 5),
    ])
      .then(([detail, match]) => {
        setRiskDetail(detail || null)
        setFirmMatches(match || null)
      })
      .finally(() => setMatchLoading(false))
  }, [selectedCompanyId])

  const sectors = useMemo(() => dashboard?.sector_heatmap || [], [dashboard])
  const timeline = riskDetail?.risk?.contributing_signals || []

  return (
    <AppShell>
      <div className="car-root">
        <div className="car-header">
          <h1 className="car-title">Class Action Radar</h1>
          <p className="car-subtitle">Module #23 — risk ranking, signal convergence, live cases, and counsel matching.</p>
        </div>

        <div className="car-stats">
          <div className="car-stat-card">
            <div className="car-stat-label">Scored Companies</div>
            <div className="car-stat-val">{dashboard?.total_risk_companies ?? '—'}</div>
          </div>
          <div className="car-stat-card">
            <div className="car-stat-label">High Risk (≥70%)</div>
            <div className="car-stat-val">{dashboard?.high_risk_companies ?? '—'}</div>
          </div>
          <div className="car-stat-card">
            <div className="car-stat-label">Active Cases</div>
            <div className="car-stat-val">{dashboard?.tracked_cases_active ?? '—'}</div>
          </div>
          <div className="car-stat-card">
            <div className="car-stat-label">Indexed Law Firms</div>
            <div className="car-stat-val">{dashboard?.law_firms_indexed ?? '—'}</div>
          </div>
        </div>

        <div className="car-grid-main" style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16 }}>
          {/* Risk Table */}
          <section className="car-section">
            <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--color-surface-container-high)' }}>
              <div className="car-section-title" style={{ padding: 0, margin: 0, border: 'none' }}>Risk Table</div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="car-table">
                <thead>
                  <tr>
                    {['Company', 'Type', 'Horizon', 'Probability'].map((h) => (
                      <th key={h} className="car-th">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(loading ? [] : risks).map((row) => (
                    <tr
                      key={row.company_id}
                      onClick={() => setSelectedCompanyId(row.company_id)}
                      className={`car-tr ${selectedCompanyId === row.company_id ? 'selected' : ''}`}
                    >
                      <td className="car-td">{row.company_name}</td>
                      <td className="car-td"><TypeBadge type={row.predicted_type} /></td>
                      <td className="car-td">{row.time_horizon_days ? `${row.time_horizon_days}d` : '—'}</td>
                      <td className="car-td car-td-strong">{pct(row.class_action_probability)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Timeline */}
          <section className="car-section car-section-padded">
            <div className="car-section-title">Signal Timeline</div>
            <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: 4 }}>
              {(timeline || []).slice(0, 8).map((sig, idx) => (
                <div key={`${sig.signal_type}-${idx}`} className="car-item">
                  <div className="car-item-title">{sig.signal_type}</div>
                  <div className="car-item-sub">
                    weight:{' '}
                    <span className="car-item-mono">{(sig.weight || 0).toFixed ? sig.weight.toFixed(2) : sig.weight}</span>
                    {' · '} 
                    {sig.date ? new Date(sig.date).toLocaleDateString('en-CA') : 'n/a'}
                  </div>
                </div>
              ))}
              {!timeline?.length && <div className="car-item-sub">No convergence signals available for this company.</div>}
            </div>
          </section>
        </div>

        <div className="car-grid-sub" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
          {/* Active Cases */}
          <section className="car-section car-section-padded">
            <div className="car-section-title">Active Cases Tracker</div>
            <div style={{ maxHeight: 280, overflowY: 'auto', paddingRight: 4 }}>
              {cases.slice(0, 20).map((c) => (
                <div key={c.id} className="car-item">
                  <div className="car-item-title">{c.case_name}</div>
                  <div className="car-item-sub">{c.jurisdiction} · {c.status} · {c.case_type || 'untyped'}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Firm Match Panel */}
          <section className="car-section car-section-padded">
            <div className="car-section-title">Firm Match Panel</div>
            {matchLoading ? (
              <div className="car-item-sub">Loading firm recommendations…</div>
            ) : (
              <div style={{ display: 'grid', gap: 16 }}>
                <div>
                  <div className="car-item-sub" style={{ marginBottom: 6, fontWeight: 700, textTransform: 'uppercase' }}>Plaintiff</div>
                  {(firmMatches?.plaintiff_firms || []).slice(0, 3).map((m) => (
                    <div key={m.firm.id} className="car-item">
                      <div className="car-item-title">{m.firm.name}</div>
                      <div className="car-item-sub">match: <span className="car-item-mono">{pct(m.score)}</span></div>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="car-item-sub" style={{ marginBottom: 6, fontWeight: 700, textTransform: 'uppercase' }}>Defence</div>
                  {(firmMatches?.defence_firms || []).slice(0, 3).map((m) => (
                    <div key={m.firm.id} className="car-item">
                      <div className="car-item-title">{m.firm.name}</div>
                      <div className="car-item-sub">match: <span className="car-item-mono">{pct(m.score)}</span></div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>

        {/* Sector Heatmap */}
        <section className="car-section car-section-padded" style={{ marginTop: 16 }}>
          <div className="car-section-title">Sector Heatmap</div>
          <div className="car-hm-grid">
            {sectors.slice(0, 15).map((s) => (
              <div key={s.sector} className="car-hm-cell">
                <div className="car-hm-sector">{s.sector}</div>
                <div className="car-hm-val">{s.risk_count}</div>
                <div className="car-hm-pct">{pct(s.avg_probability)} avg prob</div>
              </div>
            ))}
          </div>
        </section>

      </div>
    </AppShell>
  )
}
