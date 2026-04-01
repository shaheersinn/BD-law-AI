/**
 * pages/AssociateAcceleratorPage.jsx — route /associate-accelerator
 * Associate BD activity tracking, coaching recommendations, and skill development.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, EmptyState, ErrorState } from '../components/ui/Primitives'
import { bd } from '../api/client'

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
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)
  const [hoveredRow, setHoveredRow] = useState(null)

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
    // Support both array of associates or object with associates key
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
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>
        <PageHeader
          tag="Training & Development"
          title="Associate Accelerator"
          subtitle="Associate BD activity tracking, coaching recommendations, and skill development"
        />

        {/* Metric cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
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

        <div style={{ display: 'grid', gridTemplateColumns: recommendations.length > 0 ? '2fr 1fr' : '1fr', gap: '1.5rem', alignItems: 'start' }}>
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
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-surface-container-high)' }}>
                      {['Associate', 'Practice Group', 'Activities', 'Pitches', 'Content', 'Engagement', 'Trend'].map(h => (
                        <th key={h} style={{
                          padding: '0.5rem 0.75rem',
                          textAlign: 'left',
                          fontWeight: 700,
                          fontSize: '0.625rem',
                          letterSpacing: '0.05em',
                          textTransform: 'uppercase',
                          color: 'var(--color-on-surface-variant)',
                          whiteSpace: 'nowrap',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {associates.map((assoc, i) => {
                      const score = Number(assoc.engagement_score ?? assoc.engagement ?? 0)
                      return (
                        <tr
                          key={assoc.id ?? assoc.associate_id ?? i}
                          onMouseEnter={() => setHoveredRow(i)}
                          onMouseLeave={() => setHoveredRow(null)}
                          style={{
                            borderBottom: '1px solid var(--color-surface-container-high)',
                            background: hoveredRow === i ? 'var(--color-surface-container-low)' : 'transparent',
                            transition: 'background 0.12s',
                            cursor: 'default',
                          }}
                        >
                          <td style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-on-surface)', whiteSpace: 'nowrap' }}>
                            {assoc.name ?? assoc.associate_name ?? '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {assoc.practice_group ?? assoc.practice_area ?? '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface)', textAlign: 'center' }}>
                            {assoc.activity_count ?? assoc.activities_month ?? '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface)', textAlign: 'center' }}>
                            {assoc.pitches_supported ?? assoc.pitches ?? '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface)', textAlign: 'center' }}>
                            {assoc.content_drafted ?? assoc.content ?? '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem' }}>
                            <span style={{
                              display: 'inline-block',
                              padding: '2px 10px',
                              borderRadius: 'var(--radius-full)',
                              fontFamily: 'var(--font-data)',
                              fontSize: '0.6875rem',
                              fontWeight: 700,
                              background: engagementBg(score),
                              color: engagementColor(score),
                              whiteSpace: 'nowrap',
                            }}>
                              {score > 0 ? `${score}%` : '—'}
                            </span>
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem' }}>
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

          {/* Recommended Actions — only shown when recommendations exist */}
          {!loading && recommendations.length > 0 && (
            <Panel title="Recommended Actions">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {recommendations.map((rec, i) => (
                  <div
                    key={rec.id ?? i}
                    style={{
                      padding: '0.875rem 1rem',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-surface-container-low)',
                      borderLeft: '3px solid var(--color-secondary)',
                    }}
                  >
                    {rec.associate_name && (
                      <div style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.6875rem',
                        fontWeight: 700,
                        color: 'var(--color-secondary)',
                        letterSpacing: '0.04em',
                        textTransform: 'uppercase',
                        marginBottom: '0.25rem',
                      }}>
                        {rec.associate_name}
                      </div>
                    )}
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.8125rem',
                      color: 'var(--color-on-surface)',
                      lineHeight: 1.5,
                    }}>
                      {rec.action ?? rec.recommendation ?? rec.text ?? '—'}
                    </div>
                    {rec.priority && (
                      <div style={{
                        marginTop: '0.375rem',
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.625rem',
                        color: 'var(--color-on-surface-variant)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                      }}>
                        Priority: {rec.priority}
                      </div>
                    )}
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
