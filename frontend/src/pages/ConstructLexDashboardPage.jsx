/**
 * pages/ConstructLexDashboardPage.jsx — route /constructlex
 *
 * BD Intelligence command center: velocity rankings, practice area demand,
 * and live mandate metrics from triggers.stats(), scores.topVelocity(),
 * and trends.practiceAreas().
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, BarChart2, Zap, Award } from 'lucide-react'
import { scores, trends, triggers } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import {
  PageHeader,
  MetricCard,
  Panel,
  Tag,
  EmptyState,
  ErrorState,
} from '../components/ui/Primitives'

export default function ConstructLexDashboardPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const [topVelocity, setTopVelocity] = useState([])
  const [practiceAreas, setPracticeAreas] = useState([])

  useEffect(() => {
    Promise.allSettled([
      triggers.stats(),
      scores.topVelocity(20),
      trends.practiceAreas(),
    ]).then(([statsResult, velocityResult, paResult]) => {
      // Each result is { status: 'fulfilled', value: ... } or { status: 'rejected', reason: ... }
      // Apply whichever calls succeeded. Never blank the whole page for a partial failure.
      if (statsResult.status === 'fulfilled') {
        setStats(statsResult.value)
      } else {
        console.warn('triggers.stats() failed:', statsResult.reason?.message)
      }

      if (velocityResult.status === 'fulfilled') {
        setTopVelocity(Array.isArray(velocityResult.value) ? velocityResult.value : [])
      } else {
        console.warn('scores.topVelocity() failed:', velocityResult.reason?.message)
        setTopVelocity([])
      }

      if (paResult.status === 'fulfilled') {
        setPracticeAreas(Array.isArray(paResult.value) ? paResult.value : [])
      } else {
        console.warn('trends.practiceAreas() failed:', paResult.reason?.message)
        setPracticeAreas([])
      }

      // Only show the global error banner if ALL three calls failed simultaneously.
      const allFailed =
        statsResult.status === 'rejected' &&
        velocityResult.status === 'rejected' &&
        paResult.status === 'rejected'
      if (allFailed) {
        setError(statsResult.reason?.message || 'Failed to load dashboard — please retry')
      }
    }).finally(() => setLoading(false))
  }, [])

  if (error) return (
    <AppShell>
      <div style={{ padding: '2rem' }}>
        <ErrorState message={error} onRetry={() => { setError(null); setLoading(true) }} />
      </div>
    </AppShell>
  )

  const top10PA = practiceAreas
    .slice()
    .sort((a, b) => (b.count_7d || 0) - (a.count_7d || 0))
    .slice(0, 10)

  /** API: GET /api/triggers/stats → TriggerStats (not legacy dashboard keys). */
  const metricTriggers72h = stats?.total_72h
  const metricTriggers24h = stats?.total_24h
  const metricUnlabelledHigh = stats?.unlabelled_high_urgency
  const activeSources = stats?.by_source && typeof stats.by_source === 'object'
    ? Object.keys(stats.by_source).length
    : 0

  return (
    <AppShell>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>

        <PageHeader
          tag="BD Intelligence"
          title="ConstructLex Market Intelligence"
          subtitle="Live mandate signals, velocity rankings, and practice area demand"
        />

        {/* Metric cards — wired to triggers.stats() TriggerStats */}
        <section style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1.25rem',
          marginBottom: '2.5rem',
        }}>
          <MetricCard
            label="Triggers (72h)"
            value={loading ? <Skeleton width={60} height={24} /> : (metricTriggers72h ?? '—')}
            accent="navy"
          />
          <MetricCard
            label="Triggers (24h)"
            value={loading ? <Skeleton width={60} height={24} /> : (metricTriggers24h ?? '—')}
            accent="teal"
          />
          <MetricCard
            label="High urgency (open)"
            value={loading ? <Skeleton width={60} height={24} /> : (metricUnlabelledHigh ?? '—')}
            accent="blue"
          />
          <MetricCard
            label="Feed sources (72h)"
            value={loading ? <Skeleton width={60} height={24} /> : activeSources}
            accent="gold"
          />
        </section>

        {/* Two-column grid: velocity (2fr) + PA demand (1fr) */}
        <section style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr',
          gap: '2rem',
        }}>

          {/* Left: Velocity Rankings */}
          <Panel title="Velocity Rankings">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <Skeleton width={24} height={16} />
                    <Skeleton width={140} height={16} />
                    <Skeleton width={70} height={22} />
                    <Skeleton width={100} height={16} />
                    <Skeleton width={50} height={16} />
                  </div>
                ))}
              </div>
            ) : topVelocity.length === 0 ? (
              <EmptyState
                icon={<TrendingUp size={32} />}
                title="No velocity data yet"
                message="Scoring pipeline will populate rankings once companies are scored."
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--color-surface-container-low)' }}>
                      {['Rank', 'Company', 'Score', 'Velocity', 'Practice Area'].map(h => (
                        <th key={h} style={{
                          padding: '9px 14px',
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.625rem',
                          fontWeight: 700,
                          color: 'var(--color-on-surface-variant)',
                          letterSpacing: '0.05em',
                          textTransform: 'uppercase',
                          textAlign: h === 'Score' ? 'right' : 'left',
                          whiteSpace: 'nowrap',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {topVelocity.map((item, i) => (
                      <tr
                        key={item.company_id || i}
                        onClick={() => item.company_id && navigate(`/companies/${item.company_id}`)}
                        style={{
                          cursor: 'pointer',
                          background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent',
                          transition: 'background var(--transition-fast)',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
                        onMouseLeave={e => e.currentTarget.style.background = i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent'}
                      >
                        <td style={{
                          padding: '13px 14px',
                          fontFamily: 'var(--font-editorial)',
                          fontSize: '1rem',
                          color: 'var(--color-on-surface-variant)',
                          whiteSpace: 'nowrap',
                        }}>
                          {String(i + 1).padStart(2, '0')}
                        </td>
                        <td style={{
                          padding: '13px 14px',
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.875rem',
                          fontWeight: 600,
                          color: 'var(--color-primary)',
                          maxWidth: 200,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}>
                          {item.company_name || item.name || `Company ${item.company_id}`}
                        </td>
                        <td style={{
                          padding: '13px 14px',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.875rem',
                          color: 'var(--color-primary)',
                          textAlign: 'right',
                          whiteSpace: 'nowrap',
                        }}>
                          {item.top_score_30d != null || item.composite_score != null
                            ? `${((item.top_score_30d ?? item.composite_score) * 100).toFixed(1)}%`
                            : '—'}
                        </td>
                        <td style={{ padding: '13px 14px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 3,
                            padding: '3px 8px',
                            borderRadius: 'var(--radius-full)',
                            background: (item.velocity_score || 0) >= 0
                              ? 'var(--color-secondary-container)'
                              : 'var(--color-error-bg)',
                            color: (item.velocity_score || 0) >= 0
                              ? 'var(--color-on-secondary-container)'
                              : 'var(--color-error)',
                            fontFamily: 'var(--font-data)',
                            fontSize: '0.625rem',
                            fontWeight: 700,
                            letterSpacing: '0.04em',
                            textTransform: 'uppercase',
                          }}>
                            {(item.velocity_score || 0) >= 0 ? '↑' : '↓'}{' '}
                            {Math.abs(item.velocity_score || 0).toFixed(1)}
                          </span>
                        </td>
                        <td style={{
                          padding: '13px 14px',
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.8125rem',
                          color: 'var(--color-on-surface-variant)',
                          maxWidth: 160,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}>
                          {item.top_practice_area || item.top_practice || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          {/* Right: Practice Area Demand */}
          <Panel title="Practice Area Demand">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {Array.from({ length: 10 }).map((_, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Skeleton width={120} height={14} />
                    <Skeleton width={36} height={20} />
                  </div>
                ))}
              </div>
            ) : top10PA.length === 0 ? (
              <EmptyState
                icon={<BarChart2 size={32} />}
                title="No trend data yet"
                message="Practice area demand will populate once signals are collected."
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {top10PA.map((pa, i) => (
                  <div
                    key={pa.practice_area || i}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.5rem 0.75rem',
                      borderRadius: 'var(--radius-md)',
                      background: i === 0 ? 'var(--color-secondary-container)' : 'var(--color-surface-container-low)',
                      transition: 'background var(--transition-fast)',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
                    onMouseLeave={e => e.currentTarget.style.background = i === 0 ? 'var(--color-secondary-container)' : 'var(--color-surface-container-low)'}
                  >
                    <span style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.8125rem',
                      fontWeight: i === 0 ? 700 : 500,
                      color: i === 0 ? 'var(--color-on-secondary-container)' : 'var(--color-on-surface)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      flex: 1,
                      minWidth: 0,
                      marginRight: '0.5rem',
                    }}>
                      {pa.practice_area || pa.name || `Area ${i + 1}`}
                    </span>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-full)',
                      background: i === 0 ? 'var(--color-on-secondary-container)' : 'var(--color-surface-container-high)',
                      color: i === 0 ? 'var(--color-secondary-container)' : 'var(--color-on-surface-variant)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.6875rem',
                      fontWeight: 700,
                      whiteSpace: 'nowrap',
                    }}>
                      {pa.count_7d ?? 0}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

        </section>
      </div>
    </AppShell>
  )
}
