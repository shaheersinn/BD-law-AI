/**
 * components/SignalFeed.jsx — Digital Atelier signal feed.
 *
 * Tonal surface cards (no borders). Signal type chips.
 * Confidence badge using secondary-container.
 * Pagination with pill-style buttons.
 */

import { useState } from 'react'
import { Skeleton } from './Skeleton'

const PAGE_SIZE = 20

/* ── Signal type → category mapping for color-coded chips ─── */
const SIGNAL_CATEGORIES = {
  Regulatory: ['SEC', 'SEDAR', 'SEDI', 'CSA', 'OSFI', 'OSC_Notices'],
  Filing:     ['Annual_Report', 'Proxy_Circular', 'Press_Release', 'Financial_Statement'],
  Litigation: ['Court_Filing', 'Class_Action', 'Regulatory_Action', 'Bankruptcy'],
  Market:     ['Market_Data', 'Analyst_Report', 'Credit_Rating', 'Bond_Offering'],
  Corporate:  ['Leadership_Change', 'M_And_A', 'Restructuring', 'Layoff', 'Job_Posting'],
  Geo:        ['ADS_B', 'Satellite', 'Vessel_Tracking', 'Trade_Data'],
}

function getSignalCategory(type) {
  if (!type) return 'Other'
  for (const [cat, types] of Object.entries(SIGNAL_CATEGORIES)) {
    if (types.some(t => type.toLowerCase().includes(t.toLowerCase()))) return cat
  }
  return 'Other'
}

const CATEGORY_COLORS = {
  Regulatory: { bg: 'var(--color-error-bg)', color: 'var(--color-error)' },
  Filing:     { bg: 'var(--color-secondary-container)', color: 'var(--color-on-secondary-container)' },
  Litigation: { bg: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
  Market:     { bg: 'var(--color-surface-container-high)', color: 'var(--color-on-surface-variant)' },
  Corporate:  { bg: 'var(--color-secondary-container)', color: 'var(--color-secondary)' },
  Geo:        { bg: 'var(--color-surface-container-high)', color: 'var(--color-primary)' },
  Other:      { bg: 'var(--color-surface-container-high)', color: 'var(--color-on-surface-variant)' },
}

function confidenceBand(score) {
  if (score == null) return { color: 'var(--color-on-surface-variant)', bg: 'var(--color-surface-container-high)', label: 'N/A' }
  const pct = Math.round(score * 100)
  if (pct >= 80) return { color: 'var(--color-success)', bg: 'var(--color-success-bg)', label: `${pct}%` }
  if (pct >= 50) return { color: 'var(--color-warning)', bg: 'var(--color-warning-bg)', label: `${pct}%` }
  return               { color: 'var(--color-error)', bg: 'var(--color-error-bg)', label: `${pct}%` }
}

function ConfidenceBadge({ score }) {
  const { color, bg, label } = confidenceBand(score)
  return (
    <span style={{
      fontSize: 11,
      fontFamily: 'var(--font-mono)',
      fontWeight: 500,
      color,
      background: bg,
      padding: '2px 7px',
      borderRadius: 'var(--radius-full)',
      marginLeft: 8,
      letterSpacing: '0.02em',
    }}>
      {label}
    </span>
  )
}

function SignalTypeChip({ type }) {
  const cat = getSignalCategory(type)
  const { bg, color } = CATEGORY_COLORS[cat] || CATEGORY_COLORS.Other
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px 8px',
      borderRadius: 'var(--radius-full)',
      background: bg,
      color,
      fontFamily: 'var(--font-data)',
      fontSize: '0.6875rem',
      fontWeight: 700,
      letterSpacing: '0.05em',
      textTransform: 'uppercase',
    }}>
      {type}
    </span>
  )
}

