import React, { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line } from 'recharts'
import { pitchData, partners, clients } from '../../data/mockData.js'
import { PageHeader, MetricCard, Tag, Spinner, AIBadge } from '../ui/index.jsx'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', padding: '10px 14px', borderRadius: 3, fontSize: 11 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.fill || p.stroke, fontFamily: "'IBM Plex Mono', monospace" }}>
          {p.name}: {typeof p.value === 'number' && p.value <= 100 ? `${p.value}%` : p.value}
        </div>
      ))}
    </div>
  )
}

export default function PitchAutopsy() {
  const [activeTab, setActiveTab] = useState('autopsy')
  const [campaignTarget, setCampaignTarget] = useState(clients[0])
  const [campaignContent, setCampaignContent] = useState('')
  const [campaignLoading, setCampaignLoading] = useState(false)
  const [debriefInput, setDebriefInput] = useState('')
  const [debriefResult, setDebriefResult] = useState('')
  const [debriefLoading, setDebriefLoading] = useState(false)

  const winFactors = [
    { factor: "Partner presented first", wins: 78, losses: 44 },
    { factor: "Case studies included", wins: 71, losses: 31 },
    { factor: "Fixed fee offered", wins: 68, losses: 38 },
    { factor: "GC attended meeting", wins: 82, losses: 52 },
    { factor: "Follow-up within 48h", wins: 74, losses: 29 },
  ]

  async function generateCampaign() {
    setCampaignLoading(true)
    setCampaignContent('')
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          messages: [{
            role: 'user',
            content: `Design a multi-channel BD campaign for a BigLaw firm targeting this client.

Client: ${campaignTarget.name}
Industry: ${campaignTarget.industry}
Active Matter: ${campaignTarget.activeMatter}
Partner Owner: ${campaignTarget.partnerOwner}
Current Practice Groups: ${campaignTarget.practiceGroups.join(', ')}
Wallet Share: ${campaignTarget.walletShare}% (opportunity to grow)
Flight Risk: ${campaignTarget.churnScore}/100

Design a 4-step coordinated campaign sequence (over 6 weeks) that:
1. Step 1 (Week 1): Initial value-add touchpoint — what to send and why
2. Step 2 (Week 2-3): Follow-up engagement — specific offer or invitation
3. Step 3 (Week 4): Deeper engagement — cross-sell opportunity
4. Step 4 (Week 6): Conversion moment — what to propose

For each step, specify: channel (email/call/event/memo), sender (partner/associate), content angle, and expected client action.

Under 250 words total. Plain text with simple numbering. Be specific to this client's industry and situation.`
          }]
        })
      })
      const data = await res.json()
      setCampaignContent(data.content?.[0]?.text || 'Error.')
    } catch { setCampaignContent('API error.') }
    setCampaignLoading(false)
  }

  async function analyzeDebrief() {
    setDebriefLoading(true)
    setDebriefResult('')
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 600,
          messages: [{
            role: 'user',
            content: `You are a law firm BD analyst. Analyze this lost pitch debrief and extract actionable insights.

Debrief Information:
${debriefInput}

Provide:
1. Root cause of the loss (single most likely reason)
2. What the winning firm likely did differently
3. One specific improvement for the next pitch to this client
4. Whether to re-pitch in 6 months or walk away

Under 150 words. Direct and specific. No fluff. Plain text.`
          }]
        })
      })
      const data = await res.json()
      setDebriefResult(data.content?.[0]?.text || 'Error.')
    } catch { setDebriefResult('API error.') }
    setDebriefLoading(false)
  }

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="BD Analytics"
        title="Pitch Autopsy & BD Campaigns"
        subtitle="Statistical win/loss analysis across all pitches. AI debrief agent removes social friction from loss analysis. Multi-channel campaign orchestration for priority clients."
      />

      <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        {[
          { key: 'autopsy', label: 'Pitch Autopsy' },
          { key: 'campaigns', label: 'BD Campaign Engine' },
          { key: 'debrief', label: 'Loss Debrief Agent' },
        ].map(t => (
          <button key={t.key} className={`tab-btn ${activeTab === t.key ? 'active' : ''}`} onClick={() => setActiveTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'autopsy' && (
        <div>
          <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
            <MetricCard label="Overall Win Rate" value="63.6%" change={18.1} changeDir="up" sub="vs prior quarter" accent="green" />
            <MetricCard label="Total Pitches YTD" value="35" sub="across all practice groups" accent="blue" />
            <MetricCard label="Best Performing" value="Q1 2025" sub="72.7% win rate" accent="gold" />
            <MetricCard label="Average Deal Size Won" value="$420K" sub="first year revenue" accent="purple" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {/* Win rate trend */}
            <div className="panel" style={{ padding: '16px 18px' }}>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 14 }}>
                Win Rate Trend
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={[...pitchData].reverse()}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="win_rate" name="Win Rate" stroke="var(--accent-green)" strokeWidth={2} dot={{ fill: 'var(--accent-green)', r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Win/loss bar */}
            <div className="panel" style={{ padding: '16px 18px' }}>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 14 }}>
                Won vs Lost by Quarter
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={[...pitchData].reverse()}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 9, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="won" name="Won" fill="var(--accent-green)" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="lost" name="Lost" fill="rgba(239,68,68,0.5)" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Win factors */}
          <div className="panel" style={{ padding: '16px 18px', marginTop: 14 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 14 }}>
              Statistical Win Factors (Win % when factor present vs absent)
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {winFactors.map(f => (
                <div key={f.factor} style={{ display: 'grid', gridTemplateColumns: '220px 1fr 1fr', gap: 12, alignItems: 'center' }}>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{f.factor}</div>
                  <div>
                    <div style={{ fontSize: 9, color: 'var(--accent-green)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 3 }}>WITH: {f.wins}%</div>
                    <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${f.wins}%`, background: 'var(--accent-green)', borderRadius: 3 }} />
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 9, color: 'var(--accent-red)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 3 }}>WITHOUT: {f.losses}%</div>
                    <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${f.losses}%`, background: 'rgba(239,68,68,0.5)', borderRadius: 3 }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'campaigns' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 14 }}>
            <div className="panel" style={{ padding: 0 }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                Select Campaign Target
              </div>
              {clients.map(c => (
                <div
                  key={c.id}
                  onClick={() => { setCampaignTarget(c); setCampaignContent('') }}
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid var(--border)',
                    cursor: 'pointer',
                    background: campaignTarget?.id === c.id ? 'var(--bg-elevated)' : 'transparent',
                    borderLeft: campaignTarget?.id === c.id ? '2px solid var(--accent-gold)' : '2px solid transparent',
                  }}
                >
                  <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 2 }}>{c.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{c.industry} · {c.partnerOwner}</div>
                </div>
              ))}
            </div>
            <div className="panel" style={{ padding: '18px 20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>AI Campaign Orchestrator</div>
                    <AIBadge />
                  </div>
                  <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 18 }}>{campaignTarget?.name}</div>
                </div>
                <button className="oracle-btn oracle-btn-primary" onClick={generateCampaign} disabled={campaignLoading}>
                  {campaignLoading ? '...' : '▷ Generate Campaign'}
                </button>
              </div>
              {campaignLoading ? <Spinner /> : campaignContent ? (
                <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 3, padding: '16px 18px' }}>
                  <pre style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 13, lineHeight: 1.8, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0 }}>
                    {campaignContent}
                  </pre>
                  <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
                    <button className="oracle-btn oracle-btn-primary" onClick={() => navigator.clipboard?.writeText(campaignContent)}>Copy Campaign</button>
                    <button className="oracle-btn oracle-btn-secondary" onClick={generateCampaign}>Regenerate</button>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.7 }}>
                  Select a client and generate a 4-step, 6-week coordinated BD campaign. ORACLE considers the client's industry, flight risk, wallet share gap, and practice group mix to design the optimal sequence of touchpoints.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'debrief' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div className="panel" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>GC Debrief Agent</div>
              <AIBadge />
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.7, marginBottom: 16 }}>
              Paste any information you have from a lost pitch: GC's response, informal feedback, what you observed, who won and why. ORACLE extracts the root cause and builds improvement recommendations without the social awkwardness of asking directly.
            </div>
            <textarea
              className="oracle-input"
              rows={10}
              placeholder="Paste post-pitch notes, feedback received, observations about what went wrong, who the client chose and any context you have..."
              value={debriefInput}
              onChange={e => setDebriefInput(e.target.value)}
            />
            <button className="oracle-btn oracle-btn-primary" style={{ width: '100%', marginTop: 12 }} onClick={analyzeDebrief} disabled={debriefLoading || !debriefInput.trim()}>
              {debriefLoading ? 'Analyzing...' : 'Analyze Loss'}
            </button>
          </div>
          <div className="panel" style={{ padding: '18px 20px' }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 16 }}>
              Analysis Results
            </div>
            {debriefLoading ? <Spinner /> : debriefResult ? (
              <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-secondary)', borderLeft: '2px solid var(--accent-red)', paddingLeft: 14 }}>
                {debriefResult}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                Analysis will appear here. ORACLE identifies the root cause, what the winning firm likely did differently, and whether to re-pitch or walk away.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
