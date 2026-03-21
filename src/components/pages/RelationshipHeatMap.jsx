import React, { useState } from 'react'
import { clients, partners } from '../../data/mockData.js'
import { PageHeader, MetricCard, Tag } from '../ui/index.jsx'

const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : `$${(n/1000).toFixed(0)}K`

export default function RelationshipHeatMap() {
  const [hoveredCell, setHoveredCell] = useState(null)
  const [selectedPartner, setSelectedPartner] = useState(null)

  // Build actual relationship matrix
  const matrix = partners.map(partner => {
    return {
      partner,
      cells: clients.map(client => {
        const owns = partner.clients.includes(client.id)
        const score = owns
          ? Math.min(100, 55 + Math.floor(Math.random() * 45))
          : Math.random() > 0.65 ? Math.floor(Math.random() * 35) + 5 : 0
        return { client, score, owns }
      })
    }
  })

  const getCellColor = (score) => {
    if (score === 0) return 'var(--bg-base)'
    if (score >= 75) return `rgba(34, 197, 94, ${0.15 + (score - 75) / 100})`
    if (score >= 50) return `rgba(232, 168, 58, ${0.1 + (score - 50) / 200})`
    if (score >= 25) return `rgba(59, 130, 246, ${0.08 + score / 400})`
    return `rgba(59, 130, 246, 0.06)`
  }

  const getCellBorder = (score, owns) => {
    if (owns) return '1px solid rgba(34,197,94,0.4)'
    if (score >= 25) return '1px solid var(--border)'
    return '1px solid var(--border)'
  }

  const whitespace = []
  matrix.forEach(row => {
    row.cells.forEach(cell => {
      if (!cell.owns && cell.score === 0) {
        whitespace.push({ partner: row.partner.name, client: cell.client.name, industry: cell.client.industry })
      }
    })
  })

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Relationship Intelligence"
        title="Relationship Heat Map"
        subtitle="Every partner–client relationship scored by recency, depth, and cross-practice penetration. Identify whitespace and multi-practice opportunities at a glance."
      />

      <div className="stagger" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
        <MetricCard label="Total Relationships" value={matrix.reduce((s, r) => s + r.cells.filter(c => c.score > 0).length, 0)} sub="partner-client pairs" accent="blue" />
        <MetricCard label="Primary (Owned)" value={matrix.reduce((s, r) => s + r.cells.filter(c => c.owns).length, 0)} sub="direct ownership" accent="green" />
        <MetricCard label="Whitespace Pairs" value={whitespace.length} sub="zero relationship" accent="red" />
        <MetricCard label="Cross-sell Opportunities" value={clients.filter(c => c.practiceGroups.length < 3).length} sub="single practice clients" accent="gold" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 14 }}>
        {/* Heat map */}
        <div className="panel" style={{ padding: '18px 20px', overflowX: 'auto' }}>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 16 }}>
            Partner × Client Relationship Matrix
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 14 }}>
            {[
              { color: 'rgba(34,197,94,0.4)', label: 'Primary (75–100)' },
              { color: 'rgba(232,168,58,0.3)', label: 'Active (50–74)' },
              { color: 'rgba(59,130,246,0.2)', label: 'Aware (1–49)' },
              { color: 'var(--bg-base)', label: 'No Relationship' },
            ].map(l => (
              <div key={l.label} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <div style={{ width: 12, height: 12, background: l.color, border: '1px solid var(--border)', borderRadius: 2 }} />
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace" }}>{l.label}</span>
              </div>
            ))}
          </div>

          {/* Grid */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'separate', borderSpacing: 3, minWidth: 600 }}>
              <thead>
                <tr>
                  <th style={{ width: 110, padding: '4px 8px', textAlign: 'left', fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace', fontWeight: 'normal'" }}>PARTNER ↓ CLIENT →</th>
                  {clients.map(c => (
                    <th key={c.id} style={{ padding: '4px 6px', textAlign: 'center', fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", fontWeight: 'normal', minWidth: 80 }}>
                      <div style={{ writing: 'vertical', maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 9 }}>
                        {c.name.split(' ')[0]}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.map(row => (
                  <tr key={row.partner.id}>
                    <td style={{ padding: '3px 8px', fontSize: 11, fontWeight: 500, whiteSpace: 'nowrap', color: selectedPartner?.id === row.partner.id ? 'var(--accent-gold)' : 'var(--text-primary)' }}>
                      <div
                        style={{ cursor: 'pointer' }}
                        onClick={() => setSelectedPartner(selectedPartner?.id === row.partner.id ? null : row.partner)}
                      >
                        {row.partner.name.split(' ')[0]} {row.partner.name.split(' ')[1]?.[0]}.
                      </div>
                    </td>
                    {row.cells.map(cell => (
                      <td
                        key={cell.client.id}
                        onMouseEnter={() => setHoveredCell({ partner: row.partner, client: cell.client, score: cell.score, owns: cell.owns })}
                        onMouseLeave={() => setHoveredCell(null)}
                        style={{ padding: 3, cursor: 'pointer' }}
                      >
                        <div style={{
                          width: 80, height: 36,
                          background: getCellColor(cell.score),
                          border: getCellBorder(cell.score, cell.owns),
                          borderRadius: 3,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 11, fontFamily: "'IBM Plex Mono', monospace",
                          color: cell.score === 0 ? 'var(--text-muted)' : cell.score >= 75 ? 'var(--accent-green)' : cell.score >= 50 ? 'var(--accent-gold)' : '#60a5fa',
                          transition: 'all 0.1s',
                          fontWeight: cell.owns ? 600 : 400,
                        }}>
                          {cell.score === 0 ? '—' : cell.score}
                          {cell.owns && <span style={{ fontSize: 7, marginLeft: 2 }}>●</span>}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Side panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Hover tooltip */}
          <div className="panel" style={{ padding: '14px 16px', minHeight: 100 }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
              Cell Inspector
            </div>
            {hoveredCell ? (
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{hoveredCell.client.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>{hoveredCell.partner.name}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Relationship Score</span>
                    <span className="data-display" style={{ fontSize: 14, color: hoveredCell.score >= 75 ? 'var(--accent-green)' : 'var(--accent-gold)' }}>{hoveredCell.score || '—'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Ownership</span>
                    <Tag color={hoveredCell.owns ? 'green' : 'default'}>{hoveredCell.owns ? 'Primary' : 'Secondary'}</Tag>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Client Revenue</span>
                    <span className="data-display" style={{ fontSize: 11 }}>{fmt(hoveredCell.client.firmRevenue)}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Hover over a cell to inspect the relationship</div>
            )}
          </div>

          {/* Whitespace opportunities */}
          <div className="panel" style={{ padding: '14px 16px', flex: 1, overflowY: 'auto' }}>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>
              Whitespace Opportunities
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {whitespace.slice(0, 8).map((w, i) => (
                <div key={i} style={{ padding: '8px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 3 }}>
                  <div style={{ fontSize: 11, fontWeight: 500 }}>{w.client.split(' ').slice(0,2).join(' ')}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{w.partner.split(' ')[0]} has zero relationship</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
