/**
 * pages/CompanyDetailPage.jsx — Digital Atelier company detail.
 * Editorial header, tonal card system, score matrix, signal feed.
 * Practice area chips, velocity badges using secondary-container.
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

function StatBlock({ label, value }) {
  if (!value && value !== 0) return null
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-data)',
        fontSize: '0.6875rem',
        fontWeight: 700,
        color: 'var(--color-on-surface-variant)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: 4,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: typeof value === 'number' ? 'var(--font-mono)' : 'var(--font-data)',
        fontSize: 14,
        fontWeight: 600,
        color: 'var(--color-on-surface)',
      }}>
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
        borderRadius: 'var(--radius-md)',
        background: active
          ? 'var(--color-surface-container-lowest)'
          : 'transparent',
        color: active
          ? 'var(--color-on-surface)'
          : 'var(--color-on-surface-variant)',
        fontWeight: active ? 700 : 400,
        cursor: 'pointer',
        fontSize: '0.6875rem',
        fontFamily: 'var(--font-data)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        transition: 'background 150ms ease-out, color 150ms ease-out',
        boxShadow: active ? 'var(--shadow-ambient)' : 'none',
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
      <div style={{
        padding: '3rem 2rem',
        textAlign: 'center',
        color: 'var(--color-error)',
        fontFamily: 'var(--font-data)',
      }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>⚠</div>{error}
      </div>
    </AppShell>
  )

  const cardStyle = {
    background: 'var(--color-surface-container-lowest)',
    borderRadius: 'var(--radius-xl)',
    padding: '1.5rem',
    marginBottom: '1.5rem',
    boxShadow: 'var(--shadow-ambient)',
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2.5rem 2rem' }}>

        {loading ? (
          <>
            <SkeletonCompanyHeader />
            <div style={cardStyle}><SkeletonTable rows={8} cols={4} /></div>
          </>
        ) : (
          <>
            {/* Header */}
            <div style={{ marginBottom: '1.5rem' }}>
              <button
                onClick={() => navigate(-1)}
                style={{
                  background: 'none',
                  cursor: 'pointer',
                  color: 'var(--color-on-surface-variant)',
                  fontSize: 13,
                  padding: 0,
                  marginBottom: 12,
                  fontFamily: 'var(--font-data)',
                }}
              >
                ← Back
              </button>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <h1 style={{
                    fontFamily: 'var(--font-editorial)',
                    fontWeight: 500,
                    fontSize: '1.75rem',
                    color: 'var(--color-primary)',
                    margin: 0,
                    marginBottom: 6,
                    letterSpacing: '-0.01em',
                  }}>
                    {company?.name || `Company ${id}`}
                  </h1>
                  <p style={{
                    fontFamily: 'var(--font-data)',
                    color: 'var(--color-on-surface-variant)',
                    fontSize: 13,
                    margin: 0,
                    letterSpacing: '0.01em',
                  }}>
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
                        borderRadius: 'var(--radius-full)',
                        background: 'var(--color-warning-bg)',
                        color: 'var(--color-warning)',
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
              <div style={{ ...cardStyle, padding: '1.25rem 1.5rem' }}>
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

            {/* Tabs — pill style */}
            <div style={{
              display: 'flex',
              gap: 4,
              marginBottom: '1.25rem',
              flexWrap: 'wrap',
              alignItems: 'center',
              background: 'var(--color-surface-container-low)',
              borderRadius: 'var(--radius-xl)',
              padding: 4,
              width: 'fit-content',
            }}>
              <TabButton label="Score Matrix" active={tab === 'scores'} onClick={() => setTab('scores')} />
              <TabButton label="Recent Signals" active={tab === 'signals'} onClick={() => setTab('signals')} />
              {score && (
                <button
                  onClick={() => navigate(`/companies/${id}/explain`)}
                  style={{
                    marginLeft: 'auto',
                    padding: '7px 16px',
                    background: 'transparent',
                    color: 'var(--color-primary)',
                    cursor: 'pointer',
                    fontSize: '0.6875rem',
                    fontFamily: 'var(--font-data)',
                    fontWeight: 600,
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                    borderRadius: 'var(--radius-md)',
                    transition: 'background 150ms ease-out',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  SHAP Explanations →
                </button>
              )}
            </div>

            {/* Score tab */}
            {tab === 'scores' && (
              <div style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1rem' }}>
                  <h2 style={{
                    fontFamily: 'var(--font-editorial)',
                    fontWeight: 500,
                    fontSize: 18,
                    color: 'var(--color-primary)',
                    margin: 0,
                    letterSpacing: '-0.01em',
                  }}>
                    34 × 3 Mandate Probability Matrix
                  </h2>
                  {score?.scored_at && (
                    <span style={{
                      fontSize: 11,
                      color: 'var(--color-on-surface-variant)',
                      fontFamily: 'var(--font-mono)',
                    }}>
                      {new Date(score.scored_at).toLocaleString('en-CA', { dateStyle: 'medium', timeStyle: 'short' })}
                    </span>
                  )}
                </div>
                <ScoreMatrix scores={score?.scores} companyId={null} />
              </div>
            )}

            {/* Signals tab */}
            {tab === 'signals' && (
              <div style={cardStyle}>
                <h2 style={{
                  fontFamily: 'var(--font-editorial)',
                  fontWeight: 500,
                  fontSize: 18,
                  color: 'var(--color-primary)',
                  margin: '0 0 1rem',
                  letterSpacing: '-0.01em',
                }}>
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
