/**
 * pages/CompanyDetailPage.jsx — Company profile + 34×3 score matrix.
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { companies as companiesApi, signals as signalsApi } from '../api/client'
import ScoreMatrix from '../components/ScoreMatrix'
import SignalFeed  from '../components/SignalFeed'
import useScoreStore from '../stores/scores'

const S = {
  page:  { minHeight: '100vh', background: '#F8F7F4', fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif' },
  main:  { maxWidth: 1100, margin: '0 auto', padding: '2rem 1.5rem' },
  back:  { color: '#6b7280', fontSize: '0.875rem', textDecoration: 'none', display: 'inline-block', marginBottom: '1.25rem' },
  h1:    { fontSize: '1.5rem', fontWeight: 700, color: '#111827', marginBottom: 4 },
  meta:  { fontSize: '0.85rem', color: '#6b7280', marginBottom: '1.5rem' },
  card:  { background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.5rem', marginBottom: '1.5rem' },
  cardH: { fontSize: '1rem', fontWeight: 600, color: '#374151', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' },
  badge: { fontSize: '0.75rem', fontWeight: 500, padding: '3px 10px', borderRadius: 999 },
  grid:  { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px,1fr))', gap: '1rem', marginBottom: '0.5rem' },
  stat:  { label: { fontSize: '0.75rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em' }, value: { fontSize: '0.95rem', fontWeight: 600, color: '#111827' } },
  btn:   { padding: '8px 16px', background: '#f9fafb', color: '#374151', border: '1px solid #e5e7eb', borderRadius: 8, fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', textDecoration: 'none', display: 'inline-block' },
}

function StatBlock({ label, value }) {
  if (!value && value !== 0) return null
  return (
    <div>
      <div style={{ fontSize: '0.72rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#111827' }}>{value}</div>
    </div>
  )
}

export default function CompanyDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { fetchScore, getScore } = useScoreStore()

  const [company, setCompany]   = useState(null)
  const [signals,  setSignals]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [tab,      setTab]      = useState('scores') // 'scores' | 'signals'

  const score = getScore(id)

  useEffect(() => {
    Promise.all([
      companiesApi.get(id),
      fetchScore(id),
      signalsApi.list(id, { limit: 100 }),
    ])
      .then(([co, , sigs]) => {
        setCompany(co)
        setSignals(sigs || [])
      })
      .catch((err) => setError(err.message || 'Failed to load company'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={S.page}><main style={S.main}><p style={{ color: '#9ca3af' }}>Loading…</p></main></div>
  if (error)   return <div style={S.page}><main style={S.main}><p style={{ color: '#ef4444' }}>{error}</p></main></div>

  return (
    <div style={S.page}>
      <main style={S.main}>
        <a href="/search" style={S.back}>← Search</a>

        <h1 style={S.h1}>{company?.name || `Company ${id}`}</h1>
        <p style={S.meta}>
          {[company?.ticker, company?.exchange, company?.sector, company?.province]
            .filter(Boolean).join(' · ')}
        </p>

        {/* Stats row */}
        {company && (
          <div style={{ ...S.card, paddingTop: '1.25rem', paddingBottom: '1.25rem' }}>
            <div style={S.grid}>
              <StatBlock label="Ticker"         value={company.ticker ? `${company.ticker} (${company.exchange})` : null} />
              <StatBlock label="Sector"         value={company.sector} />
              <StatBlock label="Province"       value={company.province} />
              <StatBlock label="Employees"      value={company.employee_count?.toLocaleString()} />
              <StatBlock label="Market Cap"     value={company.market_cap_cad ? `$${(company.market_cap_cad / 1e9).toFixed(1)}B CAD` : null} />
              <StatBlock label="Signals (total)" value={company.signal_count} />
            </div>
          </div>
        )}

        {/* Tab switcher */}
        <div style={{ display: 'flex', gap: 8, marginBottom: '1rem' }}>
          {['scores', 'signals'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: '7px 16px',
                border: '1px solid',
                borderColor: tab === t ? '#0C9182' : '#e5e7eb',
                borderRadius: 8,
                background: tab === t ? '#ecfdf5' : '#fff',
                color: tab === t ? '#0C9182' : '#374151',
                fontWeight: tab === t ? 600 : 400,
                cursor: 'pointer',
                fontSize: '0.875rem',
                textTransform: 'capitalize',
              }}
            >
              {t}
            </button>
          ))}
          {score && (
            <a
              href={`/companies/${id}/explain`}
              style={{ ...S.btn, marginLeft: 'auto' }}
            >
              View Explanations →
            </a>
          )}
        </div>

        {tab === 'scores' && (
          <div style={S.card}>
            <div style={S.cardH}>
              <span>34 × 3 Mandate Probability Matrix</span>
              {score && (
                <span style={{ fontSize: '0.75rem', color: '#9ca3af', fontWeight: 400 }}>
                  Scored {new Date(score.scored_at).toLocaleString()}
                </span>
              )}
            </div>
            {score ? (
              <ScoreMatrix scores={score.scores} />
            ) : (
              <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>
                No scores available yet. Scoring may be pending.
              </p>
            )}
          </div>
        )}

        {tab === 'signals' && (
          <div style={S.card}>
            <h2 style={{ ...S.cardH, marginBottom: '1rem' }}>Recent Signals (last 90 days)</h2>
            <SignalFeed signals={signals} />
          </div>
        )}
      </main>
    </div>
  )
}
