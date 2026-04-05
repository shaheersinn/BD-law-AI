/**
 * pages/MADarkSignalsPage.jsx — P12 Redesign
 * 
 * M&A dark signals: jets, satellite, pre-announcement.
 * Route: /m-a-dark-signals
 * Data: geo.jets(), geo.satellite(), signals.list()
 * DM Serif Display + DM Sans typographies with injected CSS.
 */

import { useEffect, useState } from 'react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { geo, signals } from '../api/client'

const MADS_CSS = `
.mads-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.mads-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.25rem;
  margin-bottom: 2rem;
}
.mads-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1.5rem;
}

/* Cards */
.mads-card {
  padding: 0.875rem 1rem;
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  margin-bottom: 0.75rem;
  transition: background var(--transition-fast), transform var(--transition-fast);
}
.mads-card:hover {
  background: var(--color-surface-container-high);
  transform: translateY(-2px);
}
.mads-card-label {
  font-family: var(--font-data);
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 0.35rem;
  line-height: 1.3;
}
.mads-card-meta {
  font-family: var(--font-data);
  font-size: 0.75rem;
  color: var(--color-on-surface-variant);
  margin-bottom: 0.25rem;
}
.mads-card-headline {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-primary);
  line-height: 1.4;
  margin-bottom: 0.5rem;
}

.mads-tags-row {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 6px;
}

@media (max-width: 980px) {
  .mads-grid { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('mads-styles')) {
    const el = document.createElement('style')
    el.id = 'mads-styles'
    el.textContent = MADS_CSS
    document.head.appendChild(el)
  }
}

export default function MADarkSignalsPage() {
  injectCSS()
  const [loading, setLoading] = useState(true)
  const [jets, setJets] = useState([])
  const [satellite, setSatellite] = useState([])
  const [maSignals, setMaSignals] = useState([])
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    setError(null)
    Promise.all([
      geo.jets(),
      geo.satellite(),
      signals.list(null, { signal_type: 'merger_acquisition', limit: 20 }),
    ])
      .then(([j, s, sigs]) => {
        setJets(j || [])
        setSatellite(s || [])
        setMaSignals(sigs || [])
      })
      .catch(err => setError(err.message || 'Failed to load M&A signals'))
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

  return (
    <AppShell>
      <div className="mads-root">
        <PageHeader
          tag="M&A Intelligence"
          title="M&A Dark Signals"
          subtitle="Private jet movements, satellite imagery, and pre-announcement deal signals"
        />

        {/* Metric cards */}
        <div className="mads-metrics">
          <MetricCard label="Jet Alerts"       value={loading ? <Skeleton width={32} height={24} /> : jets.length}      accent="navy" />
          <MetricCard label="Satellite Flags"  value={loading ? <Skeleton width={32} height={24} /> : satellite.length} accent="blue" />
          <MetricCard label="M&A Signals"      value={loading ? <Skeleton width={32} height={24} /> : maSignals.length} accent="red" />
        </div>

        {/* Three-panel grid */}
        <div className="mads-grid">
          {/* Private Jet Activity */}
          <Panel title="Private Jet Activity">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} width="100%" height={74} />)}
              </div>
            ) : jets.length === 0 ? (
              <EmptyState title="No jet alerts" message="No private jet activity detected" />
            ) : (
              jets.map((jet, i) => (
                <div key={i} className="mads-card">
                  <div className="mads-card-label">{jet.company || jet.tail_number || '—'}</div>
                  {jet.route && <div className="mads-card-meta">Route: {jet.route}</div>}
                  {jet.date && <div className="mads-card-meta">{jet.date}</div>}
                  {jet.urgency != null && (
                    <div className="mads-tags-row">
                      <Tag label={`Confidence ${jet.urgency}%`} color={jet.urgency > 75 ? 'red' : 'gold'} />
                    </div>
                  )}
                </div>
              ))
            )}
          </Panel>

          {/* Satellite Flags */}
          <Panel title="Satellite Flags">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} width="100%" height={74} />)}
              </div>
            ) : satellite.length === 0 ? (
              <EmptyState title="No satellite flags" message="No satellite imagery changes detected" />
            ) : (
              satellite.map((s, i) => (
                <div key={i} className="mads-card">
                  <div className="mads-card-label">{s.company || s.site || '—'}</div>
                  {s.change_type && <div className="mads-card-meta">{s.change_type}</div>}
                  {s.confidence != null && (
                    <div className="mads-tags-row">
                      <Tag label={`${s.confidence}% conf`} color={s.confidence > 75 ? 'gold' : 'default'} />
                    </div>
                  )}
                </div>
              ))
            )}
          </Panel>

          {/* Pre-Announcement Signals */}
          <Panel title="Pre-Announcement Signals">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} width="100%" height={74} />)}
              </div>
            ) : maSignals.length === 0 ? (
              <EmptyState title="No M&A signals" message="No pre-announcement signals detected" />
            ) : (
              maSignals.map((sig, i) => (
                <div key={i} className="mads-card">
                  <div className="mads-card-headline">
                    {sig.headline || sig.text?.slice(0, 80) || 'Signal detected'}
                  </div>
                  <div className="mads-tags-row">
                    {sig.source && <span className="mads-card-meta" style={{ margin: 0, marginRight: 4 }}>{sig.source}</span>}
                    {sig.confidence != null && (
                      <Tag
                        label={`${Math.round(sig.confidence * 100)}%`}
                        color={sig.confidence > 0.7 ? 'green' : sig.confidence > 0.5 ? 'gold' : 'default'}
                      />
                    )}
                  </div>
                </div>
              ))
            )}
          </Panel>
        </div>
      </div>
    </AppShell>
  )
}
