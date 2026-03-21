import React from 'react'
import { FIRM_NAME } from '../../data/mockData.js'

const NAV_SECTIONS = [
  {
    label: "INTELLIGENCE",
    items: [
      { id: "dashboard", icon: "◈", label: "Command Center" },
      { id: "churn", icon: "⚠", label: "Client Churn Predictor" },
      { id: "regulatory", icon: "⚡", label: "Regulatory Ripple" },
      { id: "heatmap", icon: "◫", label: "Relationship Heat Map" },
    ]
  },
  {
    label: "ACQUISITION",
    items: [
      { id: "precrime", icon: "◉", label: "Pre-Crime Acquisition" },
      { id: "mandates", icon: "↯", label: "Mandate Pre-Formation" },
      { id: "maDark", icon: "◎", label: "M&A Dark Signals" },
      { id: "supplychain", icon: "⛓", label: "Supply Chain Cascade" },
    ]
  },
  {
    label: "INTELLIGENCE OPS",
    items: [
      { id: "competitive", icon: "⊗", label: "Competitor Radar" },
      { id: "wallet", icon: "◑", label: "Wallet Share Engine" },
      { id: "alumni", icon: "◇", label: "Alumni Activator" },
      { id: "gcprofiler", icon: "◈", label: "GC Profiler" },
    ]
  },
  {
    label: "DEVELOPMENT",
    items: [
      { id: "associate", icon: "△", label: "Associate Accelerator" },
      { id: "pitchaudit", icon: "⊕", label: "Pitch Autopsy" },
      { id: "campaigns", icon: "▷", label: "BD Campaigns" },
    ]
  },
]

export default function Sidebar({ active, setActive }) {
  return (
    <div
      style={{
        width: 220,
        minWidth: 220,
        background: 'var(--bg-panel)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <div style={{
            width: 28, height: 28,
            background: 'var(--accent-gold)',
            borderRadius: 3,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#070b13',
            fontFamily: "'Syne', sans-serif",
            fontWeight: 800,
            fontSize: 14,
            letterSpacing: '-0.02em',
            flexShrink: 0,
          }}>O</div>
          <div>
            <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 16, letterSpacing: '-0.01em', lineHeight: 1 }}>BD for Law</div>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: 2 }}>Intelligence OS</div>
          </div>
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8, padding: '4px 6px', background: 'var(--bg-elevated)', borderRadius: 2, letterSpacing: '0.02em' }}>
          {FIRM_NAME}
        </div>
      </div>

      {/* Nav sections */}
      <div style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        {NAV_SECTIONS.map(section => (
          <div key={section.label} style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", color: 'var(--text-muted)', letterSpacing: '0.12em', padding: '6px 6px 4px', marginBottom: 2 }}>
              {section.label}
            </div>
            {section.items.map(item => (
              <button
                key={item.id}
                className={`nav-item ${active === item.id ? 'active' : ''}`}
                style={{ width: '100%', textAlign: 'left', border: 'none', background: 'none' }}
                onClick={() => setActive(item.id)}
              >
                <span style={{ fontSize: 13, width: 16, textAlign: 'center', flexShrink: 0 }}>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* Bottom status */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', fontSize: 10, color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
          <span className="signal-dot animate-pulse-gold" style={{ background: 'var(--accent-green)' }}></span>
          <span>All signal feeds active</span>
        </div>
        <div style={{ fontFamily: "'IBM Plex Mono', monospace" }}>v2.4.1 · Nov 2025</div>
      </div>
    </div>
  )
}
