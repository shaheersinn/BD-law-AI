/**
 * pages/CompetitiveIntelPage.jsx — route /competitive-intel
 * Real-time tracking of competitor firm movements, lateral hires, and market positioning.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Users } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { firms } from '../api/client'

function threatColor(level) {
  if (!level) return 'default'
  const l = level.toLowerCase()
  if (l === 'high') return 'red'
  if (l === 'medium') return 'gold'
  if (l === 'low') return 'green'
  return 'default'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d)) return dateStr
  return d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}

const MAX_PA_TAGS = 3

export default function CompetitiveIntelPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)
  const [hoveredRow, setHoveredRow] = useState(null)

  useEffect(() => {
    firms.competitive()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load competitive intelligence'))
      .finally(() => setLoading(false))
  }, [])

  const handleRetry = () => {
    setError(null)
    setLoading(true)
    firms.competitive()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load competitive intelligence'))
      .finally(() => setLoading(false))
  }

  const firmList = useMemo(() => {
    if (Array.isArray(data)) return data
    return data.firms ?? data.items ?? []
  }, [data])

  const recentLaterals = useMemo(() => {
    const laterals = []
    for (const firm of firmList) {
      const hireLaterals = firm.lateral_hires ?? firm.recent_lateral_hires ?? []
      for (const hire of hireLaterals) {
        laterals.push({ ...hire, firm_name: firm.name ?? firm.firm_name })
      }
    }
    return laterals.sort((a, b) => new Date(b.date ?? b.hired_at ?? 0) - new Date(a.date ?? a.hired_at ?? 0)).slice(0, 20)
  }, [firmList])

  const stats = useMemo(() => {
    const totalLaterals = firmList.reduce((acc, f) => acc + Number(f.recent_laterals ?? f.lateral_count ?? (f.lateral_hires?.length ?? 0)), 0)
    const allPAs = new Set()
    for (const firm of firmList) {
      const pas = firm.practice_areas ?? []
      pas.forEach(pa => allPAs.add(pa))
    }
    return { count: firmList.length, totalLaterals, practiceOverlaps: allPAs.size }
  }, [firmList])

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
          tag="Competitive Intelligence"
          title="Competitive Intel Radar"
          subtitle="Real-time tracking of competitor firm movements, lateral hires, and market positioning"
        />

        {/* Metric cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={100} radius={12} />)
          ) : (
            <>
              <MetricCard label="Firms Monitored" value={stats.count} sub="competitor firms" accent="navy" />
              <MetricCard label="Recent Laterals" value={stats.totalLaterals} sub="lateral hires tracked" accent="red" />
              <MetricCard label="Practice Overlaps" value={stats.practiceOverlaps} sub="unique practice areas" accent="gold" />
            </>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
          {/* Firm Intelligence table */}
          <Panel title="Firm Intelligence">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Array.from({ length: 7 }).map((_, i) => (
                  <Skeleton key={i} height={44} radius={6} style={{ opacity: 1 - i * 0.08 }} />
                ))}
              </div>
            ) : firmList.length === 0 ? (
              <EmptyState
                icon={<Shield size={32} />}
                title="No competitive data"
                message="Competitor firm data will populate as intelligence gathering runs"
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-surface-container-high)' }}>
                      {['Firm Name', 'Headcount', 'Practice Areas', 'Recent Laterals', 'Market Position', 'Threat Level'].map(h => (
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
                    {firmList.map((firm, i) => {
                      const pas = firm.practice_areas ?? []
                      const shownPAs = pas.slice(0, MAX_PA_TAGS)
                      const extraCount = pas.length - MAX_PA_TAGS
                      return (
                        <tr
                          key={firm.id ?? firm.firm_id ?? i}
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
                            {firm.name ?? firm.firm_name ?? '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface)', textAlign: 'center' }}>
                            {firm.headcount != null ? Number(firm.headcount).toLocaleString() : '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem' }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', alignItems: 'center' }}>
                              {shownPAs.map((pa, idx) => (
                                <Tag key={idx} label={pa} color="navy" />
                              ))}
                              {extraCount > 0 && (
                                <span style={{
                                  fontFamily: 'var(--font-data)',
                                  fontSize: '0.625rem',
                                  fontWeight: 700,
                                  color: 'var(--color-on-surface-variant)',
                                }}>+{extraCount}</span>
                              )}
                            </div>
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface)', textAlign: 'center' }}>
                            {firm.recent_laterals ?? firm.lateral_count ?? (firm.lateral_hires?.length ?? '—')}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {firm.market_position ?? firm.position ?? '—'}
                          </td>
                          <td style={{ padding: '0.625rem 0.75rem' }}>
                            <Tag label={firm.threat_level ?? 'Unknown'} color={threatColor(firm.threat_level)} />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          {/* Recent Lateral Hires sidebar */}
          <Panel title="Recent Lateral Hires">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} height={56} radius={6} style={{ opacity: 1 - i * 0.07 }} />
                ))}
              </div>
            ) : recentLaterals.length === 0 ? (
              <EmptyState
                icon={<Users size={32} />}
                title="No lateral data"
                message="Lateral hire tracking will populate as intelligence runs"
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {recentLaterals.map((hire, i) => (
                  <div
                    key={hire.id ?? i}
                    style={{
                      padding: '0.75rem',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-surface-container-low)',
                      borderLeft: '3px solid var(--color-error-bg)',
                    }}
                  >
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color: 'var(--color-on-surface)',
                      marginBottom: '0.125rem',
                    }}>
                      {hire.name ?? hire.hire_name ?? '—'}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.75rem',
                      color: 'var(--color-on-surface-variant)',
                      marginBottom: '0.125rem',
                    }}>
                      {hire.firm_name ?? hire.firm ?? '—'} · {hire.practice ?? hire.practice_area ?? '—'}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.625rem',
                      color: 'var(--color-on-surface-variant)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}>
                      {formatDate(hire.date ?? hire.hired_at)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </AppShell>
  )
}
