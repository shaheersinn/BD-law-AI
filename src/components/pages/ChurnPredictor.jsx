import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts'
import { clients, churnSignals } from '../../data/mockData.js'
import { PageHeader, MetricCard, RiskBadge, ScoreBar, Section, Tag, Spinner, AIBadge } from '../ui/index.jsx'

const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : `$${(n/1000).toFixed(0)}K`

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', padding: '8px 12px', borderRadius: 3, fontSize: 11 }}>
      <div style={{ color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>Month {label}</div>
      <div style={{ color: 'var(--accent-red)', fontFamily: "'IBM Plex Mono', monospace" }}>Flight Risk: {payload[0]?.value}%</div>
    </div>
  )
}

export default function ChurnPredictor() {
  const [selected, setSelected] = useState(clients.find(c => c.churnScore >= 60) || clients[0])
  const [aiInsight, setAiInsight] = useState('')
  const [loading, setLoading] = useState(false)

  const signals = churnSignals.find(s => s.clientId === selected.id)
  const chartData = (signals?.trend || [20, 25, 30, 35]).map((v, i) => ({ month: i + 1, risk: v }))

  const atRisk = clients.filter(c => c.churnScore >= 60)
  const watching = clients.filter(c => c.churnScore >= 30 && c.churnScore < 60)
  const stable = clients.filter(c => c.churnScore < 30)

  async function generateInsight() {
    setLoading(true)
    setAiInsight('')
    const signalList = signals?.signals?.join('\n- ') || 'No signals available'
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: `You are a BigLaw business development AI. Analyze this client churn risk situation and provide a concise, actionable brief for the managing partner.

Client: ${selected.name}
Industry: ${selected.industry}
Flight Risk Score: ${selected.churnScore}/100 (${selected.riskLevel.toUpperCase()} RISK)
Partner Owner: ${selected.partnerOwner}
Annual Firm Revenue: ${fmt(selected.firmRevenue)}
Last Contact: ${selected.lastContact} days ago
Active Matter: ${selected.activeMatter}

Risk Signals Detected:
- ${signalList}

Provide:
1. Root cause analysis (2-3 sentences, direct and specific)
2. Recommended immediate action (1-2 specific steps, with timing)
3. One non-obvious insight about this situation

Format as plain text, no headers, keep it under 200 words. Be direct — this is going to a senior partner who has 2 minutes to read it.`
          }]
        })
      })
      const data = await res.json()
      setAiInsight(data.content?.[0]?.text || 'Unable to generate insight.')
    } catch (e) {
      setAiInsight('API error. Check your connection or API key configuration.')
    }
    setLoading(false)
  }

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Client Intelligence"
        title="Silent Client Churn Predictor"
        subtitle="Supervised ML scoring detects departure signals in billing rhythm, matter cadence, and communication patterns months before a client leaves."
      />

      {/* KPIs */}
      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Critical Risk Clients" value={atRisk.length} sub="≥60 flight risk score" accent="red" />
        <MetricCard label="Watching" value={watching.length} sub="30–59 risk score" accent="gold" />
        <MetricCard label="Stable Relationships" value={stable.length} sub="<30 risk score" accent="green" />
        <MetricCard label="Revenue at Risk" value={fmt(atRisk.reduce((s, c) => s + c.firmRevenue, 0))} sub="from flagged clients" accent="red" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 14 }}>
        {/* Client list */}
        <div className="panel" style={{ padding: 0, overflowY: 'auto' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            All Clients — Risk Ranked
          </div>
          {[...clients].sort((a, b) => b.churnScore - a.churnScore).map(c => (
            <div
              key={c.id}
              onClick={() => setSelected(c)}
              style={{
                padding: '12px 16px',
                borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
                background: selected.id === c.id ? 'var(--bg-elevated)' : 'transparent',
                borderLeft: selected.id === c.id ? '2px solid var(--accent-gold)' : '2px solid transparent',
                transition: 'all 0.1s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <div style={{ fontWeight: 500, fontSize: 13, lineHeight: 1.2 }}>{c.name}</div>
                <RiskBadge level={c.riskLevel} />
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 6 }}>{c.partnerOwner} · {fmt(c.firmRevenue)}/yr</div>
              <ScoreBar score={c.churnScore} />
            </div>
          ))}
        </div>

        {/* Detail panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Header */}
          <div className="panel" style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 20, letterSpacing: '-0.02em', marginBottom: 4 }}>{selected.name}</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <Tag color="default">{selected.industry}</Tag>
                  <Tag color="default">{selected.type}</Tag>
                  <Tag color="default">{selected.geoRegion}</Tag>
                  {selected.practiceGroups.map(pg => <Tag key={pg} color="blue">{pg}</Tag>)}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div className="data-display" style={{ fontSize: 36, fontWeight: 700, color: selected.churnScore >= 75 ? 'var(--accent-red)' : selected.churnScore >= 50 ? '#f97316' : 'var(--accent-gold)', lineHeight: 1 }}>{selected.churnScore}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>FLIGHT RISK SCORE</div>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
              {[
                { label: 'Active Matter', val: selected.activeMatter },
                { label: 'Last Contact', val: `${selected.lastContact}d ago` },
                { label: 'Annual Revenue', val: fmt(selected.firmRevenue) },
                { label: 'Wallet Share', val: `${selected.walletShare}%` },
              ].map(({ label, val }) => (
                <div key={label}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 2 }}>{label}</div>
                  <div style={{ fontSize: 13, fontWeight: 500, fontFamily: "'IBM Plex Mono', monospace" }}>{val}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {/* Risk trajectory chart */}
            <div className="panel" style={{ padding: '14px 16px' }}>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>Risk Score Trajectory</div>
              <ResponsiveContainer width="100%" height={130}>
                <LineChart data={chartData}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <ReferenceLine y={75} stroke="rgba(239,68,68,0.3)" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="risk" stroke="var(--accent-red)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Detected signals */}
            <div className="panel" style={{ padding: '14px 16px' }}>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>Detected Risk Signals</div>
              {signals?.signals?.length ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {signals.signals.map((s, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                      <span style={{ color: 'var(--accent-red)', fontSize: 10, marginTop: 2, flexShrink: 0 }}>▸</span>
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{s}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No anomalies detected for this client.</div>
              )}
            </div>
          </div>

          {/* AI Insight */}
          <div className="panel" style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>AI Partner Brief</div>
                <AIBadge />
              </div>
              <button className="oracle-btn oracle-btn-primary" onClick={generateInsight} disabled={loading}>
                {loading ? '...' : 'Generate Brief'}
              </button>
            </div>
            {loading ? (
              <Spinner />
            ) : aiInsight ? (
              <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', borderLeft: '2px solid var(--accent-gold)', paddingLeft: 14 }}>
                {aiInsight}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                Click "Generate Brief" to get an AI-powered root cause analysis and recommended actions for this client relationship.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
