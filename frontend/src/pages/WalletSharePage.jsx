/**
 * pages/WalletSharePage.jsx — route /wallet-share
 * Legal spend penetration and revenue growth opportunities across client portfolio.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { DollarSign } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { clients } from '../api/client'

function walletShareColor(pct) {
  if (pct == null) return 'var(--color-surface-container-high)'
  if (pct > 50) return 'var(--color-secondary)'
  if (pct > 30) return '#d97706'
  return 'var(--color-error)'
}

function opportunityColor(level) {
  if (!level) return 'default'
  const l = level.toLowerCase()
  if (l === 'high') return 'green'
  if (l === 'medium') return 'gold'
  return 'default'
}

function formatCurrency(val, short = true) {
  if (val == null || isNaN(val)) return '—'
  const n = Number(val)
  if (short) {
    if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  }
  return `$${n.toLocaleString()}`
}

function formatPct(val) {
  if (val == null || isNaN(val)) return '—'
  return `${Math.round(Number(val))}%`
}

function formatYoY(val) {
  if (val == null || isNaN(val)) return '—'
  const n = Number(val)
  const sign = n >= 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

function yoyColor(val) {
  if (val == null) return 'var(--color-on-surface-variant)'
  return Number(val) >= 0 ? 'var(--color-success)' : 'var(--color-error)'
}

export default function WalletSharePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)
  const [hoveredRow, setHoveredRow] = useState(null)

  useEffect(() => {
    clients.walletShare()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load wallet share data'))
      .finally(() => setLoading(false))
  }, [])

  const handleRetry = () => {
    setError(null)
    setLoading(true)
    clients.walletShare()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load wallet share data'))
      .finally(() => setLoading(false))
  }

  const clientList = useMemo(() => {
    if (Array.isArray(data)) return data
    return data.clients ?? data.items ?? []
  }, [data])

  const stats = useMemo(() => {
    const totalBilled = clientList.reduce((acc, c) => acc + Number(c.total_billing ?? c.billed ?? 0), 0)
    const shareVals = clientList.map(c => Number(c.wallet_share ?? c.share_pct ?? 0)).filter(v => !isNaN(v))
    const avgWalletShare = shareVals.length > 0 ? Math.round(shareVals.reduce((a, b) => a + b, 0) / shareVals.length) : 0
    const growthOpportunities = clientList.filter(c => Number(c.wallet_share ?? c.share_pct ?? 100) < 30).length
    const atRisk = clientList
      .filter(c => c.churn_risk === true || c.churn_risk === 'high' || c.status === 'at_risk')
      .reduce((acc, c) => acc + Number(c.total_billing ?? c.billed ?? 0), 0)
    return { totalBilled, avgWalletShare, growthOpportunities, atRisk }
  }, [clientList])

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
          tag="Revenue Intelligence"
          title="Wallet Share Analysis"
          subtitle="Legal spend penetration and revenue growth opportunities across client portfolio"
        />

        {/* Metric cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={100} radius={12} />)
          ) : (
            <>
              <MetricCard
                label="Total Billed"
                value={formatCurrency(stats.totalBilled)}
                sub="across all clients"
                accent="teal"
              />
              <MetricCard
                label="Avg Wallet Share"
                value={`${stats.avgWalletShare}%`}
                sub="of total legal spend"
                accent="blue"
              />
              <MetricCard
                label="Growth Opportunities"
                value={stats.growthOpportunities}
                sub="clients below 30% share"
                accent="gold"
              />
              <MetricCard
                label="At Risk Revenue"
                value={formatCurrency(stats.atRisk)}
                sub="churn-risk clients"
                accent="red"
              />
            </>
          )}
        </div>

        {/* Client Wallet Analysis */}
        <Panel title="Client Wallet Analysis">
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} height={52} radius={6} style={{ opacity: 1 - i * 0.08 }} />
              ))}
            </div>
          ) : clientList.length === 0 ? (
            <EmptyState
              icon={<DollarSign size={32} />}
              title="No wallet share data"
              message="Client billing data will populate as financial records are ingested"
            />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: '0.8125rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-surface-container-high)' }}>
                    {['Client', 'Total Billing', 'Our Share', 'Competitor Est.', 'YoY Growth', 'Practice Groups', 'Opportunity'].map(h => (
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
                  {clientList.map((client, i) => {
                    const sharePct = Number(client.wallet_share ?? client.share_pct ?? 0)
                    const competitorEst = client.competitor_estimated_share ?? client.competitor_est
                    const practiceGroups = client.practice_groups ?? client.practice_areas ?? []
                    const yoy = client.yoy_growth ?? client.growth_rate

                    return (
                      <tr
                        key={client.id ?? client.client_id ?? i}
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
                          {client.name ?? client.company_name ?? client.client_name ?? '—'}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-on-surface)', whiteSpace: 'nowrap' }}>
                          {formatCurrency(client.total_billing ?? client.billed)}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', minWidth: 120 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ flex: 1, height: 6, background: 'var(--color-surface-container-high)', borderRadius: 'var(--radius-full)', overflow: 'hidden', minWidth: 60 }}>
                              <div style={{
                                height: '100%',
                                width: `${Math.min(100, sharePct)}%`,
                                background: walletShareColor(sharePct),
                                borderRadius: 'var(--radius-full)',
                                transition: 'width 0.3s ease',
                              }} />
                            </div>
                            <span style={{ fontFamily: 'var(--font-data)', fontSize: '0.75rem', fontWeight: 700, color: walletShareColor(sharePct), whiteSpace: 'nowrap' }}>
                              {formatPct(sharePct)}
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', whiteSpace: 'nowrap' }}>
                          {competitorEst != null ? formatCurrency(competitorEst) : '—'}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: yoyColor(yoy), whiteSpace: 'nowrap' }}>
                          {formatYoY(yoy)}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem', maxWidth: 160 }}>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                            {practiceGroups.slice(0, 2).map((pg, idx) => (
                              <Tag key={idx} label={pg} color="navy" />
                            ))}
                            {practiceGroups.length > 2 && (
                              <span style={{ fontFamily: 'var(--font-data)', fontSize: '0.625rem', fontWeight: 700, color: 'var(--color-on-surface-variant)' }}>
                                +{practiceGroups.length - 2}
                              </span>
                            )}
                            {practiceGroups.length === 0 && (
                              <span style={{ fontFamily: 'var(--font-data)', fontSize: '0.75rem', color: 'var(--color-on-surface-variant)' }}>—</span>
                            )}
                          </div>
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem' }}>
                          <Tag
                            label={client.opportunity ?? client.opportunity_level ?? 'Low'}
                            color={opportunityColor(client.opportunity ?? client.opportunity_level)}
                          />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </AppShell>
  )
}
