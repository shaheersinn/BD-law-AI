/**
 * pages/PitchAutopsyPage.jsx — P19 Redesign
 * 
 * Win/loss analysis with signal correlation and partner coaching insights.
 * Uses injected CSS to adhere to DM Sans/Serif type system, removing inline styles.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { bd } from '../api/client'

const AUTOPSY_CSS = `
.pa-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.pa-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}
.pa-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

/* Filters */
.pa-filters {
  display: flex;
  gap: 6px;
}
.pa-filter-btn {
  padding: 5px 12px;
  border-radius: var(--radius-full);
  font-family: var(--font-data);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: none;
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.pa-filter-btn.active {
  background: var(--color-primary);
  color: #fff;
}
.pa-filter-btn.inactive {
  background: var(--color-surface-container-high);
  color: var(--color-on-surface-variant);
}

/* Table */
.pa-table {
  width: 100%;
  border-collapse: collapse;
}
.pa-th {
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
.pa-tr {
  transition: background var(--transition-fast);
}
.pa-tr:nth-child(even) { background: var(--color-surface-container-low); }
.pa-tr:hover { background: var(--color-surface-container-high) !important; }

.pa-td {
  padding: 13px 12px;
  white-space: nowrap;
}
.pa-td-date {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
}
.pa-td-primary {
  font-family: var(--font-data);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pa-td-secondary {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pa-td-amount {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-on-surface);
}

/* Win Rate Bars */
.pa-wr-item {
  margin-bottom: 0.75rem;
}
.pa-wr-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.pa-wr-label {
  font-family: var(--font-data);
  font-size: 0.75rem;
  color: var(--color-on-surface);
  max-width: 75%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pa-wr-pct {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
}
.pa-wr-track {
  height: 4px;
  background: var(--color-surface-container-high);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.pa-wr-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}
.pa-wr-meta {
  font-family: var(--font-data);
  font-size: 0.625rem;
  color: var(--color-on-surface-variant);
  margin-top: 3px;
}

@media (max-width: 980px) {
  .pa-grid { grid-template-columns: 1fr; }
  .pa-metrics { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 640px) {
  .pa-metrics { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('pa-styles')) {
    const el = document.createElement('style')
    el.id = 'pa-styles'
    el.textContent = AUTOPSY_CSS
    document.head.appendChild(el)
  }
}

const FILTERS = ['ALL', 'WON', 'LOST', 'PENDING']

function outcomeColor(outcome) {
  if (!outcome) return 'default'
  const o = outcome.toLowerCase()
  if (o === 'won') return 'green'
  if (o === 'lost') return 'red'
  if (o === 'pending') return 'gold'
  return 'default'
}

function formatCurrency(val) {
  if (val == null || isNaN(val)) return '—'
  const n = Number(val)
  if (n >= 1_000_000) return \`$\${(n / 1_000_000).toFixed(1)}M\`
  if (n >= 1_000) return \`$\${(n / 1_000).toFixed(0)}K\`
  return \`$\${n.toLocaleString()}\`
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d)) return dateStr
  return d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function PitchAutopsyPage() {
  injectCSS()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    bd.pitchHistory()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load pitch history'))
      .finally(() => setLoading(false))
  }, [])

  const handleRetry = () => {
    setError(null)
    setLoading(true)
    bd.pitchHistory()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load pitch history'))
      .finally(() => setLoading(false))
  }

  const stats = useMemo(() => {
    if (!data.length) return { winRate: 0, total: 0, avgDeal: 0, lostRevenue: 0 }
    const won = data.filter(d => d.outcome?.toLowerCase() === 'won')
    const lost = data.filter(d => d.outcome?.toLowerCase() === 'lost')
    const total = data.length
    const winRate = total > 0 ? Math.round((won.length / total) * 100) : 0
    const allValues = data.map(d => Number(d.deal_value ?? 0)).filter(v => !isNaN(v))
    const avgDeal = allValues.length > 0 ? allValues.reduce((a, b) => a + b, 0) / allValues.length : 0
    const lostRevenue = lost.reduce((acc, d) => acc + Number(d.deal_value ?? 0), 0)
    return { winRate, total, avgDeal, lostRevenue }
  }, [data])

  const winRateByPA = useMemo(() => {
    const map = {}
    for (const pitch of data) {
      const pa = pitch.practice_area ?? 'Unknown'
      if (!map[pa]) map[pa] = { won: 0, total: 0 }
      map[pa].total++
      if (pitch.outcome?.toLowerCase() === 'won') map[pa].won++
    }
    return Object.entries(map)
      .map(([pa, { won, total }]) => ({ pa, rate: total > 0 ? Math.round((won / total) * 100) : 0, total }))
      .sort((a, b) => b.rate - a.rate)
  }, [data])

  const filtered = useMemo(() => {
    if (filter === 'ALL') return data
    return data.filter(d => d.outcome?.toUpperCase() === filter)
  }, [data, filter])

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
      <div className="pa-root">
        <PageHeader
          tag="BD Performance"
          title="Pitch Autopsy"
          subtitle="Win/loss analysis with signal correlation and partner coaching insights"
        />

        {/* Metric cards */}
        <div className="pa-metrics">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={100} radius={12} />)
          ) : (
            <>
              <MetricCard label="Win Rate" value={\`\${stats.winRate}%\`} sub="of closed pitches" accent="teal" />
              <MetricCard label="Total Pitches" value={stats.total} sub="all time" accent="blue" />
              <MetricCard label="Avg Deal Size" value={formatCurrency(stats.avgDeal)} sub="per pitch" accent="gold" />
              <MetricCard label="Lost Revenue" value={formatCurrency(stats.lostRevenue)} sub="closed-lost total" accent="red" />
            </>
          )}
        </div>

        <div className="pa-grid">
          {/* Pitch History */}
          <Panel
            title="Pitch History"
            actions={
              <div className="pa-filters">
                {FILTERS.map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={\`pa-filter-btn \${filter === f ? 'active' : 'inactive'}\`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            }
          >
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Array.from({ length: 7 }).map((_, i) => (
                  <Skeleton key={i} height={44} radius={6} style={{ opacity: 1 - i * 0.08 }} />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <EmptyState
                icon={<TrendingUp size={32} />}
                title="No pitches found"
                message={filter === 'ALL' ? 'Pitch history will appear once BD data is available' : \`No \${filter.toLowerCase()} pitches recorded\`}
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="pa-table">
                  <thead>
                    <tr>
                      {['Date', 'Company', 'Practice Area', 'Partner', 'Deal Value', 'Outcome', 'Reason'].map(h => (
                        <th key={h} className="pa-th">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((pitch, i) => (
                      <tr key={pitch.id ?? i} className="pa-tr">
                        <td className="pa-td pa-td-date">
                          {formatDate(pitch.date ?? pitch.pitch_date ?? pitch.created_at)}
                        </td>
                        <td className="pa-td pa-td-primary">
                          {pitch.company_name ?? pitch.company ?? '—'}
                        </td>
                        <td className="pa-td pa-td-secondary">
                          {pitch.practice_area ?? '—'}
                        </td>
                        <td className="pa-td pa-td-secondary">
                          {pitch.partner ?? pitch.partner_name ?? '—'}
                        </td>
                        <td className="pa-td pa-td-amount">
                          {formatCurrency(pitch.deal_value)}
                        </td>
                        <td className="pa-td">
                          <Tag label={pitch.outcome ?? 'Unknown'} color={outcomeColor(pitch.outcome)} />
                        </td>
                        <td className="pa-td pa-td-secondary" style={{ maxWidth: 160 }}>
                          {pitch.reason ?? pitch.loss_reason ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          {/* Win Rate by Practice Area */}
          <Panel title="Win Rate by Practice Area">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} height={36} radius={6} style={{ opacity: 1 - i * 0.07 }} />
                ))}
              </div>
            ) : winRateByPA.length === 0 ? (
              <EmptyState title="No data" message="Win rate data will appear once pitches are recorded" />
            ) : (
              <div style={{ padding: '0.5rem 0' }}>
                {winRateByPA.map(({ pa, rate, total }) => {
                  const rColor = rate >= 50 ? 'var(--color-secondary)' : rate >= 25 ? '#d97706' : 'var(--color-error)'
                  return (
                    <div key={pa} className="pa-wr-item">
                      <div className="pa-wr-header">
                        <span className="pa-wr-label">{pa}</span>
                        <span className="pa-wr-pct" style={{ color: rColor }}>{rate}%</span>
                      </div>
                      <div className="pa-wr-track">
                        <div
                          className="pa-wr-fill"
                          style={{
                            width: \`\${rate}%\`,
                            background: rColor,
                          }}
                        />
                      </div>
                      <div className="pa-wr-meta">
                        {total} pitch{total !== 1 ? 'es' : ''}
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
