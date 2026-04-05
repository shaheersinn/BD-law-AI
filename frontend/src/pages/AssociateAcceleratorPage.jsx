/**
 * pages/AssociateAcceleratorPage.jsx — P16 Redesign
 * 
 * Associate BD activity tracking, coaching recommendations, and skill development.
 * Uses injected CSS to adhere to Phase 1 styling paradigms without inline styles.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, EmptyState, ErrorState } from '../components/ui/Primitives'
import { bd } from '../api/client'

const ASSOC_CSS = `
.asc-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.asc-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}

.asc-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  align-items: start;
}
.asc-grid-single {
  grid-template-columns: 1fr;
}

/* Table */
.asc-table {
  width: 100%;
  border-collapse: collapse;
}
.asc-th {
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
.asc-tr {
  transition: background var(--transition-fast);
}
.asc-tr:nth-child(even) { background: var(--color-surface-container-low); }
.asc-tr:hover { background: var(--color-surface-container-high) !important; }

.asc-td {
  padding: 13px 12px;
  white-space: nowrap;
}
.asc-td-name {
  font-family: var(--font-data);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary);
}
.asc-td-group {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.asc-td-num {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  color: var(--color-on-surface);
  text-align: center;
}

.asc-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  white-space: nowrap;
}

/* Recommendations */
.asc-rec-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.asc-rec-item {
  padding: 0.875rem 1rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-low);
  border-left: 3px solid var(--color-secondary);
}
.asc-rec-name {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-secondary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}
.asc-rec-text {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  color: var(--color-on-surface);
  line-height: 1.5;
}
.asc-rec-priority {
  margin-top: 0.375rem;
  font-family: var(--font-data);
  font-size: 0.625rem;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

@media (max-width: 980px) {
  .asc-grid { grid-template-columns: 1fr; }
  .asc-metrics { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('asc-styles')) {
    const el = document.createElement('style')
    el.id = 'asc-styles'
    el.textContent = ASSOC_CSS
    document.head.appendChild(el)
  }
}

function engagementColor(score) {
  if (score == null) return 'var(--color-on-surface-variant)'
  if (score > 70) return 'var(--color-success)'
  if (score > 40) return '#d97706'
  return 'var(--color-error)'
}

function engagementBg(score) {
  if (score == null) return 'var(--color-surface-container-high)'
  if (score > 70) return 'var(--color-secondary-container)'
  if (score > 40) return '#fffbeb'
  return 'var(--color-error-bg)'
}

function TrendIcon({ trend }) {
  if (!trend) return <Minus size={14} color="var(--color-on-surface-variant)" />
  const t = typeof trend === 'string' ? trend.toLowerCase() : trend
  if (t === 'up' || t === 'rising' || t === 1 || t === true) {
    return <TrendingUp size={14} color="var(--color-success)" />
  }
  if (t === 'down' || t === 'falling' || t === -1) {
    return <TrendingDown size={14} color="var(--color-error)" />
  }
  return <Minus size={14} color="var(--color-on-surface-variant)" />
}

export default function AssociateAcceleratorPage() {
  injectCSS()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    bd.associateActivity()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load associate activity'))
      .finally(() => setLoading(false))
  }, [])

  const handleRetry = () => {
    setError(null)
    setLoading(true)
    bd.associateActivity()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load associate activity'))
      .finally(() => setLoading(false))
  }

  const associates = useMemo(() => {
    if (Array.isArray(data)) return data
    return data.associates ?? data.items ?? []
  }, [data])

  const recommendations = useMemo(() => {
    if (Array.isArray(data)) return []
    return data.recommendations ?? data.coaching ?? []
  }, [data])

  const stats = useMemo(() => {
    const total = associates.length
    const activitiesThisMonth = associates.reduce((acc, a) => acc + Number(a.activity_count ?? a.activities_month ?? 0), 0)
    const engScores = associates.map(a => Number(a.engagement_score ?? a.engagement ?? 0)).filter(v => !isNaN(v) && v > 0)
    const avgEngagement = engScores.length > 0 ? Math.round(engScores.reduce((a, b) => a + b, 0) / engScores.length) : 0
    return { total, activitiesThisMonth, avgEngagement }
  }, [associates])

  if (error) {
    return (
      <AppShell>
        <div style={{ padding: '2rem' }}>
          <ErrorState message={error} onRetry={handleRetry} />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="asc-root">
        <PageHeader
          tag="Training & Development"
          title="Associate Accelerator"
          subtitle="Associate BD activity tracking, coaching recommendations, and skill development"
        />

        {/* Metric cards */}
        <div className="asc-metrics">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={100} radius={12} />)
          ) : (
            <>
              <MetricCard label="Active Associates" value={stats.total} sub="in programme" accent="teal" />
              <MetricCard label="Activities This Month" value={stats.activitiesThisMonth} sub="total BD activities" accent="blue" />
              <MetricCard label="Avg Engagement" value={`${stats.avgEngagement}%`} sub="across all associates" accent="gold" />
            </>
          )}
        </div>

        <div className={`asc-grid ${recommendations.length > 0 ? '' : 'asc-grid-single'}`}>
          {/* Associate Activity Table */}
          <Panel title="Associate Activity">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Array.from({ length: 7 }).map((_, i) => (
                  <Skeleton key={i} height={44} radius={6} style={{ opacity: 1 - i * 0.08 }} />
                ))}
              </div>
            ) : associates.length === 0 ? (
              <EmptyState
                icon={<Users size={32} />}
                title="No associate data"
                message="Associate BD activity will appear once tracking is configured"
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="asc-table">
                  <thead>
                    <tr>
                      {['Associate', 'Practice Group', 'Activities', 'Pitches', 'Content', 'Engagement', 'Trend'].map(h => (
                        <th key={h} className="asc-th">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {associates.map((assoc, i) => {
                      const score = Number(assoc.engagement_score ?? assoc.engagement ?? 0)
                      return (
                        <tr key={assoc.id ?? assoc.associate_id ?? i} className="asc-tr">
                          <td className="asc-td asc-td-name">{assoc.name ?? assoc.associate_name ?? '—'}</td>
                          <td className="asc-td asc-td-group">{assoc.practice_group ?? assoc.practice_area ?? '—'}</td>
                          <td className="asc-td asc-td-num">{assoc.activity_count ?? assoc.activities_month ?? '—'}</td>
                          <td className="asc-td asc-td-num">{assoc.pitches_supported ?? assoc.pitches ?? '—'}</td>
                          <td className="asc-td asc-td-num">{assoc.content_drafted ?? assoc.content ?? '—'}</td>
                          <td className="asc-td" style={{ textAlign: 'center' }}>
                            <span className="asc-badge" style={{ background: engagementBg(score), color: engagementColor(score) }}>
                              {score > 0 ? `${score}%` : '—'}
                            </span>
                          </td>
                          <td className="asc-td" style={{ textAlign: 'center' }}>
                            <TrendIcon trend={assoc.trend} />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          {/* Recommended Actions */}
          {!loading && recommendations.length > 0 && (
            <Panel title="Recommended Actions">
              <div className="asc-rec-list">
                {recommendations.map((rec, i) => (
                  <div key={rec.id ?? i} className="asc-rec-item">
                    {rec.associate_name && <div className="asc-rec-name">{rec.associate_name}</div>}
                    <div className="asc-rec-text">{rec.action ?? rec.recommendation ?? rec.text ?? '—'}</div>
                    {rec.priority && <div className="asc-rec-priority">Priority: {rec.priority}</div>}
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>

      </div>
    </AppShell>
  )
}
