/**
 * pages/CompanyDetailPage.jsx — P14 Redesign
 * 
 * Digital Atelier company detail.
 * Editorial header, tonal card system, score matrix, signal feed.
 * Practice area chips, velocity badges using secondary-container.
 * No inline styles. Uses injected CSS.
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { companies as companiesApi, signals as signalsApi } from '../api/client'
import ScoreMatrix    from '../components/ScoreMatrix'
import SignalFeed     from '../components/SignalFeed'
import VelocityBadge  from '../components/VelocityBadge'
import AppShell       from '../components/layout/AppShell'
import { SkeletonCompanyHeader, SkeletonTable } from '../components/Skeleton'
import useScoreStore  from '../stores/scores'

const CD_CSS = `
.cd-root {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.cd-header {
  margin-bottom: 1.5rem;
}
.cd-back-btn {
  background: none;
  cursor: pointer;
  color: var(--color-on-surface-variant);
  font-size: 13px;
  padding: 0;
  margin-bottom: 12px;
  font-family: var(--font-data);
  border: none;
}
.cd-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.cd-title {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 1.75rem;
  color: var(--color-primary);
  margin: 0;
  margin-bottom: 6px;
  letter-spacing: -0.01em;
}
.cd-subtitle {
  font-family: var(--font-data);
  color: var(--color-on-surface-variant);
  font-size: 13px;
  margin: 0;
  letter-spacing: 0.01em;
}
.cd-badge-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.cd-anomaly-badge {
  font-size: 11px;
  font-family: var(--font-mono);
  padding: 3px 8px;
  border-radius: var(--radius-full);
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.cd-card {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow-ambient);
}
.cd-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}
.cd-stat-label {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}
.cd-stat-val-mono {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface);
}
.cd-stat-val-data {
  font-family: var(--font-data);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface);
}

.cd-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  align-items: center;
  background: var(--color-surface-container-low);
  border-radius: var(--radius-xl);
  padding: 4px;
  width: fit-content;
}
.cd-tab-btn {
  padding: 7px 18px;
  border-radius: var(--radius-md);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: background 150ms ease-out, color 150ms ease-out;
  border: none;
}
.cd-tab-btn.active {
  background: var(--color-surface-container-lowest);
  color: var(--color-on-surface);
  font-weight: 700;
  box-shadow: var(--shadow-ambient);
}
.cd-tab-btn.inactive {
  background: transparent;
  color: var(--color-on-surface-variant);
  font-weight: 400;
}
.cd-tab-link {
  margin-left: auto;
  padding: 7px 16px;
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 0.6875rem;
  font-family: var(--font-data);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border-radius: var(--radius-md);
  border: none;
  transition: background 150ms ease-out;
}
.cd-tab-link:hover {
  background: var(--color-surface-container-high);
}

.cd-panel-title {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 18px;
  color: var(--color-primary);
  margin: 0;
  letter-spacing: -0.01em;
}
.cd-panel-meta {
  font-size: 11px;
  color: var(--color-on-surface-variant);
  font-family: var(--font-mono);
}
.cd-error {
  padding: 3rem 2rem;
  text-align: center;
  color: var(--color-error);
  font-family: var(--font-data);
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('cd-styles')) {
    const el = document.createElement('style')
    el.id = 'cd-styles'
    el.textContent = CD_CSS
    document.head.appendChild(el)
  }
}

function StatBlock({ label, value }) {
  if (!value && value !== 0) return null
  return (
    <div>
      <div className="cd-stat-label">{label}</div>
      <div className={typeof value === 'number' ? 'cd-stat-val-mono' : 'cd-stat-val-data'}>
        {value}
      </div>
    </div>
  )
}

function TabButton({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`cd-tab-btn ${active ? 'active' : 'inactive'}`}
    >
      {label}
    </button>
  )
}

export default function CompanyDetailPage() {
  injectCSS()
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
      <div className="cd-error">
        <div style={{ fontSize: 24, marginBottom: 8 }}>⚠</div>{error}
      </div>
    </AppShell>
  )

  return (
    <AppShell>
      <div className="cd-root">

        {loading ? (
          <>
            <SkeletonCompanyHeader />
            <div className="cd-card"><SkeletonTable rows={8} cols={4} /></div>
          </>
        ) : (
          <>
            {/* Header */}
            <div className="cd-header">
              <button className="cd-back-btn" onClick={() => navigate(-1)}>← Back</button>
              <div className="cd-title-row">
                <div>
                  <h1 className="cd-title">{company?.name || `Company ${id}`}</h1>
                  <p className="cd-subtitle">
                    {[company?.ticker && `${company.ticker} (${company.exchange})`, company?.sector, company?.province]
                      .filter(Boolean).join(' · ')}
                  </p>
                </div>
                {score && (
                  <div className="cd-badge-row">
                    <VelocityBadge velocity={score.velocity_score} />
                    {score.anomaly_score != null && score.anomaly_score > 0.5 && (
                      <span className="cd-anomaly-badge">Anomaly ↑</span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Stats bar */}
            {company && (
              <div className="cd-card" style={{ padding: '1.25rem 1.5rem' }}>
                <div className="cd-stats-grid">
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
            <div className="cd-tabs">
              <TabButton label="Score Matrix" active={tab === 'scores'} onClick={() => setTab('scores')} />
              <TabButton label="Recent Signals" active={tab === 'signals'} onClick={() => setTab('signals')} />
              {score && (
                <button
                  className="cd-tab-link"
                  onClick={() => navigate(`/companies/${id}/explain`)}
                >
                  SHAP Explanations →
                </button>
              )}
            </div>

            {/* Score tab */}
            {tab === 'scores' && (
              <div className="cd-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1rem' }}>
                  <h2 className="cd-panel-title">34 × 3 Mandate Probability Matrix</h2>
                  {score?.scored_at && (
                    <span className="cd-panel-meta">
                      {new Date(score.scored_at).toLocaleString('en-CA', { dateStyle: 'medium', timeStyle: 'short' })}
                    </span>
                  )}
                </div>
                <ScoreMatrix scores={score?.scores} companyId={null} />
              </div>
            )}

            {/* Signals tab */}
            {tab === 'signals' && (
              <div className="cd-card">
                <h2 className="cd-panel-title" style={{ marginBottom: '1rem' }}>Recent Signals — last 90 days</h2>
                <SignalFeed signals={signals} />
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  )
}
