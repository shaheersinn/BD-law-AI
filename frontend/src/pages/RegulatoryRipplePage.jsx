/**
 * pages/RegulatoryRipplePage.jsx — OSC enforcement actions and regulatory signals.
 * Route: /regulatory-ripple
 * Data: triggers.live({ source: 'OSC' }), signals.list()
 */

import { useEffect, useState } from 'react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { triggers, signals } from '../api/client'

export default function RegulatoryRipplePage() {
  const [loading, setLoading] = useState(true)
  const [oscTriggers, setOscTriggers] = useState([])
  const [regSignals, setRegSignals] = useState([])
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    setError(null)
    Promise.all([
      triggers.live({ source: 'OSC' }),
      signals.list(null, { signal_type: 'regulatory', limit: 10 }),
    ])
      .then(([osc, sigs]) => {
        setOscTriggers(osc || [])
        setRegSignals(sigs || [])
      })
      .catch(err => setError(err.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (error) return (
    <AppShell>
      <div style={{ padding: '2rem' }}>
        <ErrorState message={error} onRetry={load} />
      </div>
    </AppShell>
  )

  const highImpact = oscTriggers.filter(t => (t.urgency || 0) > 80).length

  return (
    <AppShell>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>
        <PageHeader
          tag="Regulatory Intelligence"
          title="Regulatory Ripple Tracker"
          subtitle="OSC enforcement actions and regulatory signals with cascade risk analysis"
        />

        {/* Metric cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '1.25rem',
          marginBottom: '2rem',
        }}>
          <MetricCard label="Active Proceedings" value={loading ? '—' : oscTriggers.length} accent="red" />
          <MetricCard label="High Impact"         value={loading ? '—' : highImpact}        accent="gold" />
          <MetricCard label="Avg Lead Time"       value="14 days"                            accent="blue" sub="Historical average" />
        </div>

        {/* Two-panel layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          {/* OSC Enforcement Actions */}
          <Panel title="OSC Enforcement Actions">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} width="100%" height={72} />
                ))}
              </div>
            ) : oscTriggers.length === 0 ? (
              <EmptyState title="No OSC actions" message="No OSC enforcement proceedings found" />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {oscTriggers.map((item, i) => (
                  <div key={i} style={{
                    padding: '0.75rem',
                    background: 'var(--color-surface-container-low)',
                    borderRadius: 'var(--radius-md)',
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: '0.375rem',
                    }}>
                      <div style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: 'var(--color-primary)',
                      }}>{item.company || item.company_name || '—'}</div>
                      {item.urgency != null && (
                        <Tag
                          label={`${item.urgency}`}
                          color={item.urgency > 80 ? 'red' : item.urgency > 60 ? 'gold' : 'green'}
                        />
                      )}
                    </div>
                    {item.type && (
                      <div style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.6875rem',
                        color: 'var(--color-on-surface-variant)',
                        marginBottom: '0.25rem',
                      }}>{item.type}</div>
                    )}
                    {item.desc && (
                      <p style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.8125rem',
                        color: 'var(--color-on-surface-variant)',
                        lineHeight: 1.5,
                        margin: 0,
                      }}>{item.desc}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Panel>

          {/* Regulatory Signals */}
          <Panel title="Regulatory Signals">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} width="100%" height={56} />
                ))}
              </div>
            ) : regSignals.length === 0 ? (
              <EmptyState title="No signals" message="No regulatory signals in the last 90 days" />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {regSignals.map((sig, i) => (
                  <div key={i} style={{
                    padding: '0.75rem',
                    background: 'var(--color-surface-container-low)',
                    borderRadius: 'var(--radius-md)',
                  }}>
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color: 'var(--color-primary)',
                      marginBottom: '0.25rem',
                      lineHeight: 1.4,
                    }}>
                      {sig.headline || sig.text?.slice(0, 100) || 'Signal detected'}
                    </div>
                    <div style={{
                      display: 'flex',
                      gap: '0.5rem',
                      alignItems: 'center',
                    }}>
                      {sig.source && (
                        <span style={{
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.6875rem',
                          color: 'var(--color-on-surface-variant)',
                        }}>{sig.source}</span>
                      )}
                      {sig.published_at && (
                        <span style={{
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.6875rem',
                          color: 'var(--color-on-surface-variant)',
                        }}>· {new Date(sig.published_at).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' })}</span>
                      )}
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
