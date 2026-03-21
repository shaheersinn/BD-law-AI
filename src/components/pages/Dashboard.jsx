import React, { useState, useEffect } from 'react'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { kpis, clients, bdPerformanceData, prospects, regulatoryAlerts, competitorActivity, FIRM_NAME } from '../../data/mockData.js'
import { MetricCard, RiskBadge, ScoreBar, Tag } from '../ui/index.jsx'

const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : `$${(n/1000).toFixed(0)}K`

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', padding: '10px 14px', borderRadius: 3, fontSize: 12 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 6, fontFamily: "'IBM Plex Mono', monospace" }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color, fontFamily: "'IBM Plex Mono', monospace" }}>
          {p.name}: {typeof p.value === 'number' && p.value > 10000 ? fmt(p.value) : p.value}
        </div>
      ))}
    </div>
  )
}

export default function Dashboard({ setPage }) {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const atRiskClients = clients.filter(c => c.churnScore >= 60)
  const topProspects = prospects.slice(0, 4)

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: 'var(--accent-gold)', letterSpacing: '0.12em', marginBottom: 4 }}>◈ ORACLE INTELLIGENCE OS · COMMAND CENTER</div>
          <h1 style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 24, letterSpacing: '-0.03em' }}>{FIRM_NAME}</h1>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="data-display" style={{ fontSize: 18, color: 'var(--accent-gold)', letterSpacing: '0.04em' }}>
            {time.toLocaleTimeString('en-CA', { hour12: false })}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>
            {time.toLocaleDateString('en-CA', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}
          </div>
        </div>
      </div>

      {/* KPI Row */}
      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Active Pipeline" value={fmt(kpis.total_pipeline)} change={kpis.pipeline_change} changeDir="up" sub="vs last month" accent="gold" />
        <MetricCard label="Clients at Risk" value={kpis.clients_at_risk} change={null} sub="flight-risk signals" accent="red" />
        <MetricCard label="Active Prospects" value={kpis.active_prospects} change={null} sub="pre-crime signals" accent="blue" />
        <MetricCard label="Pitch Win Rate" value={`${kpis.win_rate}%`} change={kpis.win_rate_change} changeDir="up" sub="vs prior quarter" accent="green" />
        <MetricCard label="Avg Wallet Share" value={`${kpis.avg_wallet_share}%`} change={kpis.wallet_share_change} changeDir="up" sub="est. client spend" accent="purple" />
      </div>

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
        {/* Pipeline chart */}
        <div className="panel" style={{ padding: '16px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>BD Pipeline Activity</div>
            <Tag color="gold">Last 6 Months</Tag>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={bdPerformanceData}>
              <defs>
                <linearGradient id="pipelineGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-gold)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--accent-gold)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="closedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} tickFormatter={v => `$${v/1000000}M`} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="pipeline" name="Pipeline" stroke="var(--accent-gold)" fill="url(#pipelineGrad)" strokeWidth={1.5} dot={false} />
              <Area type="monotone" dataKey="closed" name="Closed" stroke="var(--accent-blue)" fill="url(#closedGrad)" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Clients at risk */}
        <div className="panel" style={{ padding: '16px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Clients at Flight Risk</div>
            <button onClick={() => setPage('churn')} style={{ fontSize: 10, color: 'var(--accent-gold)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em' }}>VIEW ALL →</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {atRiskClients.map(c => (
              <div key={c.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{c.name}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{c.partnerOwner} · {c.industry}</div>
                  </div>
                  <RiskBadge level={c.riskLevel} />
                </div>
                <ScoreBar score={c.churnScore} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
        {/* Top prospects */}
        <div className="panel" style={{ padding: '16px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Top Prospect Signals</div>
            <button onClick={() => setPage('precrime')} style={{ fontSize: 10, color: 'var(--accent-gold)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace" }}>VIEW ALL →</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {topProspects.map(p => (
              <div key={p.id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <div className="data-display" style={{ fontSize: 16, fontWeight: 700, color: p.urgency_score >= 85 ? 'var(--accent-red)' : p.urgency_score >= 70 ? '#f97316' : 'var(--accent-gold)', width: 30, flexShrink: 0 }}>{p.urgency_score}</div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{p.predicted_need}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Regulatory alerts */}
        <div className="panel" style={{ padding: '16px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Regulatory Alerts</div>
            <button onClick={() => setPage('regulatory')} style={{ fontSize: 10, color: 'var(--accent-gold)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace" }}>VIEW ALL →</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {regulatoryAlerts.slice(0, 4).map(r => (
              <div key={r.id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span className="signal-dot" style={{ marginTop: 5, flexShrink: 0, background: r.severity === 'high' ? 'var(--accent-red)' : r.severity === 'medium' ? '#f97316' : '#eab308' }}></span>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 500, lineHeight: 1.3 }}>{r.source} — {r.practiceArea}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{r.affectedClients.length} client(s) affected</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Competitor radar */}
        <div className="panel" style={{ padding: '16px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Competitor Threats</div>
            <button onClick={() => setPage('competitive')} style={{ fontSize: 10, color: 'var(--accent-gold)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace" }}>VIEW ALL →</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {competitorActivity.slice(0, 4).map((c, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span className="signal-dot" style={{ marginTop: 5, flexShrink: 0, background: c.threat_level === 'critical' ? 'var(--accent-red)' : c.threat_level === 'high' ? '#f97316' : 'var(--accent-gold)' }}></span>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 500, lineHeight: 1.3 }}>{c.firm.split(',')[0]}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 160 }}>{c.signal.substring(0, 50)}...</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
