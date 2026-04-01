/**
 * components/ui/Primitives.jsx — Shared UI building blocks.
 * Design system: Digital Atelier token set (design-system.css)
 */

import { AlertTriangle } from 'lucide-react'

// ── PageHeader ────────────────────────────────────────────────────────────────
export function PageHeader({ tag, title, subtitle }) {
  return (
    <div style={{ marginBottom: '2rem' }}>
      {tag && (
        <div style={{
          fontFamily: 'var(--font-data)',
          fontSize: '0.6875rem',
          fontWeight: 700,
          color: 'var(--color-on-surface-variant)',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          marginBottom: '0.375rem',
        }}>{tag}</div>
      )}
      <h1 style={{
        fontFamily: 'var(--font-editorial)',
        fontSize: '1.5rem',
        fontWeight: 500,
        letterSpacing: '-0.01em',
        color: 'var(--color-primary)',
        margin: 0,
        marginBottom: subtitle ? '0.375rem' : 0,
      }}>{title}</h1>
      {subtitle && (
        <p style={{
          fontFamily: 'var(--font-data)',
          fontSize: '0.875rem',
          color: 'var(--color-on-surface-variant)',
          margin: 0,
        }}>{subtitle}</p>
      )}
    </div>
  )
}

// ── MetricCard ────────────────────────────────────────────────────────────────
const ACCENT_COLORS = {
  teal:  '#2b6954',
  red:   'var(--color-error)',
  gold:  '#d97706',
  blue:  '#3b82f6',
  navy:  'var(--color-primary)',
  green: 'var(--color-secondary)',
}

export function MetricCard({ label, value, sub, accent = 'teal' }) {
  const accentColor = ACCENT_COLORS[accent] || ACCENT_COLORS.teal
  return (
    <div
      style={{
        background: 'var(--color-surface-container-lowest)',
        borderRadius: 'var(--radius-xl)',
        padding: '1.25rem',
        boxShadow: 'var(--shadow-ambient)',
        position: 'relative',
        overflow: 'hidden',
        transition: 'transform var(--transition-card), box-shadow var(--transition-card)',
        cursor: 'default',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = '0 4px 24px -6px rgba(25,28,30,0.12)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = 'var(--shadow-ambient)'
      }}
    >
      <div style={{
        fontFamily: 'var(--font-data)',
        fontSize: '0.6875rem',
        fontWeight: 700,
        color: 'var(--color-on-surface-variant)',
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        marginBottom: '0.75rem',
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-data)',
        fontSize: '1.5rem',
        fontWeight: 700,
        color: 'var(--color-on-surface)',
        lineHeight: 1.2,
      }}>{value}</div>
      {sub && (
        <div style={{
          fontFamily: 'var(--font-data)',
          fontSize: '0.6875rem',
          color: 'var(--color-on-surface-variant)',
          marginTop: '0.375rem',
        }}>{sub}</div>
      )}
      {/* 2px accent bar at bottom */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 2,
        background: accentColor,
      }} />
    </div>
  )
}

// ── Panel ─────────────────────────────────────────────────────────────────────
export function Panel({ title, children, actions, style = {} }) {
  return (
    <div style={{
      background: 'var(--color-surface-container-lowest)',
      borderRadius: 'var(--radius-xl)',
      boxShadow: 'var(--shadow-ambient)',
      overflow: 'hidden',
      ...style,
    }}>
      {(title || actions) && (
        <div style={{
          padding: '1.25rem 1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'var(--color-surface-container-lowest)',
        }}>
          {title && (
            <span style={{
              fontFamily: 'var(--font-data)',
              fontSize: '0.6875rem',
              fontWeight: 700,
              color: 'var(--color-on-surface-variant)',
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
            }}>{title}</span>
          )}
          {actions && <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>{actions}</div>}
        </div>
      )}
      <div style={{ padding: '1.5rem' }}>{children}</div>
    </div>
  )
}

// ── Tag ───────────────────────────────────────────────────────────────────────
const TAG_STYLES = {
  default: { bg: 'var(--color-surface-container-high)', color: 'var(--color-on-surface-variant)' },
  green:   { bg: 'var(--color-secondary-container)',    color: 'var(--color-on-secondary-container)' },
  red:     { bg: 'var(--color-error-bg)',               color: 'var(--color-error)' },
  gold:    { bg: '#fffbeb',                             color: '#d97706' },
  blue:    { bg: '#dbeafe',                             color: '#1d4ed8' },
  navy:    { bg: 'var(--color-primary-container)',      color: 'var(--color-on-primary-container)' },
}

export function Tag({ label, color = 'default' }) {
  const s = TAG_STYLES[color] || TAG_STYLES.default
  return (
    <span style={{
      display: 'inline-block',
      fontFamily: 'var(--font-data)',
      fontSize: '0.625rem',
      fontWeight: 700,
      letterSpacing: '0.05em',
      textTransform: 'uppercase',
      padding: '2px 10px',
      borderRadius: 'var(--radius-full)',
      background: s.bg,
      color: s.color,
      whiteSpace: 'nowrap',
    }}>{label}</span>
  )
}

// ── EmptyState ────────────────────────────────────────────────────────────────
export function EmptyState({
  icon,
  title = 'No data available',
  message = 'No data yet — scrapers will populate this within 7 days',
}) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '3rem 2rem',
      textAlign: 'center',
      gap: '0.75rem',
    }}>
      {icon && (
        <div style={{ color: 'var(--color-outline-variant)', marginBottom: '0.5rem' }}>
          {icon}
        </div>
      )}
      <h3 style={{
        fontFamily: 'var(--font-editorial)',
        fontSize: '1.25rem',
        fontWeight: 500,
        color: 'var(--color-primary)',
        margin: 0,
      }}>{title}</h3>
      <p style={{
        fontFamily: 'var(--font-data)',
        fontSize: '0.875rem',
        color: 'var(--color-on-surface-variant)',
        margin: 0,
        maxWidth: 360,
        lineHeight: 1.6,
      }}>{message}</p>
    </div>
  )
}

// ── ErrorState ────────────────────────────────────────────────────────────────
export function ErrorState({ message = 'Something went wrong', onRetry }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2.5rem',
      gap: '0.75rem',
      background: 'var(--color-error-bg)',
      borderRadius: 'var(--radius-xl)',
      textAlign: 'center',
    }}>
      <AlertTriangle size={24} color="var(--color-error)" />
      <p style={{
        fontFamily: 'var(--font-data)',
        fontSize: '0.875rem',
        color: 'var(--color-error)',
        margin: 0,
      }}>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            marginTop: '0.5rem',
            padding: '0.5rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            fontFamily: 'var(--font-data)',
            fontSize: '0.75rem',
            fontWeight: 700,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            background: 'var(--color-error)',
            color: '#fff',
            cursor: 'pointer',
            border: 'none',
          }}
        >
          Retry
        </button>
      )}
    </div>
  )
}
