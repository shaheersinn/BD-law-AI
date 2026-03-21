import React, { useState } from 'react'
import { prospects, clients } from '../../data/mockData.js'
import { PageHeader, MetricCard, Tag, Spinner, AIBadge, ScoreBar } from '../ui/index.jsx'

const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : `$${(n/1000).toFixed(0)}K`

const MANDATE_SIGNALS = [
  {
    company: "Arctis Mining Corp",
    layers: [
      { layer: "Reg/Compliance", label: "OSC sweep risk profile — sector enforcement wave forming", score: 91, source: "OSC filing pattern" },
      { layer: "Human Capital", label: "Senior compliance officer departed 45 days ago", score: 84, source: "LinkedIn" },
      { layer: "Financial/Structural", label: "Board special committee meeting — unscheduled", score: 78, source: "SEDAR filing" },
      { layer: "M&A Dark Signal", label: "Options volume 340% above 90-day average", score: 91, source: "Market data" },
      { layer: "Behavioral/Linguistic", label: "CEO earnings call language shifted to hedged phrasing", score: 66, source: "NLP analysis" },
    ],
    mandate_forming: true,
    confidence: 94,
    predicted_practice: "M&A Advisory + Securities",
    est_value: "$680K",
    convergence_window: "14 days",
  },
  {
    company: "Westbrook Digital Corp",
    layers: [
      { layer: "Dark Web / Security", label: "Credential breach detected on BreachForums at 03:14 AM", score: 99, source: "Breach monitor" },
      { layer: "Human Capital", label: "CISO role posted — internal security crisis", score: 88, source: "Job posting" },
      { layer: "Behavioral", label: "Privacy policy page deleted from website", score: 75, source: "Web monitor" },
      { layer: "Hiring Velocity", label: "IT security hiring +200% past 60 days", score: 82, source: "Job board" },
    ],
    mandate_forming: true,
    confidence: 88,
    predicted_practice: "Privacy / Cybersecurity / Regulatory",
    est_value: "$290K",
    convergence_window: "48 hours",
  },
  {
    company: "Vantage Rail Corp",
    layers: [
      { layer: "Regulatory", label: "Transport Canada audit notice filed", score: 72, source: "Public registry" },
      { layer: "Litigation", label: "2 new small claims against company this quarter", score: 55, source: "CanLII docket" },
      { layer: "Human Capital", label: "HR Director departed without announcement", score: 61, source: "LinkedIn" },
    ],
    mandate_forming: false,
    confidence: 62,
    predicted_practice: "Regulatory / Employment",
    est_value: "$180K",
    convergence_window: "4–6 weeks",
  },
]

