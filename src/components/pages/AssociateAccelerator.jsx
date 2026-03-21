import React, { useState } from 'react'
import { associates, prospects } from '../../data/mockData.js'
import { PageHeader, MetricCard, Tag, Spinner, AIBadge, ScoreBar } from '../ui/index.jsx'

const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : `$${(n/1000).toFixed(0)}K`

export default function AssociateAccelerator() {
  const [selected, setSelected] = useState(associates[0])
  const [aiContent, setAiContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [contentType, setContentType] = useState('linkedin')

  async function generateContent() {
    setLoading(true)
    setAiContent('')
    const prompts = {
      linkedin: `Draft a LinkedIn post for a ${selected.year}th-year ${selected.practice} associate at a major Canadian law firm. Practice area: ${selected.practice}. The post should position them as a thought leader. Use one of these suggested topics from their content plan: "${selected.content_plan[0]}". Make it insightful, specific, and genuinely useful to GCs and in-house counsel. Under 200 words. No hashtag spam — maximum 3 relevant hashtags. Plain text.`,
      intro: `Write an email requesting an introduction. The associate ${selected.name} at a Canadian BigLaw firm wants to be introduced by a senior partner to a prospect. The associate has identified a warm path through a mutual connection. The email should be addressed to the senior partner, asking them to make the introduction. Practice: ${selected.practice}. Target: ${selected.opportunities[0]}. Keep it under 100 words. Professional but direct. Plain text.`,
      memo: `Draft a short "deal memo" that a ${selected.year}th-year ${selected.practice} associate could send to a prospect's in-house legal team demonstrating value. Topic should relate to: ${selected.content_plan[0]}. The memo should be 150 words max, demonstrate specific expertise, and include one concrete recommendation the in-house team can act on immediately. Format as a brief professional memo. Plain text only.`,
    }
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 600,
          messages: [{ role: 'user', content: prompts[contentType] }]
        })
      })
      const data = await res.json()
      setAiContent(data.content?.[0]?.text || 'Error.')
    } catch { setAiContent('API error.') }
    setLoading(false)
  }

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Associate Development"
        title="Associate BD Accelerator"
        subtitle="The most underserved market in BigLaw. 300 associates told to 'build their book' with zero tools. Every associate gets a personal BD dashboard, warm path mapper, content plan, and shadow origination tracker."
      />

      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Associates Tracked" value={associates.length} sub="enrolled in platform" accent="blue" />
        <MetricCard label="Total Pipeline" value={fmt(associates.reduce((s, a) => s + a.pipeline_value, 0))} sub="associate-generated" accent="gold" />
        <MetricCard label="Shadow Origination" value={fmt(associates.reduce((s, a) => s + a.shadow_origination, 0))} sub="attributed BD credit" accent="green" />
        <MetricCard label="High Performers" value={associates.filter(a => a.bd_activities >= 10).length} sub="≥10 BD activities" accent="purple" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 14 }}>
        {/* Associate list */}
        <div className="panel" style={{ padding: 0 }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Associates
          </div>
          {associates.map(a => (
            <div
              key={a.id}
              onClick={() => { setSelected(a); setAiContent('') }}
              style={{
                padding: '14px 16px',
                borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
                background: selected?.id === a.id ? 'var(--bg-elevated)' : 'transparent',
                borderLeft: selected?.id === a.id ? '2px solid var(--accent-gold)' : '2px solid transparent',
              }}
            >
              <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 2 }}>{a.name}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Year {a.year} · {a.practice}</div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>PIPELINE</div>
                  <div className="data-display" style={{ fontSize: 12, color: 'var(--accent-gold)' }}>{fmt(a.pipeline_value)}</div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>ACTIVITIES</div>
                  <div className="data-display" style={{ fontSize: 12, color: a.bd_activities >= 10 ? 'var(--accent-green)' : 'var(--text-secondary)' }}>{a.bd_activities}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Detail */}
        {selected && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
              <MetricCard label="BD Activities" value={selected.bd_activities} sub="this quarter" accent="blue" mono />
              <MetricCard label="Pipeline Value" value={fmt(selected.pipeline_value)} sub="estimated" accent="gold" />
              <MetricCard label="Shadow Origination" value={fmt(selected.shadow_origination)} sub="attributed credit" accent="green" />
              <MetricCard label="Seniority" value={`Year ${selected.year}`} sub={selected.practice} accent="default" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {/* Opportunities */}
              <div className="panel" style={{ padding: '14px 16px' }}>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>
                  Ranked Opportunities
                </div>
                {selected.opportunities.map((opp, i) => (
                  <div key={i} style={{ padding: '10px 12px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 3, marginBottom: 8 }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                      <div className="data-display" style={{ fontSize: 18, fontWeight: 700, color: 'var(--accent-gold)', flexShrink: 0, lineHeight: 1 }}>{i + 1}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{opp}</div>
                    </div>
                  </div>
                ))}

                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: 'var(--text-muted)', marginBottom: 8 }}>WARM PATH MAPPER</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    Partners who know your top targets:
                    {selected.opportunities.map((opp, i) => (
                      <div key={i} style={{ marginTop: 6, padding: '6px 8px', background: 'var(--bg-base)', borderRadius: 2, border: '1px solid var(--border)' }}>
                        <span style={{ color: 'var(--accent-gold)' }}>→</span> {opp.split('(')[1]?.replace(')', '') || 'Request intro via senior partner'}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Content plan */}
              <div className="panel" style={{ padding: '14px 16px' }}>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>
                  Personal Content Plan
                </div>
                {selected.content_plan.map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 10 }}>
                    <span style={{ color: 'var(--accent-blue)', fontSize: 10, marginTop: 3 }}>▷</span>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{item}</span>
                  </div>
                ))}

                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: 'var(--text-muted)', marginBottom: 6 }}>SHADOW ORIGINATION TRACKER</div>
                  <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 3, padding: '10px 12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Logged BD Activities</span>
                      <span className="data-display" style={{ fontSize: 13, color: 'var(--accent-gold)' }}>{selected.bd_activities}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Attributable Credit</span>
                      <span className="data-display" style={{ fontSize: 13, color: 'var(--accent-green)' }}>{fmt(selected.shadow_origination)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Content Studio */}
            <div className="panel" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>AI Content Studio</div>
                  <AIBadge />
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {[
                    { key: 'linkedin', label: 'LinkedIn Post' },
                    { key: 'intro', label: 'Intro Request' },
                    { key: 'memo', label: 'Value Memo' },
                  ].map(t => (
                    <button key={t.key} className={`tab-btn ${contentType === t.key ? 'active' : ''}`} onClick={() => { setContentType(t.key); setAiContent('') }}>
                      {t.label}
                    </button>
                  ))}
                  <button className="oracle-btn oracle-btn-primary" onClick={generateContent} disabled={loading}>
                    {loading ? '...' : 'Generate'}
                  </button>
                </div>
              </div>
              {loading ? <Spinner /> : aiContent ? (
                <div>
                  <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 3, padding: '14px 16px', marginBottom: 10 }}>
                    <pre style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0 }}>
                      {aiContent}
                    </pre>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="oracle-btn oracle-btn-primary" onClick={() => navigator.clipboard?.writeText(aiContent)}>Copy</button>
                    <button className="oracle-btn oracle-btn-secondary" onClick={generateContent}>Regenerate</button>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Select a content type and click Generate to create AI-powered BD content in {selected.name.split(' ')[0]}'s voice.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