function SignalCard({ signal }) {
  return (
    <div style={{
      background: 'var(--color-surface-container-lowest)',
      borderRadius: 'var(--radius-xl)',
      padding: '14px 18px',
      boxShadow: 'var(--shadow-ambient)',
      transition: 'transform 200ms ease-out',
    }}
      onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-1px)'}
      onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
        <SignalTypeChip type={signal.signal_type} />
        <ConfidenceBadge score={signal.confidence_score} />
        {signal.practice_area_hints && (
          <span style={{
            marginLeft: 'auto',
            fontSize: 11,
            color: 'var(--color-on-surface-variant)',
            background: 'var(--color-surface-container-high)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            fontFamily: 'var(--font-data)',
            fontWeight: 600,
            letterSpacing: '0.03em',
          }}>
            {signal.practice_area_hints}
          </span>
        )}
      </div>

      {/* Signal text */}
      {signal.signal_text && (
        <p style={{
          fontSize: 13,
          color: 'var(--color-on-surface)',
          margin: '0 0 8px',
          lineHeight: 1.6,
          fontFamily: 'var(--font-data)',
          letterSpacing: '0.01em',
        }}>
          {signal.signal_text.length > 240
            ? signal.signal_text.slice(0, 240) + '…'
            : signal.signal_text}
        </p>
      )}

      {/* Footer */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        fontSize: 11, color: 'var(--color-on-surface-variant)',
        fontFamily: 'var(--font-data)',
      }}>
        {signal.scraped_at && (
          <span>{new Date(signal.scraped_at).toLocaleString('en-CA', { dateStyle: 'medium', timeStyle: 'short' })}</span>
        )}
        {signal.source_id && (
          <>
            <span>·</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{signal.source_id}</span>
          </>
        )}
        {signal.source_url && (
          <a
            href={signal.source_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              marginLeft: 'auto', color: 'var(--color-primary)',
              fontSize: 11, fontWeight: 600,
              transition: 'opacity 150ms ease-out',
              fontFamily: 'var(--font-data)',
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = '0.7'}
            onMouseLeave={e => e.currentTarget.style.opacity = '1'}
          >
            Source ↗
          </a>
        )}
      </div>
    </div>
  )
}

export default function SignalFeed({ signals = [], loading = false, filterControls = true }) {
  const [page, setPage] = useState(0)
  const [typeFilter, setTypeFilter] = useState('')

  // Loading state
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} style={{
            background: 'var(--color-surface-container-lowest)',
            borderRadius: 'var(--radius-xl)',
            padding: '14px 18px',
            boxShadow: 'var(--shadow-ambient)',
          }}>
            <Skeleton width="30%" height={12} style={{ marginBottom: 10 }} />
            <Skeleton height={12} style={{ marginBottom: 6 }} />
            <Skeleton width="70%" height={12} />
          </div>
        ))}
      </div>
    )
  }

  // Empty state
  if (!signals.length) {
    return (
      <div style={{
        padding: '3rem 2rem', textAlign: 'center',
        color: 'var(--color-on-surface-variant)',
        fontFamily: 'var(--font-data)',
      }}>
        <div style={{ fontSize: 28, marginBottom: 8 }}>📡</div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>No signals yet</div>
        <div style={{ fontSize: 12, marginTop: 4 }}>
          Signals appear here as scrapers collect new data.
        </div>
      </div>
    )
  }

  const signalTypes = [...new Set(signals.map((s) => s.signal_type))].sort()
  const filtered = typeFilter ? signals.filter((s) => s.signal_type === typeFilter) : signals
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageItems = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const selectStyle = {
    padding: '7px 12px',
    outline: '1px solid rgba(197, 198, 206, 0.15)',
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    color: 'var(--color-on-surface)',
    background: 'var(--color-surface-container-lowest)',
    fontFamily: 'var(--font-data)',
    cursor: 'pointer',
  }

  const btnStyle = (disabled) => ({
    padding: '6px 14px',
    background: disabled
      ? 'var(--color-surface-container-high)'
      : 'var(--color-surface-container-lowest)',
    color: disabled
      ? 'var(--color-on-surface-variant)'
      : 'var(--color-on-surface)',
    cursor: disabled ? 'default' : 'pointer',
    fontSize: 12,
    fontFamily: 'var(--font-data)',
    borderRadius: 'var(--radius-md)',
    outline: '1px solid rgba(197, 198, 206, 0.15)',
    transition: 'background 150ms ease-out',
  })

  return (
    <div>
      {filterControls && signalTypes.length > 1 && (
        <div style={{ marginBottom: 14 }}>
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(0) }}
            style={selectStyle}
          >
            <option value="">All signal types</option>
            {signalTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {pageItems.map((s, i) => (
          <SignalCard key={`${s.source_id}-${i}`} signal={s} />
        ))}
      </div>

      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, marginTop: 18, alignItems: 'center' }}>
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            style={btnStyle(page === 0)}
          >
            ← Prev
          </button>
          <span style={{
            fontSize: 12,
            color: 'var(--color-on-surface-variant)',
            minWidth: 60,
            textAlign: 'center',
            fontFamily: 'var(--font-data)',
          }}>
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            style={btnStyle(page >= totalPages - 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
