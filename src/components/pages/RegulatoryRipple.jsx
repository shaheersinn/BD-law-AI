import React, { useState } from 'react'
import { regulatoryAlerts, clients } from '../../data/mockData.js'
import { PageHeader, RiskBadge, Tag, Spinner, AIBadge } from '../ui/index.jsx'

export default function RegulatoryRipple() {
  const [selected, setSelected] = useState(regulatoryAlerts[0])
  const [draftContent, setDraftContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('alerts')

  const affectedClientObjs = selected ? clients.filter(c => selected.affectedClients.includes(c.id)) : []

  async function generateClientAlert(client) {
    setLoading(true)
    setDraftContent('')
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: `You are a senior lawyer at a Canadian law firm drafting a proactive client alert. Write a concise, professional client alert for the following:

REGULATORY UPDATE:
Source: ${selected.source}
Title: ${selected.title}
Date: ${selected.date}
Summary: ${selected.summary}
Practice Area: ${selected.practiceArea}

CLIENT:
Name: ${client.name}
Industry: ${client.industry}
Active Matter: ${client.activeMatter}
Practice Groups: ${client.practiceGroups.join(', ')}

Write a short client alert (150-200 words) from the law firm's perspective. Include:
1. Brief description of the regulatory change
2. Why it specifically matters to this client
3. One concrete recommended action
4. Offer to discuss

Format: Professional email style, first paragraph addresses the client directly. No subject line needed. Do not use "[Law Firm Name]" — use "our firm". Use plain text, no markdown.`
          }]
        })
      })
      const data = await res.json()
      setDraftContent(data.content?.[0]?.text || 'Error generating draft.')
    } catch {
      setDraftContent('API connection error.')
    }
    setLoading(false)
  }

  const severityColor = { high: 'var(--accent-red)', medium: '#f97316', low: '#eab308' }

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Regulatory Intelligence"
        title="Regulatory Ripple Engine"
        subtitle="Monitors OSC, OSFI, CSA, SEC, and other regulatory feeds. Automatically maps new rules to affected clients and generates personalized alerts."
      />

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 14 }}>
        {/* Alert list */}
        <div>
          <div className="panel" style={{ padding: 0 }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              {regulatoryAlerts.length} Active Alerts
            </div>
            {regulatoryAlerts.map(r => (
              <div
                key={r.id}
                onClick={() => { setSelected(r); setDraftContent(''); setActiveTab('alerts') }}
                style={{
                  padding: '14px 16px',
                  borderBottom: '1px solid var(--border)',
                  cursor: 'pointer',
                  background: selected?.id === r.id ? 'var(--bg-elevated)' : 'transparent',
                  borderLeft: selected?.id === r.id ? `2px solid ${severityColor[r.severity]}` : '2px solid transparent',
                  transition: 'all 0.1s',
                }}
              >
                <div style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'center' }}>
                  <Tag color={r.severity === 'high' ? 'red' : r.severity === 'medium' ? 'gold' : 'default'}>{r.source}</Tag>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>{r.date}</span>
                </div>
                <div style={{ fontSize: 12, fontWeight: 500, lineHeight: 1.4, marginBottom: 4 }}>{r.practiceArea}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>{r.title}</div>
                <div style={{ marginTop: 6, display: 'flex', gap: 6, alignItems: 'center' }}>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{r.affectedClients.length} client(s) mapped</span>
                  {r.draftReady && <Tag color="green">Draft Ready</Tag>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Detail */}
        {selected && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Alert details */}
            <div className="panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <Tag color={selected.severity === 'high' ? 'red' : selected.severity === 'medium' ? 'gold' : 'default'}>
                  {selected.severity.toUpperCase()} SEVERITY
                </Tag>
                <Tag color="blue">{selected.source}</Tag>
                <Tag color="default">{selected.practiceArea}</Tag>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginLeft: 'auto', alignSelf: 'center' }}>{selected.date}</span>
              </div>
              <h2 style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 17, letterSpacing: '-0.01em', lineHeight: 1.3, marginBottom: 12 }}>{selected.title}</h2>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{selected.summary}</p>
            </div>

            {/* Affected clients */}
            <div className="panel" style={{ padding: '16px 20px' }}>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 14 }}>
                Affected Clients — {affectedClientObjs.length} Mapped
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {affectedClientObjs.map(c => (
                  <div key={c.id} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 3, padding: '12px 14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                      <div>
                        <div style={{ fontWeight: 500, fontSize: 14 }}>{c.name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.partnerOwner} · {c.industry} · {c.geoRegion}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <RiskBadge level={c.riskLevel} />
                        <button
                          className="oracle-btn oracle-btn-primary"
                          style={{ fontSize: 10, padding: '4px 12px' }}
                          onClick={() => { setActiveTab('draft'); generateClientAlert(c) }}
                        >
                          ◈ Draft Alert
                        </button>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {c.practiceGroups.map(pg => <Tag key={pg} color="blue">{pg}</Tag>)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Draft pane */}
            {(loading || draftContent) && (
              <div className="panel" style={{ padding: '16px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>AI-Generated Client Alert</div>
                  <AIBadge />
                </div>
                {loading ? <Spinner /> : (
                  <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 3, padding: '16px 18px' }}>
                    <pre style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0 }}>
                      {draftContent}
                    </pre>
                    <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
                      <button className="oracle-btn oracle-btn-primary" onClick={() => navigator.clipboard?.writeText(draftContent)}>Copy Draft</button>
                      <button className="oracle-btn oracle-btn-secondary">Send for Review</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
