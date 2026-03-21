import React, { useState } from 'react'
import { competitorActivity, clients } from '../../data/mockData.js'
import { PageHeader, MetricCard, Tag, RiskBadge } from '../ui/index.jsx'

export default function CompetitiveIntel() {
  const [filter, setFilter] = useState('all')

  const categories = ['all', ...new Set(competitorActivity.map(a => a.category))]
  const filtered = filter === 'all' ? competitorActivity : competitorActivity.filter(a => a.category === filter)

  const threatColor = { critical: 'var(--accent-red)', high: '#f97316', medium: '#eab308', low: '#22c55e' }
  const threatBg = { critical: 'rgba(239,68,68,0.08)', high: 'rgba(249,115,22,0.06)', medium: 'rgba(234,179,8,0.06)', low: 'rgba(34,197,94,0.06)' }

  const conflictData = [
    { company: "Arctis Mining Corp", situation: "Being sued by Apple subsidiary", conflicted_firms: ["Osler (Apple retainer)", "Davies (Apple M&A)"], our_status: "CLEAR — No Apple relationship", advantage: "Only major firm eligible" },
    { company: "Pinnacle Health Systems", situation: "OSFI regulatory investigation", conflicted_firms: ["Stikeman (acts for regulator informally)"], our_status: "CLEAR", advantage: "2 of 4 competitors conflicted" },
  ]

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Competitive Intelligence"
        title="Competitor Radar"
        subtitle="Real-time monitoring of rival firm lateral hires, practice expansions, event presence, and conflict-of-interest arbitrage opportunities."
      />

      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Active Threats" value={competitorActivity.filter(a => a.threat_level === 'critical' || a.threat_level === 'high').length} sub="critical + high" accent="red" />
        <MetricCard label="Clients Targeted" value={new Set(competitorActivity.flatMap(a => a.affected_clients)).size} sub="by competitor activity" accent="gold" />
        <MetricCard label="Conflict Openings" value={conflictData.length} sub="competitors blocked" accent="green" />
        <MetricCard label="Firms Monitored" value={new Set(competitorActivity.map(a => a.firm)).size} sub="competitive radar" accent="blue" />
      </div>

      {/* Tab filter */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        {categories.map(cat => (
          <button key={cat} className={`tab-btn ${filter === cat ? 'active' : ''}`} onClick={() => setFilter(cat)}>
            {cat === 'all' ? 'All Signals' : cat}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
        {/* Threat feed */}
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
            Competitor Activity Feed
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {filtered.map((activity, i) => (
              <div key={i} style={{
                background: threatBg[activity.threat_level],
                border: `1px solid ${threatColor[activity.threat_level]}30`,
                borderLeft: `3px solid ${threatColor[activity.threat_level]}`,
                borderRadius: 3,
                padding: '14px 16px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{activity.firm.split(',')[0]}</div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Tag color="default">{activity.category}</Tag>
                    <span style={{ fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", color: threatColor[activity.threat_level], background: `${threatColor[activity.threat_level]}18`, border: `1px solid ${threatColor[activity.threat_level]}40`, padding: '2px 7px', borderRadius: 2 }}>
                      {activity.threat_level.toUpperCase()}
                    </span>
                  </div>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 8 }}>{activity.signal}</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>{activity.date}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>·</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Affects:</span>
                  {activity.affected_clients.map(c => (
                    <Tag key={c} color="gold">{c.split(' ')[0]}</Tag>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Conflict arbitrage */}
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
            Conflict-of-Interest Arbitrage
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {conflictData.map((item, i) => (
              <div key={i} className="panel" style={{ padding: '14px 16px' }}>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{item.company}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>{item.situation}</div>

                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>CONFLICTED RIVALS</div>
                  {item.conflicted_firms.map((f, j) => (
                    <div key={j} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ color: 'var(--accent-red)', fontSize: 10 }}>✕</span>
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{f}</span>
                    </div>
                  ))}
                </div>

                <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.25)', borderRadius: 3, padding: '10px 12px' }}>
                  <div style={{ fontSize: 10, color: 'var(--accent-green)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>OUR POSITION</div>
                  <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--accent-green)', marginBottom: 4 }}>{item.our_status}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{item.advantage}</div>
                </div>

                <button style={{ marginTop: 10, width: '100%', padding: '8px', background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 3, color: 'var(--accent-green)', fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", cursor: 'pointer', letterSpacing: '0.06em' }}>
                  DRAFT PITCH → AGGRESSIVE MOVE
                </button>
              </div>
            ))}
          </div>

          {/* Competitor heat ranking */}
          <div style={{ marginTop: 14 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
              Competitive Threat Ranking
            </div>
            <div className="panel" style={{ padding: 0 }}>
              {[
                { firm: "Davies Ward Phillips & Vineberg", signals: 2, threat: 92 },
                { firm: "Osler, Hoskin & Harcourt", signals: 2, threat: 78 },
                { firm: "Stikeman Elliott", signals: 1, threat: 61 },
                { firm: "Blake, Cassels & Graydon", signals: 1, threat: 44 },
                { firm: "McCarthy Tétrault", signals: 1, threat: 28 },
              ].map((f, i) => (
                <div key={i} className="data-row" style={{ gridTemplateColumns: '1fr 40px 50px' }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 500 }}>{f.firm.split(',')[0]}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{f.signals} active signal(s)</div>
                  </div>
                  <div className="data-display" style={{ fontSize: 14, fontWeight: 700, color: f.threat >= 75 ? 'var(--accent-red)' : f.threat >= 50 ? '#f97316' : 'var(--accent-gold)', textAlign: 'center' }}>{f.threat}</div>
                  <div style={{ display: 'flex', justifyContent: 'center' }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: f.threat >= 75 ? 'var(--accent-red)' : f.threat >= 50 ? '#f97316' : 'var(--accent-gold)' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
