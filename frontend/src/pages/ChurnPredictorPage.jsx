/**
 * pages/ChurnPredictorPage.jsx — route /churn-predictor
 *
 * Identifies existing clients at risk of silent departure before they leave.
 * Data: clients.churnScores() for the risk table, clients.churnBrief(id) on demand.
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
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>

        <PageHeader
          tag="Client Intelligence"
          title="Silent Churn Predictor"
          subtitle="Identify clients showing early departure signals before they leave"
        />

        {/* Metric cards */}
        <section style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '1.25rem',
          marginBottom: '2.5rem',
        }}>
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
                <div key={i} style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                  <Skeleton width={160} height={16} />
                  <Skeleton width={100} height={16} />
                  <Skeleton width={80} height={16} />
                  <Skeleton width={80} height={16} />
                  <Skeleton width={70} height={22} />
                  <Skeleton width={100} height={32} />
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
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--color-surface-container-low)' }}>
                    {['Client Name', 'Last Matter', 'Wallet Share', 'Engagement Score', 'Churn Risk', 'Action'].map(h => (
                      <th key={h} style={{
                        padding: '9px 16px',
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.625rem',
                        fontWeight: 700,
                        color: 'var(--color-on-surface-variant)',
                        letterSpacing: '0.05em',
                        textTransform: 'uppercase',
                        textAlign: 'left',
                        whiteSpace: 'nowrap',
                      }}>{h}</th>
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
                      <tr
                        key={id}
                        style={{
                          background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent',
                          transition: 'background var(--transition-fast)',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
                        onMouseLeave={e => e.currentTarget.style.background = i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent'}
                      >
                        <td style={{
                          padding: '13px 16px',
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.875rem',
                          fontWeight: 600,
                          color: 'var(--color-primary)',
                          whiteSpace: 'nowrap',
                        }}>
                          {client.client_name || client.name || `Client ${id}`}
                        </td>
                        <td style={{
                          padding: '13px 16px',
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.8125rem',
                          color: 'var(--color-on-surface-variant)',
                          whiteSpace: 'nowrap',
                        }}>
                          {client.last_matter
                            ? new Date(client.last_matter).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
                            : '—'}
                        </td>
                        <td style={{
                          padding: '13px 16px',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.8125rem',
                          color: 'var(--color-on-surface)',
                          whiteSpace: 'nowrap',
                        }}>
                          {client.wallet_share != null ? `${(client.wallet_share * 100).toFixed(1)}%` : '—'}
                        </td>
                        <td style={{
                          padding: '13px 16px',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.8125rem',
                          color: 'var(--color-on-surface)',
                          whiteSpace: 'nowrap',
                        }}>
                          {client.engagement_score != null ? client.engagement_score.toFixed(2) : '—'}
                        </td>
                        <td style={{ padding: '13px 16px', whiteSpace: 'nowrap' }}>
                          <Tag label={churnTagLabel(score)} color={churnTagColor(score)} />
                        </td>
                        <td style={{ padding: '13px 16px', whiteSpace: 'nowrap' }}>
                          {hasBrief && !hasBrief.error ? (
                            <span style={{
                              fontFamily: 'var(--font-data)',
                              fontSize: '0.6875rem',
                              color: 'var(--color-secondary)',
                              fontWeight: 700,
                            }}>Brief Ready</span>
                          ) : (
                            <button
                              onClick={() => handleGenerateBrief(id)}
                              disabled={isBriefing}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 6,
                                padding: '6px 14px',
                                borderRadius: 'var(--radius-md)',
                                fontFamily: 'var(--font-data)',
                                fontSize: '0.6875rem',
                                fontWeight: 700,
                                letterSpacing: '0.04em',
                                textTransform: 'uppercase',
                                cursor: isBriefing ? 'default' : 'pointer',
                                background: isBriefing ? 'var(--color-surface-container-high)' : 'var(--color-primary)',
                                color: isBriefing ? 'var(--color-on-surface-variant)' : '#fff',
                                border: 'none',
                                transition: 'background var(--transition-fast)',
                                opacity: isBriefing ? 0.7 : 1,
                              }}
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
