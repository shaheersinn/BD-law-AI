/**
 * pages/MADarkSignalsPage.jsx — M&A dark signals: jets, satellite, pre-announcement.
 * Route: /m-a-dark-signals
 * Data: geo.jets(), geo.satellite(), signals.list()
 */

import { useEffect, useState } from 'react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { geo, signals } from '../api/client'

export default function MADarkSignalsPage() {
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

  const cardStyle = {
    padding: '0.75rem',
    background: 'var(--color-surface-container-low)',
    borderRadius: 'var(--radius-md)',
    marginBottom: '0.75rem',
  }

  const labelStyle = {
    fontFamily: 'var(--font-data)',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--color-primary)',
    marginBottom: '0.25rem',
  }

  const metaStyle = {
    fontFamily: 'var(--font-data)',
    fontSize: '0.6875rem',
    color: 'var(--color-on-surface-variant)',
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>
        <PageHeader
          tag="M&A Intelligence"
          title="M&A Dark Signals"
          subtitle="Private jet movements, satellite imagery, and pre-announcement deal signals"
        />

        {/* Metric cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '1.25rem',
          marginBottom: '2rem',
        }}>
          <MetricCard label="Jet Alerts"       value={loading ? '—' : jets.length}      accent="navy" />
          <MetricCard label="Satellite Flags"  value={loading ? '—' : satellite.length} accent="blue" />
          <MetricCard label="M&A Signals"      value={loading ? '—' : maSignals.length} accent="red" />
        </div>

        {/* Three-panel grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem' }}>
          {/* Private Jet Activity */}
          <Panel title="Private Jet Activity">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} width="100%" height={64} />)}
              </div>
            ) : jets.length === 0 ? (
              <EmptyState title="No jet alerts" message="No private jet activity detected" />
            ) : (
              jets.map((jet, i) => (
                <div key={i} style={cardStyle}>
                  <div style={labelStyle}>{jet.company || jet.tail_number || '—'}</div>
                  {jet.route && <div style={metaStyle}>Route: {jet.route}</div>}
                  {jet.date && <div style={metaStyle}>{jet.date}</div>}
                  {jet.urgency != null && <Tag label={`Confidence ${jet.urgency}%`} color={jet.urgency > 75 ? 'red' : 'gold'} />}
                </div>
              ))
            )}
          </Panel>

          {/* Satellite Flags */}
          <Panel title="Satellite Flags">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} width="100%" height={64} />)}
              </div>
            ) : satellite.length === 0 ? (
              <EmptyState title="No satellite flags" message="No satellite imagery changes detected" />
            ) : (
              satellite.map((s, i) => (
                <div key={i} style={cardStyle}>
                  <div style={labelStyle}>{s.company || s.site || '—'}</div>
                  {s.change_type && <div style={metaStyle}>{s.change_type}</div>}
                  {s.confidence != null && <Tag label={`${s.confidence}% conf`} color={s.confidence > 75 ? 'gold' : 'default'} />}
                </div>
              ))
            )}
          </Panel>

          {/* Pre-Announcement Signals */}
          <Panel title="Pre-Announcement Signals">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} width="100%" height={56} />)}
              </div>
            ) : maSignals.length === 0 ? (
              <EmptyState title="No M&A signals" message="No pre-announcement signals detected" />
            ) : (
              maSignals.map((sig, i) => (
                <div key={i} style={cardStyle}>
                  <div style={{
                    fontFamily: 'var(--font-data)',
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    color: 'var(--color-primary)',
                    lineHeight: 1.4,
                    marginBottom: '0.25rem',
                  }}>
                    {sig.headline || sig.text?.slice(0, 80) || 'Signal detected'}
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                    {sig.source && <span style={metaStyle}>{sig.source}</span>}
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
