import { useEffect, useMemo, useState } from 'react'
import AppShell from '../components/layout/AppShell'
import { classActions as classActionsApi } from '../api/client'

function pct(value) {
  return `${((value || 0) * 100).toFixed(1)}%`
}

function TypeBadge({ type }) {
  const label = type ? type.replaceAll('_', ' ') : 'unknown'
  return (
    <span style={{
      padding: '2px 8px',
      borderRadius: 999,
      background: 'var(--color-surface-container-high)',
      color: 'var(--color-on-surface-variant)',
      fontSize: '0.6875rem',
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      fontWeight: 700,
    }}>
      {label}
    </span>
  )
}

export default function ClassActionRadar() {
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
      <div style={{ maxWidth: 1320, margin: '0 auto', padding: '2rem' }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <h1 style={{ fontFamily: 'var(--font-editorial)', color: 'var(--color-primary)', marginBottom: 4 }}>
            Class Action Radar
          </h1>
          <p style={{ color: 'var(--color-on-surface-variant)', fontSize: '0.875rem' }}>
            Module #23 — risk ranking, signal convergence, live cases, and counsel matching.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(140px, 1fr))', gap: 12, marginBottom: 16 }}>
          <div style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: '0.6875rem', color: 'var(--color-on-surface-variant)' }}>Scored Companies</div>
            <div style={{ fontSize: '1.5rem', color: 'var(--color-primary)' }}>{dashboard?.total_risk_companies ?? '—'}</div>
          </div>
          <div style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: '0.6875rem', color: 'var(--color-on-surface-variant)' }}>High Risk (≥70%)</div>
            <div style={{ fontSize: '1.5rem', color: 'var(--color-primary)' }}>{dashboard?.high_risk_companies ?? '—'}</div>
          </div>
          <div style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: '0.6875rem', color: 'var(--color-on-surface-variant)' }}>Active Cases</div>
            <div style={{ fontSize: '1.5rem', color: 'var(--color-primary)' }}>{dashboard?.tracked_cases_active ?? '—'}</div>
          </div>
          <div style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: '0.6875rem', color: 'var(--color-on-surface-variant)' }}>Indexed Law Firms</div>
            <div style={{ fontSize: '1.5rem', color: 'var(--color-primary)' }}>{dashboard?.law_firms_indexed ?? '—'}</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16 }}>
          <section style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: 14, borderBottom: '1px solid var(--color-surface-container-high)' }}>
              <strong>Risk Table</strong>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-container-low)' }}>
                  {['Company', 'Type', 'Horizon', 'Probability'].map((h) => (
                    <th key={h} style={{ textAlign: 'left', padding: 10, fontSize: '0.6875rem', color: 'var(--color-on-surface-variant)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(loading ? [] : risks).map((row) => (
                  <tr
                    key={row.company_id}
                    onClick={() => setSelectedCompanyId(row.company_id)}
                    style={{
                      cursor: 'pointer',
                      background: selectedCompanyId === row.company_id ? 'var(--color-surface-container-low)' : 'transparent',
                    }}
                  >
                    <td style={{ padding: 10 }}>{row.company_name}</td>
                    <td style={{ padding: 10 }}><TypeBadge type={row.predicted_type} /></td>
                    <td style={{ padding: 10 }}>{row.time_horizon_days ? `${row.time_horizon_days}d` : '—'}</td>
                    <td style={{ padding: 10, fontWeight: 700 }}>{pct(row.class_action_probability)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, padding: 14 }}>
            <strong>Signal Timeline</strong>
            <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
              {(timeline || []).slice(0, 8).map((sig, idx) => (
                <div key={`${sig.signal_type}-${idx}`} style={{ background: 'var(--color-surface-container-low)', borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700 }}>{sig.signal_type}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-on-surface-variant)' }}>
                    weight: {(sig.weight || 0).toFixed ? sig.weight.toFixed(2) : sig.weight} · {sig.date ? new Date(sig.date).toLocaleDateString('en-CA') : 'n/a'}
                  </div>
                </div>
              ))}
              {!timeline?.length && <div style={{ color: 'var(--color-on-surface-variant)', fontSize: '0.8125rem' }}>No convergence signals available for this company.</div>}
            </div>
          </section>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
          <section style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, padding: 14 }}>
            <strong>Active Cases Tracker</strong>
            <div style={{ marginTop: 10, display: 'grid', gap: 8, maxHeight: 280, overflow: 'auto' }}>
              {cases.slice(0, 20).map((c) => (
                <div key={c.id} style={{ background: 'var(--color-surface-container-low)', borderRadius: 8, padding: 10 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.8125rem' }}>{c.case_name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-on-surface-variant)' }}>
                    {c.jurisdiction} · {c.status} · {c.case_type || 'untyped'}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, padding: 14 }}>
            <strong>Firm Match Panel</strong>
            {matchLoading ? (
              <div style={{ marginTop: 10, color: 'var(--color-on-surface-variant)' }}>Loading firm recommendations…</div>
            ) : (
              <div style={{ marginTop: 10, display: 'grid', gap: 12 }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-on-surface-variant)', marginBottom: 6 }}>Plaintiff</div>
                  {(firmMatches?.plaintiff_firms || []).slice(0, 3).map((m) => (
                    <div key={m.firm.id} style={{ padding: 8, background: 'var(--color-surface-container-low)', borderRadius: 8, marginBottom: 6 }}>
                      <div style={{ fontWeight: 700, fontSize: '0.8125rem' }}>{m.firm.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-on-surface-variant)' }}>match: {pct(m.score)}</div>
                    </div>
                  ))}
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-on-surface-variant)', marginBottom: 6 }}>Defence</div>
                  {(firmMatches?.defence_firms || []).slice(0, 3).map((m) => (
                    <div key={m.firm.id} style={{ padding: 8, background: 'var(--color-surface-container-low)', borderRadius: 8, marginBottom: 6 }}>
                      <div style={{ fontWeight: 700, fontSize: '0.8125rem' }}>{m.firm.name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-on-surface-variant)' }}>match: {pct(m.score)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>

        <section style={{ background: 'var(--color-surface-container-lowest)', borderRadius: 12, padding: 14, marginTop: 16 }}>
          <strong>Sector Heatmap</strong>
          <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'repeat(5, minmax(100px, 1fr))', gap: 8 }}>
            {sectors.slice(0, 15).map((s) => (
              <div key={s.sector} style={{ background: 'var(--color-surface-container-low)', borderRadius: 8, padding: 10 }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-on-surface-variant)' }}>{s.sector}</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-primary)' }}>{s.risk_count}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-on-surface-variant)' }}>{pct(s.avg_probability)}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  )
}
