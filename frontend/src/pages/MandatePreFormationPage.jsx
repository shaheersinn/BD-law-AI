/**
 * pages/MandatePreFormationPage.jsx — route /mandate-formation
 * Shows companies exhibiting pre-mandate formation signals across 34 practice areas.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Target } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { scores, trends } from '../api/client'

const HORIZONS = ['30d', '60d', '90d']

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
  // Try multiple key formats the API might return
  for (const [, horizonScores] of Object.entries(company.scores)) {
    const val = horizonScores?.[horizon] ?? horizonScores?.[`${key}d`] ?? horizonScores?.[`d${key}`]
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
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [topVelocity, setTopVelocity] = useState([])
  const [practiceAreas, setPracticeAreas] = useState([])
  const [error, setError] = useState(null)
  const [horizon, setHorizon] = useState('30d')
  const [hoveredRow, setHoveredRow] = useState(null)

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
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>
        <PageHeader
          tag="Mandate Intelligence"
          title="Mandate Pre-Formation Radar"
          subtitle="Companies showing pre-mandate formation signals across 34 practice areas"
        />

        {/* Horizon toggle */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          {HORIZONS.map(h => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              style={{
                padding: '0.375rem 1rem',
                borderRadius: 'var(--radius-full)',
                fontFamily: 'var(--font-data)',
                fontSize: '0.75rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                border: 'none',
                cursor: 'pointer',
                background: horizon === h ? 'var(--color-primary)' : 'var(--color-surface-container-high)',
                color: horizon === h ? '#fff' : 'var(--color-on-surface-variant)',
                transition: 'background 0.15s, color 0.15s',
              }}
            >
              {h}
            </button>
          ))}
        </div>

        {/* Metric cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
          {loading ? (
            <>
              <Skeleton height={100} radius={12} />
              <Skeleton height={100} radius={12} />
              <Skeleton height={100} radius={12} />
            </>
          ) : (
            <>
              <MetricCard
                label="High Probability"
                value={highProb.length}
                sub="velocity score > 70%"
                accent="red"
              />
              <MetricCard
                label="Forming Now"
                value={forming.length}
                sub="velocity score 50–70%"
                accent="gold"
              />
              <MetricCard
                label="Monitoring"
                value={topVelocity.length}
                sub="total companies tracked"
                accent="teal"
              />
            </>
          )}
        </div>

        {/* Main content: pipeline table + PA sidebar */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
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
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-surface-container-high)' }}>
                      {['Company', 'Top Practice Area', '30d', '60d', '90d', 'Velocity', 'Action'].map(h => (
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
                    {topVelocity.map((company, i) => {
                      const topPA = getBestPracticeArea(company)
                      const s30 = getBestScore(company, '30d')
                      const s60 = getBestScore(company, '60d')
                      const s90 = getBestScore(company, '90d')
                      const vel = company.velocity_score ?? null
                      return (
                        <tr
                          key={company.company_id ?? i}
                          onMouseEnter={() => setHoveredRow(i)}
                          onMouseLeave={() => setHoveredRow(null)}
                          style={{
                            borderBottom: '1px solid var(--color-surface-container-high)',
                            background: hoveredRow === i ? 'var(--color-surface-container-low)' : 'transparent',
                            transition: 'background 0.12s',
                            cursor: 'default',
                          }}
                        >
                          <td style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-on-surface)', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {company.company_name ?? company.company_id ?? '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {topPA}
                          </td>
                          {[s30, s60, s90].map((s, idx) => (
                            <td key={idx} style={{
                              padding: '0.625rem 0.75rem',
                              fontFamily: 'var(--font-data)',
                              fontWeight: 700,
                              color: scoreColor(s),
                              whiteSpace: 'nowrap',
                            }}>
                              {scoreLabel(s)}
                            </td>
                          ))}
                          <td style={{ padding: '0.625rem 0.75rem', fontWeight: 700, color: scoreColor(vel), whiteSpace: 'nowrap' }}>
                            {vel != null ? `${Math.round(vel * 100)}%` : '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem' }}>
                            <button
                              onClick={() => navigate(`/companies/${company.company_id}`)}
                              style={{
                                padding: '0.25rem 0.75rem',
                                borderRadius: 'var(--radius-md)',
                                fontFamily: 'var(--font-data)',
                                fontSize: '0.6875rem',
                                fontWeight: 700,
                                letterSpacing: '0.04em',
                                textTransform: 'uppercase',
                                border: '1px solid var(--color-secondary)',
                                background: 'transparent',
                                color: 'var(--color-secondary)',
                                cursor: 'pointer',
                                whiteSpace: 'nowrap',
                              }}
                            >
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

          {/* Practice Area Demand sidebar */}
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
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {topPAs.map((pa, i) => {
                  const maxCount = topPAs[0]?.count_7d ?? 1
                  const pct = Math.round(((pa.count_7d ?? 0) / maxCount) * 100)
                  return (
                    <div key={pa.practice_area ?? i}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <span style={{
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.75rem',
                          color: 'var(--color-on-surface)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: '75%',
                        }}>{pa.practice_area}</span>
                        <span style={{
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.6875rem',
                          fontWeight: 700,
                          color: 'var(--color-on-surface-variant)',
                        }}>{pa.count_7d ?? 0}</span>
                      </div>
                      <div style={{ height: 4, background: 'var(--color-surface-container-high)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${pct}%`,
                          background: 'var(--color-secondary)',
                          borderRadius: 'var(--radius-full)',
                          transition: 'width 0.3s ease',
                        }} />
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