export default function MandatePreFormation() {
  const [selected, setSelected] = useState(MANDATE_SIGNALS[0])
  const [synthesis, setSynthesis] = useState('')
  const [loading, setLoading] = useState(false)

  const layerColors = {
    "Reg/Compliance": 'var(--accent-red)',
    "Human Capital": '#f97316',
    "Financial/Structural": 'var(--accent-gold)',
    "M&A Dark Signal": '#a855f7',
    "Behavioral/Linguistic": '#06b6d4',
    "Behavioral": '#06b6d4',
    "Dark Web / Security": 'var(--accent-red)',
    "Hiring Velocity": '#22c55e',
    "Regulatory": 'var(--accent-red)',
    "Litigation": '#f97316',
  }

  async function generateSynthesis() {
    setLoading(true)
    setSynthesis('')
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 600,
          messages: [{
            role: 'user',
            content: `You are ORACLE's synthesis AI. A mandate is forming at ${selected.company}. Across multiple intelligence layers, the following signals have converged within a ${selected.convergence_window} window:

${selected.layers.map(l => `[${l.layer}] ${l.label} (Score: ${l.score}) — Source: ${l.source}`).join('\n')}

Confidence: ${selected.confidence}%
Predicted Practice Area: ${selected.predicted_practice}
Estimated Matter Value: ${selected.est_value}

Write the partner's tactical action brief (under 150 words):
1. The one sentence that explains why to call TODAY
2. Who at the firm should call (based on practice area)
3. The exact first sentence the partner should say when the GC answers
4. What to offer in the first 5 minutes

Plain text. This will be pushed to a partner's phone. Be direct, specific, and urgent where urgency is warranted.`
          }]
        })
      })
      const data = await res.json()
      setSynthesis(data.content?.[0]?.text || 'Error.')
    } catch { setSynthesis('API error.') }
    setLoading(false)
  }

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Predictive Intelligence"
        title="Mandate Pre-Formation Detector"
        subtitle="Detects the moment a legal mandate is forming inside a target company — before the GC has called any firm. Monitors convergence of signals across 6 intelligence layers simultaneously."
      />

      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Formation Alerts" value={MANDATE_SIGNALS.filter(m => m.mandate_forming).length} sub="high-confidence mandates" accent="red" />
        <MetricCard label="Signals Converging" value={MANDATE_SIGNALS.length} sub="companies monitored" accent="gold" />
        <MetricCard label="Est. Pipeline" value={fmt(MANDATE_SIGNALS.reduce((s, m) => s + parseFloat(m.est_value.replace(/[$KM]/g, '') * (m.est_value.includes('M') ? 1000 : 1)), 0) * 1000)} sub="if all engaged" accent="green" />
        <MetricCard label="Avg Confidence" value={`${Math.round(MANDATE_SIGNALS.reduce((s, m) => s + m.confidence, 0) / MANDATE_SIGNALS.length)}%`} sub="signal accuracy" accent="blue" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 14 }}>
        {/* Company list */}
        <div className="panel" style={{ padding: 0 }}>
          {MANDATE_SIGNALS.map((m, i) => (
            <div
              key={i}
              onClick={() => { setSelected(m); setSynthesis('') }}
              style={{
                padding: '14px 16px',
                borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
                background: selected?.company === m.company ? 'var(--bg-elevated)' : 'transparent',
                borderLeft: selected?.company === m.company ? '2px solid var(--accent-gold)' : m.mandate_forming ? '2px solid var(--accent-red)' : '2px solid transparent',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <div style={{ fontWeight: 500, fontSize: 13 }}>{m.company}</div>
                <div className="data-display" style={{ fontSize: 20, fontWeight: 700, color: m.confidence >= 85 ? 'var(--accent-red)' : m.confidence >= 70 ? '#f97316' : 'var(--accent-gold)', lineHeight: 1 }}>{m.confidence}%</div>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{m.predicted_practice}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {m.mandate_forming && <Tag color="red">⚡ FORMING</Tag>}
                <Tag color="default">{m.convergence_window}</Tag>
              </div>
            </div>
          ))}
        </div>

        {/* Detail */}
        {selected && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div>
                  <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 22, letterSpacing: '-0.02em', marginBottom: 6 }}>{selected.company}</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {selected.mandate_forming && <Tag color="red">⚡ MANDATE FORMING</Tag>}
                    <Tag color="gold">{selected.predicted_practice}</Tag>
                    <Tag color="blue">{selected.est_value}</Tag>
                    <Tag color="default">Window: {selected.convergence_window}</Tag>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="data-display" style={{ fontSize: 44, fontWeight: 700, color: selected.confidence >= 85 ? 'var(--accent-red)' : '#f97316', lineHeight: 1 }}>{selected.confidence}%</div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>FORMATION CONFIDENCE</div>
                </div>
              </div>

              {/* Convergence layer visualization */}
              <div style={{ paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: 12 }}>SIGNAL CONVERGENCE — {selected.layers.length} LAYERS</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {selected.layers.map((layer, i) => (
                    <div key={i} style={{ display: 'grid', gridTemplateColumns: '160px 1fr 50px', gap: 10, alignItems: 'center', padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 3, borderLeft: `3px solid ${layerColors[layer.layer] || 'var(--accent-gold)'}` }}>
                      <div style={{ fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", color: layerColors[layer.layer] || 'var(--accent-gold)' }}>{layer.layer}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.3 }}>{layer.label}</div>
                      <div className="data-display" style={{ fontSize: 14, fontWeight: 700, color: layer.score >= 80 ? 'var(--accent-red)' : 'var(--accent-gold)', textAlign: 'right' }}>{layer.score}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Synthesis */}
            <div className="panel" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Synthesis Agent — Tactical Brief</div>
                  <AIBadge />
                </div>
                <button className="oracle-btn oracle-btn-primary" onClick={generateSynthesis} disabled={loading}>
                  {loading ? '...' : 'Generate Brief'}
                </button>
              </div>
              {loading ? <Spinner /> : synthesis ? (
                <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', borderLeft: '2px solid var(--accent-gold)', paddingLeft: 14 }}>
                  {synthesis}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  The Synthesis Agent reasons across all converged signals and generates a single tactical action brief — including who should call, what to say, and what to offer in the first 5 minutes.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
