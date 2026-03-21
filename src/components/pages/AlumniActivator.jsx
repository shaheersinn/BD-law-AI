import React, { useState } from 'react'
import { alumni, clients } from '../../data/mockData.js'
import { PageHeader, MetricCard, Tag, Spinner, AIBadge } from '../ui/index.jsx'

export default function AlumniActivator() {
  const [selected, setSelected] = useState(alumni.find(a => a.trigger_active))
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const active = alumni.filter(a => a.trigger_active)
  const warmthColor = (w) => w >= 80 ? 'var(--accent-green)' : w >= 60 ? 'var(--accent-gold)' : w >= 40 ? '#60a5fa' : 'var(--text-muted)'

  async function generateMessage() {
    if (!selected) return
    setLoading(true)
    setMessage('')
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 600,
          messages: [{
            role: 'user',
            content: `You are drafting a personal outreach message from a law firm partner to a former associate who now works in-house. This should feel warm, personal, and NOT like a sales pitch. The goal is to reconnect and create an opportunity to discuss the triggered legal situation.

Former Associate: ${selected.name}
Current Role: ${selected.current_role} at ${selected.current_company}
Left firm in: ${selected.left_year}
Their mentor at firm: ${selected.mentor}
Warmth Score: ${selected.warmth}/100
Active Legal Trigger: ${selected.trigger}
Practice area the associate worked in: ${selected.practice_when_left}

Write a SHORT, conversational message (under 120 words) from ${selected.mentor} to ${selected.name.split(' ')[0]}. It should:
- Open with a genuine personal touch (not "Hope this finds you well")
- Reference something plausible about their current role or how long it's been
- Mention the relevant development naturally, not as a pitch
- End with a low-pressure ask (coffee, quick call)

Do NOT use any legal jargon. Do NOT explicitly say "I want your business." This should sound like a real message from a person who genuinely cares about this former colleague. Plain text only, no subject line needed.`
          }]
        })
      })
      const data = await res.json()
      setMessage(data.content?.[0]?.text || 'Error.')
    } catch { setMessage('API error.') }
    setLoading(false)
  }

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Network Intelligence"
        title="Alumni Sleeper Cell Activator"
        subtitle="Maps every former associate to their current in-house role. Detects legal triggers at their companies and auto-drafts warm, personal outreach — invisible pipeline activation through trusted relationships."
      />

      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Alumni Tracked" value={alumni.length} sub="former associates" accent="blue" />
        <MetricCard label="Active Triggers" value={active.length} sub="legal events at alumni companies" accent="red" />
        <MetricCard label="Average Warmth" value={`${Math.round(alumni.reduce((s, a) => s + a.warmth, 0) / alumni.length)}`} sub="relationship score" accent="gold" />
        <MetricCard label="Est. Pipeline Value" value="$1.2M" sub="from triggered alumni" accent="green" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 14 }}>
        {/* Alumni list */}
        <div className="panel" style={{ padding: 0, overflowY: 'auto' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Alumni Network
          </div>
          {alumni.map(a => (
            <div
              key={a.id}
              onClick={() => { setSelected(a); setMessage('') }}
              style={{
                padding: '14px 16px',
                borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
                background: selected?.id === a.id ? 'var(--bg-elevated)' : 'transparent',
                borderLeft: selected?.id === a.id ? '2px solid var(--accent-gold)' : a.trigger_active ? '2px solid var(--accent-red)' : '2px solid transparent',
                transition: 'all 0.1s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                <div style={{ fontWeight: 500, fontSize: 13 }}>{a.name}</div>
                <div className="data-display" style={{ fontSize: 13, fontWeight: 600, color: warmthColor(a.warmth) }}>{a.warmth}</div>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{a.current_role}</div>
              <div style={{ fontSize: 11, color: 'var(--accent-gold)', marginBottom: 6 }}>{a.current_company}</div>
              {a.trigger_active && (
                <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 2, padding: '4px 8px' }}>
                  <div style={{ fontSize: 9, color: 'var(--accent-red)', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em' }}>⚡ TRIGGER ACTIVE</div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Detail */}
        {selected && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div>
                  <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 20, letterSpacing: '-0.02em', marginBottom: 4 }}>{selected.name}</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>{selected.current_role} · {selected.current_company}</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Tag color="default">Left {selected.left_year}</Tag>
                    <Tag color="blue">{selected.practice_when_left}</Tag>
                    <Tag color="default">Mentored by {selected.mentor}</Tag>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="data-display" style={{ fontSize: 40, fontWeight: 700, color: warmthColor(selected.warmth), lineHeight: 1 }}>{selected.warmth}</div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>WARMTH SCORE</div>
                </div>
              </div>

              {/* Warmth breakdown */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                {[
                  { label: 'Time at Firm', val: `${selected.left_year - 2014}+ yrs` },
                  { label: 'Mentor Relationship', val: selected.mentor.split(' ')[0] },
                  { label: 'Years Since Left', val: `${2025 - selected.left_year} yrs` },
                  { label: 'Relationship Type', val: 'Mentee' },
                ].map(({ label, val }) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 2 }}>{label}</div>
                    <div style={{ fontSize: 12, fontWeight: 500 }}>{val}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Legal trigger */}
            {selected.trigger_active && (
              <div style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 4, padding: '16px 18px' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
                  <span style={{ fontSize: 16 }}>⚡</span>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--accent-red)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Legal Trigger Detected</div>
                </div>
                <div style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 500, marginBottom: 6 }}>{selected.trigger}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  ORACLE detected this signal at {selected.current_company}. {selected.mentor} should reach out within 48 hours via {selected.name.split(' ')[0]}'s personal connection.
                </div>
              </div>
            )}

            {/* AI message generator */}
            <div className="panel" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>AI Outreach Message</div>
                  <AIBadge />
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>From: {selected.mentor}</span>
                  <button className="oracle-btn oracle-btn-primary" onClick={generateMessage} disabled={loading || !selected.trigger_active}>
                    {loading ? '...' : 'Draft Message'}
                  </button>
                </div>
              </div>
              {!selected.trigger_active && !message && (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>No active trigger detected for this alumni. Message drafting requires an active legal trigger at their company.</div>
              )}
              {loading ? <Spinner /> : message ? (
                <div>
                  <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 3, padding: '16px 18px', marginBottom: 12 }}>
                    <pre style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 13, lineHeight: 1.8, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0 }}>
                      {message}
                    </pre>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="oracle-btn oracle-btn-primary" onClick={() => navigator.clipboard?.writeText(message)}>Copy Message</button>
                    <button className="oracle-btn oracle-btn-secondary">Open in Email</button>
                    <button className="oracle-btn oracle-btn-secondary" onClick={generateMessage}>Regenerate</button>
                  </div>
                </div>
              ) : selected.trigger_active ? (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Click "Draft Message" to generate a warm, personal outreach note from {selected.mentor} to {selected.name.split(' ')[0]}.</div>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
