/**
 * pages/MandatePreFormationPage.jsx — P20 Redesign
 * 
 * Shows companies exhibiting pre-mandate formation signals across 34 practice areas.
 * Employs CSS injection and DM Sans/Mono integration, eliminating inline objects.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Target } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, EmptyState, ErrorState } from '../components/ui/Primitives'
import { scores, trends } from '../api/client'

const HORIZONS = ['30d', '60d', '90d']

const PRE_CSS = `
.pre-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}

/* Horizon toggle */
.pre-horizons {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}
.pre-horizon-btn {
  padding: 0.375rem 1rem;
  border-radius: var(--radius-full);
  font-family: var(--font-data);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: none;
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.pre-horizon-btn.active {
  background: var(--color-primary);
  color: #fff;
}
.pre-horizon-btn.inactive {
  background: var(--color-surface-container-high);
  color: var(--color-on-surface-variant);
}

.pre-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}
.pre-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

/* Pre-Formation Table */
.pre-table {
  width: 100%;
  border-collapse: collapse;
}
.pre-th {
  padding: 9px 12px;
  text-align: left;
  font-family: var(--font-data);
  font-weight: 700;
  font-size: 0.625rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-on-surface-variant);
  background: var(--color-surface-container-low);
  white-space: nowrap;
}
.pre-tr {
  transition: background var(--transition-fast);
}
.pre-tr:nth-child(even) { background: var(--color-surface-container-low); }
.pre-tr:hover { background: var(--color-surface-container-high) !important; }

