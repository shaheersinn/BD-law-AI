/**
 * pages/CompetitiveIntelPage.jsx — P18 Redesign
 * 
 * Real-time tracking of competitor firm movements, lateral hires, and market positioning.
 * Enforces DM Sans / DM Serif typography without inline styles.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Users } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { firms } from '../api/client'

const CI_CSS = `
.ci-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.ci-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}
.ci-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

/* Table */
.ci-table {
  width: 100%;
  border-collapse: collapse;
}
.ci-th {
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
.ci-tr {
  transition: background var(--transition-fast);
}
.ci-tr:nth-child(even) { background: var(--color-surface-container-low); }
.ci-tr:hover { background: var(--color-surface-container-high) !important; }

.ci-td {
  padding: 13px 12px;
  white-space: nowrap;
}
.ci-td-name {
  font-family: var(--font-editorial);
  font-size: 1.05rem;
  font-weight: 400;
  color: var(--color-primary);
}
.ci-td-mono {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-on-surface);
  text-align: center;
}
.ci-td-meta {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ci-tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}
.ci-tags-extra {
  font-family: var(--font-data);
  font-size: 0.625rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
}

/* Lateral Hire sidebar */
.ci-lat-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}
.ci-lat-item {
  padding: 0.75rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-low);
  border-left: 3px solid var(--color-error-bg);
  transition: transform var(--transition-fast);
}
.ci-lat-item:hover {
  transform: translateX(2px);
}
.ci-lat-name {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-on-surface);
  margin-bottom: 2px;
}
.ci-lat-org {
  font-family: var(--font-data);
  font-size: 0.75rem;
  color: var(--color-on-surface-variant);
  margin-bottom: 2px;
}
.ci-lat-date {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

@media (max-width: 980px) {
  .ci-grid { grid-template-columns: 1fr; }
  .ci-metrics { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('ci-styles')) {
    const el = document.createElement('style')
    el.id = 'ci-styles'
    el.textContent = CI_CSS
    document.head.appendChild(el)
  }
}

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
  injectCSS()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)

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
      <div className="ci-root">
        <PageHeader
          tag="Competitive Intelligence"
          title="Competitive Intel Radar"
          subtitle="Real-time tracking of competitor firm movements, lateral hires, and market positioning"
        />

        {/* Metric cards */}
        <div className="ci-metrics">
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

        <div className="ci-grid">
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
                <table className="ci-table">
                  <thead>
                    <tr>
                      {['Firm Name', 'Headcount', 'Practice Areas', 'Recent Laterals', 'Market Position', 'Threat Level'].map(h => (
                        <th key={h} className="ci-th">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {firmList.map((firm, i) => {
                      const pas = firm.practice_areas ?? []
                      const shownPAs = pas.slice(0, MAX_PA_TAGS)
                      const extraCount = pas.length - MAX_PA_TAGS
                      return (
                        <tr key={firm.id ?? firm.firm_id ?? i} className="ci-tr">
                          <td className="ci-td ci-td-name">
                            {firm.name ?? firm.firm_name ?? '—'}
                          </td>
                          <td className="ci-td ci-td-mono">
                            {firm.headcount != null ? Number(firm.headcount).toLocaleString() : '—'}
                          </td>
                          <td className="ci-td">
                            <div className="ci-tags-container">
                              {shownPAs.map((pa, idx) => (
                                <Tag key={idx} label={pa} color="navy" />
                              ))}
                              {extraCount > 0 && <span className="ci-tags-extra">+{extraCount}</span>}
                            </div>
                          </td>
                          <td className="ci-td ci-td-mono">
                            {firm.recent_laterals ?? firm.lateral_count ?? (firm.lateral_hires?.length ?? '—')}
                          </td>
                          <td className="ci-td ci-td-meta">
                            {firm.market_position ?? firm.position ?? '—'}
                          </td>
                          <td className="ci-td">
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
              <div className="ci-lat-list">
                {recentLaterals.map((hire, i) => (
                  <div key={hire.id ?? i} className="ci-lat-item">
                    <div className="ci-lat-name">
                      {hire.name ?? hire.hire_name ?? '—'}
                    </div>
                    <div className="ci-lat-org">
                      {hire.firm_name ?? hire.firm ?? '—'} · {hire.practice ?? hire.practice_area ?? '—'}
                    </div>
                    <div className="ci-lat-date">
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
