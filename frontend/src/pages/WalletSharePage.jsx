/**
 * pages/WalletSharePage.jsx — P15 Redesign
 * 
 * Legal spend penetration and revenue growth opportunities across client portfolio.
 * Removed inline styles. Uses injected CSS and standard design metrics.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { DollarSign } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { clients } from '../api/client'

const WALL_CSS = `
.ws-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.ws-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}

/* Table */
.ws-table {
  width: 100%;
  border-collapse: collapse;
}
.ws-th {
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
.ws-tr {
  transition: background var(--transition-fast);
}
.ws-tr:nth-child(even) { background: var(--color-surface-container-low); }
.ws-tr:hover { background: var(--color-surface-container-high) !important; }

.ws-td {
  padding: 13px 12px;
  white-space: nowrap;
}
.ws-td-primary {
  font-family: var(--font-editorial);
  font-size: 1.05rem;
  font-weight: 400;
  color: var(--color-primary);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ws-td-amount {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-on-surface);
}
.ws-td-mono {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
}
.ws-yoy {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  font-weight: 700;
}

.ws-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ws-bar-outer {
  flex: 1;
  height: 6px;
  background: var(--color-surface-container-high);
  border-radius: var(--radius-full);
  overflow: hidden;
  min-width: 60px;
}
.ws-bar-inner {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}
.ws-bar-label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
}

.ws-tags-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.ws-tags-extra {
  font-family: var(--font-data);
  font-size: 0.625rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
}

@media (max-width: 980px) {
  .ws-metrics { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 640px) {
  .ws-metrics { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('ws-styles')) {
    const el = document.createElement('style')
    el.id = 'ws-styles'
    el.textContent = WALL_CSS
    document.head.appendChild(el)
  }
}

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
    if (n >= 1_000_000) return \`$\${(n / 1_000_000).toFixed(1)}M\`
    if (n >= 1_000) return \`$\${(n / 1_000).toFixed(0)}K\`
  }
  return \`$\${n.toLocaleString()}\`
}

function formatPct(val) {
  if (val == null || isNaN(val)) return '—'
  return \`\${Math.round(Number(val))}%\`
}

function formatYoY(val) {
  if (val == null || isNaN(val)) return '—'
  const n = Number(val)
  const sign = n >= 0 ? '+' : ''
  return \`\${sign}\${n.toFixed(1)}%\`
}

function yoyColor(val) {
  if (val == null) return 'var(--color-on-surface-variant)'
  return Number(val) >= 0 ? 'var(--color-success)' : 'var(--color-error)'
}

export default function WalletSharePage() {
  injectCSS()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)

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
      <div className="ws-root">
        <PageHeader
          tag="Revenue Intelligence"
          title="Wallet Share Analysis"
          subtitle="Legal spend penetration and revenue growth opportunities across client portfolio"
        />

        {/* Metric cards */}
        <div className="ws-metrics">
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
                value={\`\${stats.avgWalletShare}%\`}
                sub="of total legal spend"
                accent="blue"
              />
              <MetricCard
                label="Growth Opportunities"
                value={stats.growthOpportunities}
                sub="below 30% share"
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
              <table className="ws-table">
                <thead>
                  <tr>
                    {['Client', 'Total Billing', 'Our Share', 'Competitor Est.', 'YoY Growth', 'Practice Groups', 'Opportunity'].map(h => (
                      <th key={h} className="ws-th">{h}</th>
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
                      <tr key={client.id ?? client.client_id ?? i} className="ws-tr">
                        <td className="ws-td ws-td-primary">
                          {client.name ?? client.company_name ?? client.client_name ?? '—'}
                        </td>
                        <td className="ws-td ws-td-amount">
                          {formatCurrency(client.total_billing ?? client.billed)}
                        </td>
                        <td className="ws-td" style={{ minWidth: 120 }}>
                          <div className="ws-bar-wrap">
                            <div className="ws-bar-outer">
                              <div
                                className="ws-bar-inner"
                                style={{
                                  width: \`\${Math.min(100, sharePct)}%\`,
                                  background: walletShareColor(sharePct),
                                }}
                              />
                            </div>
                            <span className="ws-bar-label" style={{ color: walletShareColor(sharePct) }}>
                              {formatPct(sharePct)}
                            </span>
                          </div>
                        </td>
                        <td className="ws-td ws-td-mono">
                          {competitorEst != null ? formatCurrency(competitorEst) : '—'}
                        </td>
                        <td className="ws-td ws-yoy" style={{ color: yoyColor(yoy) }}>
                          {formatYoY(yoy)}
                        </td>
                        <td className="ws-td" style={{ maxWidth: 160 }}>
                          <div className="ws-tags-grid">
                            {practiceGroups.slice(0, 2).map((pg, idx) => (
                              <Tag key={idx} label={pg} color="navy" />
                            ))}
                            {practiceGroups.length > 2 && (
                              <span className="ws-tags-extra">+{practiceGroups.length - 2}</span>
                            )}
                            {practiceGroups.length === 0 && (
                              <span className="ws-tags-extra">—</span>
                            )}
                          </div>
                        </td>
                        <td className="ws-td">
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
