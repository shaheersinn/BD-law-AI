/**
 * pages/RegulatoryRipplePage.jsx — P21 Redesign
 * 
 * OSC enforcement actions and regulatory signals.
 * Restyled with injected CSS and strict typography (DM Sans / DM Serif).
 * Data: triggers.live({ source: 'OSC' }), signals.list()
 */

import { useEffect, useState } from 'react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { triggers, signals } from '../api/client'

const OSC_CSS = `
.osc-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.osc-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.25rem;
  margin-bottom: 2rem;
}
.osc-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

/* Actions List */
.osc-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.osc-card {
  padding: 0.875rem;
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  transition: transform var(--transition-fast);
}
.osc-card:hover {
  transform: translateX(2px);
}
.osc-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.375rem;
}
.osc-card-company {
  font-family: var(--font-data);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary);
}
.osc-card-type {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  color: var(--color-on-surface-variant);
  margin-bottom: 0.375rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.osc-card-desc {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
  line-height: 1.5;
  margin: 0;
}

/* Regulatory Signal */
.reg-sig-headline {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 0.375rem;
  line-height: 1.4;
}
.reg-sig-meta {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.reg-sig-meta-text {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  color: var(--color-on-surface-variant);
}

@media (max-width: 768px) {
  .osc-grid { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('osc-styles')) {
    const el = document.createElement('style')
    el.id = 'osc-styles'
    el.textContent = OSC_CSS
    document.head.appendChild(el)
  }
}

export default function RegulatoryRipplePage() {
  injectCSS()
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
      <div className="osc-root">
        <PageHeader
          tag="Regulatory Intelligence"
          title="Regulatory Ripple Tracker"
          subtitle="OSC enforcement actions and regulatory signals with cascade risk analysis"
        />

        {/* Metric cards */}
        <div className="osc-metrics">
          <MetricCard label="Active Proceedings" value={loading ? '—' : oscTriggers.length} accent="red" />
          <MetricCard label="High Impact" value={loading ? '—' : highImpact} accent="gold" />
          <MetricCard label="Avg Lead Time" value="14 days" accent="blue" sub="Historical average" />
        </div>

        {/* Two-panel layout */}
        <div className="osc-grid">
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
              <div className="osc-list">
                {oscTriggers.map((item, i) => (
                  <div key={i} className="osc-card">
                    <div className="osc-card-header">
                      <div className="osc-card-company">{item.company || item.company_name || '—'}</div>
                      {item.urgency != null && (
                        <Tag
                          label={`${item.urgency}`}
                          color={item.urgency > 80 ? 'red' : item.urgency > 60 ? 'gold' : 'green'}
                        />
                      )}
                    </div>
                    {item.type && (
                      <div className="osc-card-type">{item.type}</div>
                    )}
                    {item.desc && (
                      <p className="osc-card-desc">{item.desc}</p>
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
              <div className="osc-list">
                {regSignals.map((sig, i) => (
                  <div key={i} className="osc-card">
                    <div className="reg-sig-headline">
                      {sig.headline || sig.text?.slice(0, 100) || 'Signal detected'}
                    </div>
                    <div className="reg-sig-meta">
                      {sig.source && (
                        <span className="reg-sig-meta-text">{sig.source}</span>
                      )}
                      {sig.published_at && (
                        <span className="reg-sig-meta-text">· {new Date(sig.published_at).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' })}</span>
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
