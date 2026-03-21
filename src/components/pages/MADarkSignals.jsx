import React, { useState } from 'react'
import { maDarkSignals, supplyChainEvents, clients } from '../../data/mockData.js'
import { PageHeader, MetricCard, Tag, Spinner, AIBadge, ScoreBar } from '../ui/index.jsx'

export default function MADarkSignals() {
  const [selected, setSelected] = useState(maDarkSignals[0])
  const [pitch, setPitch] = useState('')
  const [loading, setLoading] = useState(false)

  const confidenceColor = (c) => c >= 85 ? 'var(--accent-red)' : c >= 70 ? '#f97316' : '#eab308'

  async function generatePitch() {
    setLoading(true)
    setPitch('')
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 500,
          messages: [{
            role: 'user',
            content: `You are an M&A lawyer's AI BD assistant. Write a concise outreach strategy for the following pre-deal intelligence.

Company: ${selected.company}
Predicted Deal Type: ${selected.predicted_type}
Estimated Deal Value: ${selected.est_deal_value}
Days to Likely Announcement: ${selected.days_to_announcement}
Confidence Score: ${selected.confidence}%
Current Relationship Warmth: ${selected.relationship_warmth}/100

Signals Detected:
${selected.signals.map(s => `- ${s}`).join('\n')}

Write a brief (under 150 words):
1. The specific legal services the firm should pitch (based on the deal type)
2. The ONE opening line that demonstrates intelligence without revealing surveillance
3. What to offer in the first conversation

Plain text. Be specific about which deal seats to target (buy-side, sell-side, target board, financing, regulatory clearance, etc.).`
          }]
        })
      })
      const data = await res.json()
      setPitch(data.content?.[0]?.text || 'Error.')
    } catch { setPitch('API error.') }
    setLoading(false)
  }

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="M&A Intelligence"
        title="M&A Dark Signal Detector"
        subtitle="Cross-references options anomalies, executive LinkedIn spikes, corporate jet tracking (ADS-B), and supply chain filings to detect deal formation 14–90 days before public announcement."
      />

      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Active Deal Signals" value={maDarkSignals.length} sub="companies in formation" accent="red" />
        <MetricCard label="Avg Confidence" value={`${Math.round(maDarkSignals.reduce((s, d) => s + d.confidence, 0) / maDarkSignals.length)}%`} sub="signal accuracy" accent="gold" />
        <MetricCard label="Est. Total Deal Value" value="$5.4B" sub="across active signals" accent="blue" />
        <MetricCard label="Avg Days to Announcement" value="32" sub="historical accuracy" accent="green" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 14, marginBottom: 14 }}>
        {/* Signal list */}
        <div className="panel" style={{ padding: 0 }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Active Formation Signals
          </div>
          {maDarkSignals.map((deal, i) => (
            <div
              key={i}
              onClick={() => { setSelected(deal); setPitch('') }}
              style={{
                padding: '14px 16px',
                borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
                background: selected?.company === deal.company ? 'var(--bg-elevated)' : 'transparent',
                borderLeft: selected?.company === deal.company ? '2px solid var(--accent-gold)' : '2px solid transparent',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <div style={{ fontWeight: 500, fontSize: 13 }}>{deal.company}</div>
                <div className="data-display" style={{ fontSize: 20, fontWeight: 700, color: confidenceColor(deal.confidence), lineHeight: 1 }}>{deal.confidence}%</div>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{deal.predicted_type}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <Tag color="gold">{deal.est_deal_value}</Tag>
                <Tag color="default">{deal.days_to_announcement} days</Tag>
              </div>
            </div>
          ))}
        </div>

        {/* Detail */}
        {selected && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                <div>
                  <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 22, letterSpacing: '-0.02em', marginBottom: 6 }}>{selected.company}</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Tag color="red">{selected.predicted_type}</Tag>
                    <Tag color="gold">{selected.est_deal_value}</Tag>
                    <Tag color="blue">{selected.days_to_announcement} days est.</Tag>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="data-display" style={{ fontSize: 44, fontWeight: 700, color: confidenceColor(selected.confidence), lineHeight: 1 }}>{selected.confidence}%</div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>CONFIDENCE</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8 }}>DARK SIGNALS DETECTED</div>
                  {selected.signals.map((s, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
                      <span style={{ color: 'var(--accent-gold)', fontSize: 10, marginTop: 3, flexShrink: 0 }}>◎</span>
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{s}</span>
                    </div>
                  ))}
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8 }}>RELATIONSHIP WARMTH</div>
                  <div style={{ marginBottom: 10 }}>
                    <ScoreBar score={selected.relationship_warmth} color={selected.relationship_warmth >= 50 ? 'green' : 'blue'} />
                  </div>
                  <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 3, padding: '10px 12px' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                      {selected.relationship_warmth < 30 ? '⚠ Cold Approach Required' : selected.relationship_warmth < 60 ? '→ Lukewarm Path Available' : '✓ Warm Relationship — Call Now'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {selected.relationship_warmth < 30
                        ? 'No current firm relationship. Identify second-degree connections before outreach.'
                        : 'Existing relationship exists. Move immediately — window is ' + selected.days_to_announcement + ' days.'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* AI pitch strategy */}
            <div className="panel" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>AI Deal Pitch Strategy</div>
                  <AIBadge />
                </div>
                <button className="oracle-btn oracle-btn-primary" onClick={generatePitch} disabled={loading}>
                  {loading ? '...' : 'Generate Strategy'}
                </button>
              </div>
              {loading ? <Spinner /> : pitch ? (
                <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', borderLeft: '2px solid var(--accent-gold)', paddingLeft: 14 }}>
                  {pitch}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Generate an AI strategy brief: which deal seats to pitch, the opening line that demonstrates intelligence, and first-call agenda.</div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Supply chain cascade */}
      <div className="panel" style={{ padding: '18px 20px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 16 }}>
          Supply Chain Litigation Cascade
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {supplyChainEvents.map((event, i) => (
            <div key={i} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 3, padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{event.source_company}</div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 6 }}>{event.event}</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Tag color="red">{event.urgency.toUpperCase()}</Tag>
                    <Tag color="gold">{event.legal_need}</Tag>
                    <Tag color="default">{event.date}</Tag>
                  </div>
                </div>
                <div style={{ textAlign: 'right', fontSize: 11, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>
                  Est. Exposure:<br />
                  <span style={{ color: 'var(--accent-red)', fontSize: 13, fontWeight: 600 }}>{event.est_exposure}</span>
                </div>
              </div>
              <div style={{ paddingTop: 10, borderTop: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>CASCADE TARGETS — YOUR CLIENTS AT RISK</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {event.cascade_targets.map(t => (
                    <div key={t} style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 3, padding: '6px 10px' }}>
                      <div style={{ fontSize: 12, fontWeight: 500 }}>{t}</div>
                      <div style={{ fontSize: 10, color: 'var(--accent-red)' }}>Immediate exposure</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
