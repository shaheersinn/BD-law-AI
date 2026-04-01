/**
 * pages/PitchAutopsyPage.jsx — route /pitch-autopsy
 * Win/loss analysis with signal correlation and partner coaching insights.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { bd } from '../api/client'

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
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toLocaleString()}`
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d)) return dateStr
  return d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function PitchAutopsyPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('ALL')
  const [hoveredRow, setHoveredRow] = useState(null)

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
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>
        <PageHeader
          tag="BD Performance"
          title="Pitch Autopsy"
          subtitle="Win/loss analysis with signal correlation and partner coaching insights"
        />

        {/* Metric cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={100} radius={12} />)
          ) : (
            <>
              <MetricCard label="Win Rate" value={`${stats.winRate}%`} sub="of closed pitches" accent="teal" />
              <MetricCard label="Total Pitches" value={stats.total} sub="all time" accent="blue" />
              <MetricCard label="Avg Deal Size" value={formatCurrency(stats.avgDeal)} sub="per pitch" accent="gold" />
              <MetricCard label="Lost Revenue" value={formatCurrency(stats.lostRevenue)} sub="closed-lost total" accent="red" />
            </>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
          {/* Pitch History */}
          <Panel
            title="Pitch History"
            actions={
              <div style={{ display: 'flex', gap: '0.375rem' }}>
                {FILTERS.map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    style={{
                      padding: '0.25rem 0.625rem',
                      borderRadius: 'var(--radius-full)',
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.625rem',
                      fontWeight: 700,
                      letterSpacing: '0.04em',
                      textTransform: 'uppercase',
                      border: 'none',
                      cursor: 'pointer',
                      background: filter === f ? 'var(--color-primary)' : 'var(--color-surface-container-high)',
                      color: filter === f ? '#fff' : 'var(--color-on-surface-variant)',
                      transition: 'background 0.12s, color 0.12s',
                    }}
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
                message={filter === 'ALL' ? 'Pitch history will appear once BD data is available' : `No ${filter.toLowerCase()} pitches recorded`}
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-surface-container-high)' }}>
                      {['Date', 'Company', 'Practice Area', 'Partner', 'Deal Value', 'Outcome', 'Reason'].map(h => (
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
                    {filtered.map((pitch, i) => (
                      <tr
                        key={pitch.id ?? i}
                        onMouseEnter={() => setHoveredRow(i)}
                        onMouseLeave={() => setHoveredRow(null)}
                        style={{
                          borderBottom: '1px solid var(--color-surface-container-high)',
                          background: hoveredRow === i ? 'var(--color-surface-container-low)' : 'transparent',
                          transition: 'background 0.12s',
                          cursor: 'default',
                        }}
                      >
                        <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', whiteSpace: 'nowrap' }}>
                          {formatDate(pitch.date ?? pitch.pitch_date ?? pitch.created_at)}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-on-surface)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {pitch.company_name ?? pitch.company ?? '—'}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {pitch.practice_area ?? '—'}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', whiteSpace: 'nowrap' }}>
                          {pitch.partner ?? pitch.partner_name ?? '—'}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-on-surface)', whiteSpace: 'nowrap' }}>
                          {formatCurrency(pitch.deal_value)}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem' }}>
                          <Tag label={pitch.outcome ?? 'Unknown'} color={outcomeColor(pitch.outcome)} />
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {winRateByPA.map(({ pa, rate, total }) => (
                  <div key={pa}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <span style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.75rem',
                        color: 'var(--color-on-surface)',
                        maxWidth: '75%',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>{pa}</span>
                      <span style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.6875rem',
                        fontWeight: 700,
                        color: rate >= 50 ? 'var(--color-secondary)' : rate >= 25 ? '#d97706' : 'var(--color-error)',
                      }}>{rate}%</span>
                    </div>
                    <div style={{ height: 4, background: 'var(--color-surface-container-high)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${rate}%`,
                        background: rate >= 50 ? 'var(--color-secondary)' : rate >= 25 ? '#d97706' : 'var(--color-error)',
                        borderRadius: 'var(--radius-full)',
                        transition: 'width 0.3s ease',
                      }} />
                    </div>
                    <div style={{ fontFamily: 'var(--font-data)', fontSize: '0.625rem', color: 'var(--color-on-surface-variant)', marginTop: '0.125rem' }}>
                      {total} pitch{total !== 1 ? 'es' : ''}
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
