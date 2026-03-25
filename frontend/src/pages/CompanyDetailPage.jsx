/**
 * pages/CompanyDetailPage.jsx — ConstructLex Pro company detail.
 *
 * Changes from Phase 8A:
 * - AppShell layout
 * - Skeleton loading instead of plain "Loading…"
 * - Stats bar with ConstructLex card styling
 * - ScoreMatrix with sparklines prop
 * - Velocity + anomaly badges
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { companies as companiesApi, signals as signalsApi } from '../api/client'
import ScoreMatrix    from '../components/ScoreMatrix'
import SignalFeed     from '../components/SignalFeed'
import VelocityBadge  from '../components/VelocityBadge'
import AppShell       from '../components/layout/AppShell'
import { SkeletonCompanyHeader, SkeletonTable, Skeleton } from '../components/Skeleton'
import useScoreStore  from '../stores/scores'

const card = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-lg)',
  padding: '1.5rem',
  marginBottom: '1.5rem',
  boxShadow: 'var(--shadow-sm)',
}

function StatBlock({ label, value }) {
  if (!value && value !== 0) return null
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', fontFamily: typeof value === 'number' ? 'var(--font-mono)' : 'var(--font-body)' }}>
        {value}
      </div>
    </div>
  )
}

function TabButton({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '7px 18px',
        border: '1px solid',
        borderColor: active ? 'var(--accent)' : 'var(--border)',
        borderRadius: 'var(--radius-md)',
        background: active ? 'var(--accent-light)' : 'var(--surface)',
        color: active ? 'var(--accent)' : 'var(--text-secondary)',
        fontWeight: active ? 700 : 400,
        cursor: 'pointer',
        fontSize: 13,
        fontFamily: 'var(--font-body)',
        transition: 'all var(--transition)',
      }}
    >
      {label}
    </button>
  )
}

export default function CompanyDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { fetchScore, getScore } = useScoreStore()

  const [company,  setCompany]  = useState(null)
  const [signals,  setSignals]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [tab,      setTab]      = useState('scores')

  const score = getScore(id)

  useEffect(() => {
    Promise.all([
      companiesApi.get(id),
      fetchScore(id),
      signalsApi.list(id, { limit: 100 }),
    ])
      .then(([co, , sigs]) => { setCompany(co); setSignals(sigs || []) })
      .catch((err) => setError(err.message || 'Failed to load company'))
      .finally(() => setLoading(false))
  }, [id])

  if (error) return (
    <AppShell>
      <div style={{ padding: '3rem 2rem', textAlign: 'center', color: 'var(--error)' }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>⚠</div>{error}
      </div>
    </AppShell>
  )

  return (
    <AppShell>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2.5rem 2rem' }}>

        {loading ? (
          <>
            <SkeletonCompanyHeader />
            <div style={card}><SkeletonTable rows={8} cols={4} /></div>
          </>
        ) : (
          <>
            {/* Header */}
            <div style={{ marginBottom: '1.5rem' }}>
              <button
                onClick={() => navigate(-1)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', fontSize: 13, padding: 0, marginBottom: 12, fontFamily: 'var(--font-body)' }}
              >
                ← Back
              </button>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <h1 style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 700, fontSize: 30,
                    color: 'var(--text)', margin: 0, marginBottom: 6,
                  }}>
                    {company?.name || `Company ${id}`}
                  </h1>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 13, margin: 0 }}>
                    {[company?.ticker && `${company.ticker} (${company.exchange})`, company?.sector, company?.province]
                      .filter(Boolean).join(' · ')}
                  </p>
                </div>
                {score && (
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <VelocityBadge velocity={score.velocity_score} />
                    {score.anomaly_score != null && score.anomaly_score > 0.5 && (
                      <span style={{
                        fontSize: 11, fontFamily: 'var(--font-mono)', padding: '3px 8px',
                        borderRadius: 999, background: 'var(--warning-bg)',
                        color: 'var(--warning)', border: '1px solid var(--warning)',
                      }}>
                        Anomaly ↑
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Stats bar */}
            {company && (
              <div style={{ ...card, padding: '1.25rem 1.5rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
                  <StatBlock label="Exchange" value={company.ticker ? `${company.ticker} · ${company.exchange}` : null} />
                  <StatBlock label="Sector"   value={company.sector} />
                  <StatBlock label="Province" value={company.province} />
                  <StatBlock label="Employees" value={company.employee_count?.toLocaleString('en-CA')} />
                  <StatBlock label="Market Cap" value={company.market_cap_cad ? `$${(company.market_cap_cad / 1e9).toFixed(1)}B` : null} />
                  <StatBlock label="Signals" value={company.signal_count} />
                </div>
              </div>
            )}

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 8, marginBottom: '1.25rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <TabButton label="Score Matrix" active={tab === 'scores'} onClick={() => setTab('scores')} />
              <TabButton label="Recent Signals" active={tab === 'signals'} onClick={() => setTab('signals')} />
              {score && (
                <button
                  onClick={() => navigate(`/companies/${id}/explain`)}
                  style={{
                    marginLeft: 'auto', padding: '7px 16px',
                    background: 'none', border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)', color: 'var(--text-secondary)',
                    cursor: 'pointer', fontSize: 12, fontFamily: 'var(--font-body)',
                    transition: 'all var(--transition)',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
                >
                  SHAP Explanations →
                </button>
              )}
            </div>

            {/* Score tab */}
            {tab === 'scores' && (
              <div style={card}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1rem' }}>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--text)', margin: 0 }}>
                    34 × 3 Mandate Probability Matrix
                  </h2>
                  {score?.scored_at && (
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                      {new Date(score.scored_at).toLocaleString('en-CA', { dateStyle: 'medium', timeStyle: 'short' })}
                    </span>
                  )}
                </div>
                <ScoreMatrix scores={score?.scores} companyId={null} />
              </div>
            )}

            {/* Signals tab */}
            {tab === 'signals' && (
              <div style={card}>
                <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--text)', margin: '0 0 1rem' }}>
                  Recent Signals — last 90 days
                </h2>
                <SignalFeed signals={signals} />
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  )
}