.pre-td {
  padding: 13px 12px;
  white-space: nowrap;
}
.pre-td-co {
  font-family: var(--font-data);
  font-weight: 600;
  color: var(--color-on-surface);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pre-td-pa {
  font-family: var(--font-data);
  color: var(--color-on-surface-variant);
  font-size: 0.8125rem;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pre-td-score {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.875rem;
}
.pre-obtn {
  padding: 5px 12px;
  border-radius: var(--radius-md);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid var(--color-secondary);
  background: transparent;
  color: var(--color-secondary);
  cursor: pointer;
  white-space: nowrap;
}
.pre-obtn:hover {
  background: rgba(212, 168, 103, 0.1);
}

/* PA Demand Sidebar */
.pre-pa-item {
  margin-bottom: 0.625rem;
}
.pre-pa-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.pre-pa-label {
  font-family: var(--font-data);
  font-size: 0.75rem;
  color: var(--color-on-surface);
  max-width: 75%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pre-pa-val {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
}
.pre-pa-track {
  height: 4px;
  background: var(--color-surface-container-high);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.pre-pa-fill {
  height: 100%;
  background: var(--color-secondary);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

@media (max-width: 980px) {
  .pre-grid { grid-template-columns: 1fr; }
  .pre-metrics { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('pre-styles')) {
    const el = document.createElement('style')
    el.id = 'pre-styles'
    el.textContent = PRE_CSS
    document.head.appendChild(el)
  }
}

function scoreColor(val) {
  if (val == null) return 'var(--color-on-surface-variant)'
  if (val > 0.7) return 'var(--color-error)'
  if (val > 0.5) return '#d97706'
  return 'var(--color-secondary)'
}

function scoreLabel(val) {
  if (val == null) return '—'
  return `${Math.round(val * 100)}%`
}

function getBestPracticeArea(company) {
  if (!company.scores) return '—'
  let best = null
  let bestScore = 0
  for (const [pa, horizonScores] of Object.entries(company.scores)) {
    const s = horizonScores?.['30d'] ?? horizonScores?.d30 ?? 0
    if (s > bestScore) { bestScore = s; best = pa }
  }
  return best || '—'
}

function getHorizonScore(company, horizon) {
  if (!company.scores) return null
  const key = horizon.replace('d', '')
  for (const [, horizonScores] of Object.entries(company.scores)) {
    const val = horizonScores?.[horizon] ?? horizonScores?.[key + 'd'] ?? horizonScores?.['d' + key]
    if (val != null) return val
  }
  return null
}

function getBestScore(company, horizon) {
  if (!company.scores) return null
  let best = 0
  for (const [, horizonScores] of Object.entries(company.scores)) {
    const val = horizonScores?.[horizon] ?? horizonScores?.[horizon.replace('d', '')] ?? 0
    if (val > best) best = val
  }
  return best || null
}

export default function MandatePreFormationPage() {
  injectCSS()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [topVelocity, setTopVelocity] = useState([])
  const [practiceAreas, setPracticeAreas] = useState([])
  const [error, setError] = useState(null)
  const [horizon, setHorizon] = useState('30d')

  useEffect(() => {
    Promise.all([scores.topVelocity(20), trends.practiceAreas()])
      .then(([vel, pa]) => {
        setTopVelocity(vel || [])
        setPracticeAreas(pa || [])
      })
      .catch(err => setError(err.message || 'Failed to load mandate formation data'))
      .finally(() => setLoading(false))
  }, [])

  const handleRetry = () => {
    setError(null)
    setLoading(true)
    Promise.all([scores.topVelocity(20), trends.practiceAreas()])
      .then(([vel, pa]) => {
        setTopVelocity(vel || [])
        setPracticeAreas(pa || [])
      })
      .catch(err => setError(err.message || 'Failed to load mandate formation data'))
      .finally(() => setLoading(false))
  }

  if (error) {
    return (
      <AppShell>
        <div style={{ padding: '2rem' }}>
          <ErrorState message={error} onRetry={handleRetry} />
        </div>
      </AppShell>
    )
  }

  const highProb = topVelocity.filter(v => (v.velocity_score ?? 0) > 0.7)
  const forming = topVelocity.filter(v => (v.velocity_score ?? 0) > 0.5 && (v.velocity_score ?? 0) <= 0.7)
  const topPAs = [...practiceAreas]
    .sort((a, b) => (b.count_7d ?? 0) - (a.count_7d ?? 0))
    .slice(0, 15)

  return (
    <AppShell>
      <div className="pre-root">
        <PageHeader
          tag="Mandate Intelligence"
          title="Mandate Pre-Formation Radar"
          subtitle="Companies showing pre-mandate formation signals across 34 practice areas"
        />

        {/* Horizon toggle */}
        <div className="pre-horizons">
          {HORIZONS.map(h => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`pre-horizon-btn ${horizon === h ? 'active' : 'inactive'}`}
            >
              {h}
            </button>
          ))}
        </div>

        {/* Metric cards */}
        <div className="pre-metrics">
          {loading ? (
            <>
              <Skeleton height={100} radius={12} />
              <Skeleton height={100} radius={12} />
              <Skeleton height={100} radius={12} />
            </>
          ) : (
            <>
              <MetricCard label="High Probability" value={highProb.length} sub="velocity score > 70%" accent="red" />
              <MetricCard label="Forming Now" value={forming.length} sub="velocity score 50–70%" accent="gold" />
              <MetricCard label="Monitoring" value={topVelocity.length} sub="total companies tracked" accent="teal" />
            </>
          )}
        </div>

        <div className="pre-grid">
          {/* Pre-Formation Pipeline */}
          <Panel title="Pre-Formation Pipeline">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} height={44} radius={6} style={{ opacity: 1 - i * 0.08 }} />
                ))}
              </div>
            ) : topVelocity.length === 0 ? (
              <EmptyState
                icon={<Target size={32} />}
                title="No signals detected"
                message="The pipeline will populate as scrapers collect company data"
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="pre-table">
                  <thead>
                    <tr>
                      {['Company', 'Top Practice Area', '30d', '60d', '90d', 'Velocity', 'Action'].map(h => (
                        <th key={h} className="pre-th">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {topVelocity.map((company, i) => {
                      const topPA = getBestPracticeArea(company)
                      const s30 = getBestScore(company, '30d')
                      const s60 = getBestScore(company, '60d')
                      const s90 = getBestScore(company, '90d')
                      const vel = company.velocity_score ?? null
                      return (
                        <tr key={company.company_id ?? i} className="pre-tr">
                          <td className="pre-td pre-td-co">
                            {company.company_name ?? company.company_id ?? '—'}
                          </td>
                          <td className="pre-td pre-td-pa">
                            {topPA}
                          </td>
                          {[s30, s60, s90].map((s, idx) => (
                            <td key={idx} className="pre-td pre-td-score" style={{ color: scoreColor(s) }}>
                              {scoreLabel(s)}
                            </td>
                          ))}
                          <td className="pre-td pre-td-score" style={{ color: scoreColor(vel) }}>
                            {vel != null ? `${Math.round(vel * 100)}%` : '—'}
                          </td>
                          <td className="pre-td">
                            <button className="pre-obtn" onClick={() => navigate(`/companies/${company.company_id}`)}>
                              View Details
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          {/* PA Demand sidebar */}
          <Panel title="Practice Area Demand">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Array.from({ length: 10 }).map((_, i) => (
                  <Skeleton key={i} height={32} radius={6} style={{ opacity: 1 - i * 0.06 }} />
                ))}
              </div>
            ) : topPAs.length === 0 ? (
              <EmptyState title="No trend data" message="Practice area demand will appear once signals are collected" />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {topPAs.map((pa, i) => {
                  const maxCount = topPAs[0]?.count_7d ?? 1
                  const pct = Math.round(((pa.count_7d ?? 0) / maxCount) * 100)
                  return (
                    <div key={pa.practice_area ?? i} className="pre-pa-item">
                      <div className="pre-pa-header">
                        <span className="pre-pa-label">{pa.practice_area}</span>
                        <span className="pre-pa-val">{pa.count_7d ?? 0}</span>
                      </div>
                      <div className="pre-pa-track">
                        <div className="pre-pa-fill" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </AppShell>
  )
}
