import React from 'react'

export function PageHeader({ title, subtitle, tag, actions }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24, paddingBottom: 16, borderBottom: '1px solid var(--border)' }}>
      <div>
        {tag && (
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: 'var(--accent-gold)', letterSpacing: '0.12em', marginBottom: 6, textTransform: 'uppercase' }}>
            ◈ {tag}
          </div>
        )}
        <h1 style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 22, letterSpacing: '-0.02em', marginBottom: 4 }}>{title}</h1>
        {subtitle && <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{subtitle}</p>}
      </div>
      {actions && <div style={{ display: 'flex', gap: 8 }}>{actions}</div>}
    </div>
  )
}

export function MetricCard({ label, value, change, changeDir, sub, accent, mono }) {
  const colors = {
    gold: 'var(--accent-gold)',
    blue: 'var(--accent-blue)',
    red: 'var(--accent-red)',
    green: 'var(--accent-green)',
    purple: 'var(--accent-purple)',
    default: 'var(--text-primary)',
  }
  return (
    <div className="metric-card" style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: mono !== false ? "'IBM Plex Mono', monospace" : "'Syne', sans-serif", fontSize: 28, fontWeight: 700, color: colors[accent] || colors.default, letterSpacing: '-0.02em', lineHeight: 1 }}>{value}</div>
      {(change !== undefined || sub) && (
        <div style={{ marginTop: 6, fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
          {change !== undefined && (
            <span style={{ color: changeDir === 'up' ? 'var(--accent-green)' : changeDir === 'down' ? 'var(--accent-red)' : 'var(--text-muted)' }}>
              {changeDir === 'up' ? '↑' : changeDir === 'down' ? '↓' : '→'} {Math.abs(change)}%
            </span>
          )}
          {sub && <span style={{ color: 'var(--text-muted)' }}>{sub}</span>}
        </div>
      )}
      {accent && (
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 2, background: colors[accent], opacity: 0.4 }} />
      )}
    </div>
  )
}

export function RiskBadge({ level }) {
  const map = {
    critical: { label: 'CRITICAL', cls: 'risk-critical' },
    high: { label: 'HIGH', cls: 'risk-high' },
    medium: { label: 'MEDIUM', cls: 'risk-medium' },
    low: { label: 'LOW', cls: 'risk-low' },
  }
  const { label, cls } = map[level] || map.low
  return (
    <span className={cls} style={{ fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.08em', padding: '2px 7px', borderRadius: 2 }}>
      {label}
    </span>
  )
}

export function ScoreBar({ score, color }) {
  const colors = {
    red: '#ef4444', orange: '#f97316', yellow: '#eab308', green: '#22c55e',
    blue: '#3b82f6', gold: 'var(--accent-gold)',
  }
  const auto = score >= 75 ? colors.red : score >= 50 ? colors.orange : score >= 30 ? colors.yellow : colors.green
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div className="progress-bar" style={{ flex: 1 }}>
        <div className="progress-fill" style={{ width: `${score}%`, background: color ? colors[color] : auto }} />
      </div>
      <span className="data-display" style={{ fontSize: 12, color: color ? colors[color] : auto, width: 28, textAlign: 'right' }}>{score}</span>
    </div>
  )
}

export function Section({ title, children, actions, style }) {
  return (
    <div className="panel" style={{ padding: '16px 18px', ...style }}>
      {title && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, paddingBottom: 12, borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: '0.06em', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{title}</div>
          {actions}
        </div>
      )}
      {children}
    </div>
  )
}

export function Tag({ children, color }) {
  const cols = {
    gold: { bg: 'rgba(232,168,58,0.1)', border: 'rgba(232,168,58,0.3)', text: 'var(--accent-gold)' },
    blue: { bg: 'rgba(59,130,246,0.1)', border: 'rgba(59,130,246,0.3)', text: '#60a5fa' },
    red: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', text: '#f87171' },
    green: { bg: 'rgba(34,197,94,0.1)', border: 'rgba(34,197,94,0.3)', text: '#4ade80' },
    purple: { bg: 'rgba(168,85,247,0.1)', border: 'rgba(168,85,247,0.3)', text: '#c084fc' },
    default: { bg: 'var(--bg-elevated)', border: 'var(--border)', text: 'var(--text-secondary)' },
  }
  const c = cols[color] || cols.default
  return (
    <span style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.text, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", padding: '2px 7px', borderRadius: 2, letterSpacing: '0.04em' }}>
      {children}
    </span>
  )
}

export function Spinner() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" }}>
      <div style={{
        width: 14, height: 14,
        border: '2px solid var(--border)',
        borderTopColor: 'var(--accent-gold)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      Processing...
    </div>
  )
}

export function EmptyState({ icon, message }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
      <div style={{ fontSize: 28, marginBottom: 10 }}>{icon}</div>
      <div style={{ fontSize: 12 }}>{message}</div>
    </div>
  )
}

export function AIBadge() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: 'rgba(232,168,58,0.08)', border: '1px solid rgba(232,168,58,0.25)', borderRadius: 2, padding: '2px 8px', fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", color: 'var(--accent-gold)', letterSpacing: '0.08em' }}>
      ◈ AI
    </span>
  )
}
