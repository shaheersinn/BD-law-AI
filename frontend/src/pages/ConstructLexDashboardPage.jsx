/*
 * pages/ConstructLexDashboardPage.jsx — P4 Redesign
 *
 * BD Intelligence command center: velocity rankings and practice area demand.
 * 
 * Includes the Promise.allSettled logic injected earlier to ensure
 * partial API failures don't blank the entire page. Uses DM Serif Display.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, BarChart2 } from 'lucide-react'
import { scores, trends, triggers } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import {
  PageHeader,
  MetricCard,
  Panel,
  EmptyState,
  ErrorState,
} from '../components/ui/Primitives'

const DASHBOARD_CSS = `
.db-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}
.db-main-layout {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 2rem;
}
.db-vel-table {
  width: 100%;
  border-collapse: collapse;
}
.db-vel-th {
  padding: 9px 14px;
  font-family: var(--font-data);
  font-size: 0.625rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background: var(--color-surface-container-low);
  text-align: left;
  white-space: nowrap;
}
.db-vel-th-right { text-align: right; }
.db-vel-tr {
  cursor: pointer;
  transition: background var(--transition-fast);
}
.db-vel-tr:nth-child(even) { background: var(--color-surface-container-low); }
.db-vel-tr:hover { background: var(--color-surface-container-high) !important; }

.db-vel-td {
  padding: 13px 14px;
  white-space: nowrap;
}
.db-vel-rank {
  font-family: var(--font-editorial);
  font-size: 1.1rem;
  color: var(--color-on-surface-variant);
}
.db-vel-company {
  font-family: var(--font-data);
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--color-primary);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.db-vel-score {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  color: var(--color-primary);
  text-align: right;
  font-weight: 500;
}
.db-vel-badge-up {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 3px 8px; border-radius: var(--radius-full);
  background: var(--color-secondary-container);
  color: var(--color-on-secondary-container);
  font-family: var(--font-data); font-size: 0.625rem; font-weight: 700;
  letter-spacing: 0.04em;
}
.db-vel-badge-down {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 3px 8px; border-radius: var(--radius-full);
  background: var(--color-error-bg);
  color: var(--color-error);
  font-family: var(--font-data); font-size: 0.625rem; font-weight: 700;
  letter-spacing: 0.04em;
}
.db-vel-pa {
  font-family: var(--font-data);
  font-size: 0.8rem;
  color: var(--color-on-surface-variant);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.db-pa-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-low);
  margin-bottom: 8px;
  transition: background var(--transition-fast);
}
.db-pa-item:hover { background: var(--color-surface-container-high); }
.db-pa-item.featured {
  background: var(--color-secondary-container);
}
.db-pa-item.featured:hover {
  background: var(--color-secondary-container);
  opacity: 0.95;
}
.db-pa-label {
  font-family: var(--font-data);
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--color-on-surface);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.db-pa-item.featured .db-pa-label {
  font-weight: 700;
  color: var(--color-on-secondary-container);
}
.db-pa-count {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--color-surface-container-high);
  color: var(--color-on-surface-variant);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
}
.db-pa-item.featured .db-pa-count {
  background: var(--color-on-secondary-container);
  color: var(--color-secondary-container);
}

@media (max-width: 980px) {
  .db-grid { grid-template-columns: 1fr 1fr; }
  .db-main-layout { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .db-grid { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('db-styles')) {
    const el = document.createElement('style')
    el.id = 'db-styles'
    el.textContent = DASHBOARD_CSS
    document.head.appendChild(el)
  }
}

export default function ConstructLexDashboardPage() {
  injectCSS()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  const [stats, setStats] = useState(null)
  const [topVelocity, setTopVelocity] = useState([])
  const [practiceAreas, setPracticeAreas] = useState([])

  // Horizon toggle (visual only, per prompt)
  const [horizon, setHorizon] = useState('30d')

  useEffect(() => {
    // Retaining the Promise.allSettled logic to prevent partial failure blank-outs
    Promise.allSettled([
      triggers.stats(),
      scores.topVelocity(20),
      trends.practiceAreas(),
    ]).then(([statsResult, velocityResult, paResult]) => {
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

  const metricTriggers72h = stats?.total_72h
  const metricTriggers24h = stats?.total_24h
  const activeSources = stats?.by_source && typeof stats.by_source === 'object'
    ? Object.keys(stats.by_source).length
    : 0

  return (
    <AppShell>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2.5rem 2rem 4rem' }}>
        <PageHeader
          title="Command Center"
          subtitle="Live mandate signals, velocity rankings, and practice area demand"
        />

        <div className="db-grid">
          <MetricCard
            label="Triggers (72h)"
            value={loading ? <Skeleton width={60} height={28} /> : (metricTriggers72h ?? '—')}
            accent="red"
          />
          <MetricCard
            label="Triggers (24h)"
            value={loading ? <Skeleton width={60} height={28} /> : (metricTriggers24h ?? '—')}
            accent="green"
          />
          <MetricCard
            label="Companies Scored"
            value={loading ? <Skeleton width={60} height={28} /> : (topVelocity.length > 0 ? topVelocity.length : '—')}
            accent="blue"
          />
          <MetricCard
            label="Active Sources"
            value={loading ? <Skeleton width={60} height={28} /> : activeSources}
            accent="amber"
          />
        </div>

        <div className="db-main-layout">
          {/* Left: Velocity Rankings */}
          <Panel 
            title="Velocity Rankings"
            actions={
              <div className="cl-tabs" style={{ marginBottom: 0 }}>
                {['30d', '60d', '90d'].map(h => (
                  <button 
                    key={h} 
                    type="button"
                    className={`cl-tab ${horizon === h ? 'active' : ''}`}
                    onClick={() => setHorizon(h)}
                    style={{ padding: '4px 12px' }}
                  >
                    {h}
                  </button>
                ))}
              </div>
            }
          >
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} style={{ display: 'flex', gap: '1rem' }}>
                    <Skeleton width="100%" height={32} />
                  </div>
                ))}
              </div>
            ) : topVelocity.length === 0 ? (
              <EmptyState
                icon={<TrendingUp size={32} />}
                title="No data yet"
                message="No data yet — scrapers will populate this within 7 days"
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="db-vel-table">
                  <thead>
                    <tr>
                      <th className="db-vel-th">Rank</th>
                      <th className="db-vel-th">Company</th>
                      <th className="db-vel-th db-vel-th-right">Score</th>
                      <th className="db-vel-th">Velocity</th>
                      <th className="db-vel-th">Practice Area</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topVelocity.map((item, i) => (
                      <tr
                        key={item.company_id || i}
                        className="db-vel-tr"
                        onClick={() => item.company_id && navigate(`/companies/${item.company_id}`)}
                      >
                        <td className="db-vel-td db-vel-rank">{String(i + 1).padStart(2, '0')}</td>
                        <td className="db-vel-td db-vel-company">{item.company_name || item.name || `Company ${item.company_id}`}</td>
                        <td className="db-vel-td db-vel-score">
                          {item.top_score_30d != null || item.composite_score != null
                            ? `${((item.top_score_30d ?? item.composite_score) * 100).toFixed(1)}%`
                            : '—'}
                        </td>
                        <td className="db-vel-td">
                          <span className={(item.velocity_score || 0) >= 0 ? "db-vel-badge-up" : "db-vel-badge-down"}>
                            {(item.velocity_score || 0) >= 0 ? '↑' : '↓'} {Math.abs(item.velocity_score || 0).toFixed(1)}
                          </span>
                        </td>
                        <td className="db-vel-td db-vel-pa">{item.top_practice_area || item.top_practice || '—'}</td>
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
                  <Skeleton key={i} width="100%" height={36} />
                ))}
              </div>
            ) : top10PA.length === 0 ? (
              <EmptyState
                icon={<BarChart2 size={32} />}
                title="No trend data yet"
                message="No data yet — scrapers will populate this within 7 days"
              />
            ) : (
              <div>
                {top10PA.map((pa, i) => (
                  <div key={pa.practice_area || i} className={`db-pa-item ${i === 0 ? 'featured' : ''}`}>
                    <span className="db-pa-label">{pa.practice_area || pa.name || `Area ${i + 1}`}</span>
                    <span className="db-pa-count">{pa.count_7d ?? 0}</span>
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
