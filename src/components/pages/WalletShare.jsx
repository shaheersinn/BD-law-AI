import React, { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'
import { clients } from '../../data/mockData.js'
import { PageHeader, MetricCard, Tag, ScoreBar } from '../ui/index.jsx'

const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : `$${(n/1000).toFixed(0)}K`

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', padding: '10px 14px', borderRadius: 3, fontSize: 11 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 6, fontFamily: "'IBM Plex Mono', monospace" }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.fill, fontFamily: "'IBM Plex Mono', monospace" }}>{p.name}: {p.name.includes('Share') ? `${p.value}%` : fmt(p.value)}</div>
      ))}
    </div>
  )
}

export default function WalletShare() {
  const [selected, setSelected] = useState(clients[0])
  const [view, setView] = useState('chart')

  const sortedClients = [...clients].sort((a, b) => b.totalSpend - a.totalSpend)

  const barData = sortedClients.map(c => ({
    name: c.name.split(' ')[0],
    fullName: c.name,
    captured: c.walletShare,
    uncaptured: 100 - c.walletShare,
    totalSpend: c.totalSpend,
    firmRevenue: c.firmRevenue,
  }))

  const totalClientSpend = clients.reduce((s, c) => s + c.totalSpend, 0)
  const totalFirmRevenue = clients.reduce((s, c) => s + c.firmRevenue, 0)
  const avgWalletShare = Math.round(clients.reduce((s, c) => s + c.walletShare, 0) / clients.length)
  const uncapturedValue = totalClientSpend - totalFirmRevenue

  const whitespaceAreas = [
    { practice: "Employment Law", clients: clients.filter(c => !c.practiceGroups.includes('Employment')), est_spend: 3200000 },
    { practice: "Tax Advisory", clients: clients.filter(c => !c.practiceGroups.includes('Tax')), est_spend: 4800000 },
    { practice: "ESG & Sustainability", clients: clients.filter(c => !c.practiceGroups.includes('ESG')), est_spend: 1900000 },
    { practice: "Restructuring", clients: clients.filter(c => !c.practiceGroups.includes('Restructuring')), est_spend: 2700000 },
    { practice: "IP Licensing", clients: clients.filter(c => !c.practiceGroups.includes('IP')), est_spend: 2100000 },
  ]

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Revenue Intelligence"
        title="Wallet Share Engine"
        subtitle="Estimates total outside counsel spend for each client and computes your firm's capture rate. Surfaces whitespace — practice areas the client likely spends on where you have zero active matters."
      />

      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Total Client Legal Spend" value={fmt(totalClientSpend)} sub="est. across all clients" accent="blue" />
        <MetricCard label="Firm Revenue (Captured)" value={fmt(totalFirmRevenue)} sub="from same clients" accent="green" />
        <MetricCard label="Uncaptured Potential" value={fmt(uncapturedValue)} sub="legal spend at other firms" accent="red" />
        <MetricCard label="Average Wallet Share" value={`${avgWalletShare}%`} sub="of estimated client spend" accent="gold" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 14, marginBottom: 14 }}>
        {/* Wallet share chart */}
        <div className="panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Wallet Share by Client
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              {[
                { color: 'var(--accent-green)', label: 'Captured' },
                { color: 'var(--border-bright)', label: 'At Other Firms' },
              ].map(l => (
                <div key={l.label} style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                  <div style={{ width: 10, height: 10, background: l.color, borderRadius: 2 }} />
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>{l.label}</span>
                </div>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} onClick={(d) => d?.activePayload && setSelected(clients.find(c => c.name.startsWith(d.activeLabel)))}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="captured" name="Wallet Share" stackId="a" fill="var(--accent-green)" radius={[0, 0, 0, 0]} />
              <Bar dataKey="uncaptured" name="Uncaptured" stackId="a" fill="rgba(26,38,64,0.8)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Client detail */}
        {selected && (
          <div className="panel" style={{ padding: '16px 18px' }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 14 }}>
              Client Snapshot
            </div>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>{selected.name}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 14 }}>{selected.industry} · {selected.geoRegion}</div>

            <div style={{ background: `rgba(34,197,94,0.06)`, border: '1px solid rgba(34,197,94,0.2)', borderRadius: 3, padding: '12px 14px', marginBottom: 12 }}>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Total Legal Spend</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{fmt(selected.totalSpend)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>Captured by Firm</span>
                  <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>{fmt(selected.firmRevenue)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ color: 'var(--text-muted)' }}>At Other Firms</span>
                  <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>{fmt(selected.totalSpend - selected.firmRevenue)}</span>
                </div>
                <div style={{ paddingTop: 8, borderTop: '1px solid rgba(34,197,94,0.15)' }}>
                  <ScoreBar score={selected.walletShare} color="green" />
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 4 }}>Wallet Share: {selected.walletShare}%</div>
                </div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>CURRENT PRACTICE GROUPS</div>
              <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 12 }}>
                {selected.practiceGroups.map(pg => <Tag key={pg} color="blue">{pg}</Tag>)}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Whitespace map */}
      <div className="panel" style={{ padding: '18px 20px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 16 }}>
          Practice Area Whitespace Map — Where Your Clients Are Spending Elsewhere
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
          {whitespaceAreas.map(area => (
            <div key={area.practice} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 3, padding: '14px 14px' }}>
              <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>{area.practice}</div>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 18, fontWeight: 700, color: 'var(--accent-gold)', marginBottom: 6 }}>{fmt(area.est_spend)}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8 }}>est. annual spend</div>
              <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
                {area.clients.length} client(s) with zero matters
              </div>
              <div style={{ marginTop: 8 }}>
                {area.clients.slice(0, 2).map(c => (
                  <div key={c.id} style={{ fontSize: 10, color: 'var(--text-muted)', padding: '2px 0' }}>· {c.name.split(' ')[0]}</div>
                ))}
                {area.clients.length > 2 && <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>+ {area.clients.length - 2} more</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
