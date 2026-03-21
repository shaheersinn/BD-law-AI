import React, { useState } from 'react'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts'
import { prospects } from '../../data/mockData.js'
import { PageHeader, MetricCard, RiskBadge, Tag, Spinner, AIBadge } from '../ui/index.jsx'

export default function PreCrimeAcquisition() {
  const [selected, setSelected] = useState(prospects[0])
  const [pitch, setPitch] = useState('')
  const [loading, setLoading] = useState(false)

  const urgencyColor = (s) => s >= 85 ? 'var(--accent-red)' : s >= 70 ? '#f97316' : s >= 55 ? '#eab308' : 'var(--accent-gold)'
  const warmthColor = { cold: 'var(--accent-blue)', warm: 'var(--accent-green)', lukewarm: '#eab308' }

  async function generatePitch() {
    setLoading(true)
    setPitch('')
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 800,
          messages: [{
            role: 'user',
            content: `You are a BigLaw business development AI generating an outreach strategy brief for a senior partner.

PROSPECT PROFILE:
Company: ${selected.name}
Industry: ${selected.industry}
Market Cap: ${selected.market_cap}
Legal Urgency Score: ${selected.urgency_score}/100
Predicted Legal Need: ${selected.predicted_need}
Relationship Warmth: ${selected.warmth}
Warm Path: ${selected.path}
Estimated Matter Value: ${selected.est_value}
Recommended Timeframe: ${selected.timeframe}

Detected Signals:
${selected.signals.map(s => `- ${s}`).join('\n')}

Write a concise outreach strategy brief (150 words max) covering:
1. The one key insight that creates urgency for calling now
2. The exact opening line the partner should use
3. What to offer in the first conversation

Be specific, direct, and practical. This is for a senior partner who will read it on their phone between meetings. Plain text only.`
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
        tag="Prospect Intelligence"
        title="Pre-Crime Client Acquisition Engine"
        subtitle="Monitors thousands of companies in real time. Scores them on a Legal Urgency Index based on behavioral patterns that precede legal events — not what's happened, but what's about to."
      />

      {/* Stats */}
      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Active Signals" value={prospects.length} sub="companies scored" accent="blue" />
        <MetricCard label="Urgency ≥ 80" value={prospects.filter(p => p.urgency_score >= 80).length} sub="call within 48h" accent="red" />
        <MetricCard label="Warm Paths" value={prospects.filter(p => p.warmth !== 'cold').length} sub="relationship access" accent="green" />
        <MetricCard label="Est. Pipeline" value={`$${(prospects.reduce((s, p) => s + parseFloat(p.est_value.replace(/[$KM]/g, '') * (p.est_value.includes('M') ? 1000 : 1)), 0) / 1000).toFixed(1)}M`} sub="if all converted" accent="gold" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 14 }}>
        {/* Prospect list */}
        <div className="panel" style={{ padding: 0, overflowY: 'auto' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Sorted by Legal Urgency Index
          </div>
          {[...prospects].sort((a, b) => b.urgency_score - a.urgency_score).map(p => (
            <div
              key={p.id}
              onClick={() => { setSelected(p); setPitch('') }}
              style={{
                padding: '14px 16px',
                borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
                background: selected?.id === p.id ? 'var(--bg-elevated)' : 'transparent',
                borderLeft: selected?.id === p.id ? '2px solid var(--accent-gold)' : '2px solid transparent',
                transition: 'all 0.1s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <div style={{ fontWeight: 500, fontSize: 13 }}>{p.name}</div>
                <div className="data-display" style={{ fontSize: 18, fontWeight: 700, color: urgencyColor(p.urgency_score), lineHeight: 1 }}>{p.urgency_score}</div>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{p.industry} · {p.market_cap}</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <Tag color={p.warmth === 'warm' ? 'green' : p.warmth === 'lukewarm' ? 'gold' : 'blue'}>{p.warmth.toUpperCase()}</Tag>
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{p.timeframe}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Detail */}
        {selected && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Header card */}
            <div className="panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                <div>
                  <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 22, letterSpacing: '-0.02em', marginBottom: 4 }}>{selected.name}</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <Tag color="default">{selected.industry}</Tag>
                    <Tag color="default">{selected.market_cap}</Tag>
                    {selected.ticker && <Tag color="blue">{selected.ticker}</Tag>}
                    <Tag color={selected.warmth === 'warm' ? 'green' : selected.warmth === 'lukewarm' ? 'gold' : 'blue'}>
                      {selected.warmth.toUpperCase()} RELATIONSHIP
                    </Tag>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="data-display" style={{ fontSize: 44, fontWeight: 700, color: urgencyColor(selected.urgency_score), lineHeight: 1 }}>{selected.urgency_score}</div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em' }}>LEGAL URGENCY INDEX</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                {[
                  { label: 'Predicted Need', val: selected.predicted_need },
                  { label: 'Est. Matter Value', val: selected.est_value },
                  { label: 'Timeframe', val: selected.timeframe },
                  { label: 'Warm Path', val: selected.path.split('→')[0]?.trim() || 'None' },
                ].map(({ label, val }) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 2 }}>{label}</div>
                    <div style={{ fontSize: 12, fontWeight: 500, lineHeight: 1.3 }}>{val}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {/* Signals */}
              <div className="panel" style={{ padding: '14px 16px' }}>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>
                  Detected Pre-Legal Signals
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {selected.signals.map((s, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '8px 10px', background: 'var(--bg-elevated)', borderRadius: 3, border: '1px solid var(--border)' }}>
                      <span style={{ color: 'var(--accent-gold)', fontSize: 10, marginTop: 3, flexShrink: 0 }}>◉</span>
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{s}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Warm path */}
              <div className="panel" style={{ padding: '14px 16px' }}>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>
                  Relationship Path
                </div>
                <div style={{ padding: '12px 14px', background: 'var(--bg-elevated)', border: `1px solid ${selected.warmth === 'cold' ? 'var(--border)' : 'rgba(34,197,94,0.3)'}`, borderRadius: 3, marginBottom: 12 }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>ENTRY PATH</div>
                  <div style={{ fontSize: 13, lineHeight: 1.5 }}>{selected.path}</div>
                </div>
                <div style={{ background: 'rgba(232,168,58,0.08)', border: '1px solid rgba(232,168,58,0.2)', borderRadius: 3, padding: '10px 12px' }}>
                  <div style={{ fontSize: 10, color: 'var(--accent-gold)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>RECOMMENDED ACTION</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Call within <strong style={{ color: 'var(--text-primary)' }}>{selected.timeframe}</strong>. Lead with the {selected.predicted_need} angle. Estimated first-year value: <strong style={{ color: 'var(--accent-gold)' }}>{selected.est_value}</strong>.
                  </div>
                </div>
              </div>
            </div>

            {/* AI outreach brief */}
            <div className="panel" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>AI Outreach Strategy</div>
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
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Generate an AI-powered outreach strategy brief for this prospect, including the recommended opening line and first-call agenda.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
