/**
 * pages/ChurnPredictorPage.jsx — P11 Redesign
 *
 * Identifies existing clients at risk of silent departure before they leave.
 * Data: clients.churnScores() for the risk table, clients.churnBrief(id) on demand.
 * No inline styles. Uses injected CSS.
 */

import { useEffect, useState } from 'react'
import { UserMinus, Loader } from 'lucide-react'
import { clients } from '../api/client'
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

const CHURN_CSS = `
.cp-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.cp-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}

/* Table */
.cp-table {
  width: 100%;
  border-collapse: collapse;
}
.cp-th {
  padding: 9px 16px;
  font-family: var(--font-data);
  font-size: 0.625rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  text-align: left;
  white-space: nowrap;
  background: var(--color-surface-container-low);
}
.cp-tr {
  transition: background var(--transition-fast);
}
.cp-tr:nth-child(even) { background: var(--color-surface-container-low); }
.cp-tr:hover { background: var(--color-surface-container-high) !important; }

.cp-td {
  padding: 13px 16px;
  white-space: nowrap;
}
.cp-td-name {
  font-family: var(--font-data);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary);
}
.cp-td-date {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
}
.cp-td-mono {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--color-on-surface);
}

/* Actions */
.cp-btn-brief {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-md);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: none;
  cursor: pointer;
  transition: background var(--transition-fast), opacity var(--transition-fast);
}
.cp-btn-brief-active {
  background: var(--color-primary);
  color: #fff;
}
.cp-btn-brief-active:hover { opacity: 0.9; }
.cp-btn-brief-loading {
  background: var(--color-surface-container-high);
  color: var(--color-on-surface-variant);
  cursor: default;
  opacity: 0.7;
}
.cp-brief-ready {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  color: var(--color-secondary);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

@media (max-width: 980px) {
  .cp-metrics { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('cp-styles')) {
    const el = document.createElement('style')
    el.id = 'cp-styles'
    el.textContent = CHURN_CSS
    document.head.appendChild(el)
  }
}

function churnTagColor(score) {
  if (score > 0.7) return 'red'
  if (score > 0.4) return 'gold'
  return 'green'
}

function churnTagLabel(score) {
  if (score > 0.7) return 'High Risk'
  if (score > 0.4) return 'Watch'
  return 'Healthy'
}

export default function ChurnPredictorPage() {
  injectCSS()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [churnData, setChurnData] = useState([])
  const [briefLoading, setBriefLoading] = useState({})
  const [briefResults, setBriefResults] = useState({})

  useEffect(() => {
    clients.churnScores()
      .then(data => {
        const rows = Array.isArray(data) ? data : (data?.results || [])
        setChurnData(rows.slice().sort((a, b) => (b.churn_score || 0) - (a.churn_score || 0)))
      })
      .catch(err => setError(err.message || 'Failed to load churn scores'))
      .finally(() => setLoading(false))
  }, [])

  const handleGenerateBrief = (id) => {
    setBriefLoading(prev => ({ ...prev, [id]: true }))
    clients.churnBrief(id)
      .then(result => setBriefResults(prev => ({ ...prev, [id]: result })))
      .catch(() => setBriefResults(prev => ({ ...prev, [id]: { error: true } })))
      .finally(() => setBriefLoading(prev => ({ ...prev, [id]: false })))
  }

  const atRisk    = churnData.filter(c => (c.churn_score || 0) > 0.7).length
  const moderate  = churnData.filter(c => (c.churn_score || 0) > 0.4 && (c.churn_score || 0) <= 0.7).length
  const healthy   = churnData.filter(c => (c.churn_score || 0) <= 0.4).length

  if (error) return (
    <AppShell>
      <div style={{ padding: '2rem' }}>
        <ErrorState message={error} onRetry={() => { setError(null); setLoading(true) }} />
      </div>
    </AppShell>
  )

  return (
    <AppShell>
      <div className="cp-root">

        <PageHeader
          tag="Client Intelligence"
          title="Silent Churn Predictor"
          subtitle="Identify clients showing early departure signals before they leave"
        />

        {/* Metric cards */}
        <section className="cp-metrics">
          <MetricCard
            label="At Risk"
            value={loading ? <Skeleton width={48} height={24} /> : atRisk}
            accent="red"
          />
          <MetricCard
            label="Moderate Risk"
            value={loading ? <Skeleton width={48} height={24} /> : moderate}
            accent="gold"
          />
          <MetricCard
            label="Healthy"
            value={loading ? <Skeleton width={48} height={24} /> : healthy}
            accent="teal"
          />
        </section>

        {/* Client risk table */}
        <Panel title="Client Risk Scores">
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} style={{ display: 'flex', gap: '1rem' }}>
                  <Skeleton width="100%" height={36} />
                </div>
              ))}
            </div>
          ) : churnData.length === 0 ? (
            <EmptyState
              icon={<UserMinus size={32} />}
              title="No client scores yet"
              message="Client churn scores will appear once the scoring pipeline processes your client list."
            />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="cp-table">
                <thead>
                  <tr>
                    {['Client Name', 'Last Matter', 'Wallet Share', 'Engagement Score', 'Churn Risk', 'Action'].map(h => (
                      <th key={h} className="cp-th">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {churnData.map((client, i) => {
                    const id = client.client_id || client.id || i
                    const score = client.churn_score || 0
                    const isBriefing = briefLoading[id]
                    const hasBrief = briefResults[id]
                    return (
                      <tr key={id} className="cp-tr">
                        <td className="cp-td cp-td-name">{client.client_name || client.name || `Client ${id}`}</td>
                        <td className="cp-td cp-td-date">
                          {client.last_matter
                            ? new Date(client.last_matter).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
                            : '—'}
                        </td>
                        <td className="cp-td cp-td-mono">
                          {client.wallet_share != null ? `${(client.wallet_share * 100).toFixed(1)}%` : '—'}
                        </td>
                        <td className="cp-td cp-td-mono">
                          {client.engagement_score != null ? client.engagement_score.toFixed(2) : '—'}
                        </td>
                        <td className="cp-td">
                          <Tag label={churnTagLabel(score)} color={churnTagColor(score)} />
                        </td>
                        <td className="cp-td">
                          {hasBrief && !hasBrief.error ? (
                            <span className="cp-brief-ready">Brief Ready</span>
                          ) : (
                            <button
                              onClick={() => handleGenerateBrief(id)}
                              disabled={isBriefing}
                              className={`cp-btn-brief ${isBriefing ? 'cp-btn-brief-loading' : 'cp-btn-brief-active'}`}
                            >
                              {isBriefing && <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} />}
                              {isBriefing ? 'Generating...' : 'Generate Brief'}
                            </button>
                          )}
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
