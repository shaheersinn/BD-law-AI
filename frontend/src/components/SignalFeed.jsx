/**
 * components/SignalFeed.jsx — ConstructLex Pro signal feed.
 *
 * Changes from Phase 8A:
 * - Design tokens throughout (no hardcoded colours)
 * - Confidence badge uses 3 colour bands
 * - Loading skeleton state
 * - Empty state with contextual messaging
 * - Signal card border-left accent per confidence band
 */

import { useState } from 'react'
import { Skeleton } from './Skeleton'

const PAGE_SIZE = 20

function confidenceBand(score) {
  if (score == null) return { color: 'var(--text-tertiary)', bg: 'var(--surface-raised)', label: 'N/A' }
  const pct = Math.round(score * 100)
  if (pct >= 80) return { color: 'var(--success)', bg: 'var(--success-bg)', label: `${pct}%`, accent: 'var(--success)' }
  if (pct >= 50) return { color: 'var(--warning)', bg: 'var(--warning-bg)', label: `${pct}%`, accent: '#D97706' }
  return               { color: 'var(--error)',   bg: 'var(--error-bg)',   label: `${pct}%`, accent: '#DC2626' }
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
      borderRadius: 999,
      marginLeft: 8,
      border: `1px solid ${color}22`,
      letterSpacing: '0.02em',
    }}>
      {label}
    </span>
  )
}

function SignalCard({ signal }) {
  const { accent } = confidenceBand(signal.confidence_score)
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderLeft: `3px solid ${accent || 'var(--border)'}`,
      borderRadius: 'var(--radius-md)',
      padding: '12px 16px',
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
        <span style={{
          fontSize: 11,
          fontWeight: 700,
          color: 'var(--accent)',
          textTransform: 'uppercase',
          letterSpacing: '0.07em',
          fontFamily: 'var(--font-mono)',
        }}>
          {signal.signal_type}
        </span>
        <ConfidenceBadge score={signal.confidence_score} />
        {signal.practice_area_hints && (
          <span style={{
            marginLeft: 'auto',
            fontSize: 10,
            color: 'var(--text-tertiary)',
            background: 'var(--surface-raised)',
            border: '1px solid var(--border)',
            padding: '1px 7px',
            borderRadius: 4,
            fontFamily: 'var(--font-body)',
            letterSpacing: '0.04em',
          }}>
            {signal.practice_area_hints}
          </span>
        )}
      </div>

      {/* Signal text */}
      {signal.signal_text && (
        <p style={{
          fontSize: 13,
          color: 'var(--text)',
          margin: '0 0 8px',
          lineHeight: 1.55,
        }}>
          {signal.signal_text.length > 240
            ? signal.signal_text.slice(0, 240) + '…'
            : signal.signal_text}
        </p>
      )}

      {/* Footer */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        fontSize: 11, color: 'var(--text-tertiary)',
      }}>
        {signal.scraped_at && (
          <span>{new Date(signal.scraped_at).toLocaleString('en-CA', { dateStyle: 'medium', timeStyle: 'short' })}</span>
        )}
        {signal.source_id && (
          <span style={{ color: 'var(--border-strong)' }}>·</span>
        )}
        {signal.source_id && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{signal.source_id}</span>
        )}
        {signal.source_url && (
          <a
            href={signal.source_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              marginLeft: 'auto', color: 'var(--accent)',
              fontSize: 11, fontWeight: 500,
              transition: 'opacity var(--transition)',
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
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', padding: '14px 16px',
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
        color: 'var(--text-tertiary)',
      }}>
        <div style={{ fontSize: 28, marginBottom: 8 }}>📡</div>
        <div style={{ fontSize: 13, fontWeight: 500 }}>No signals yet</div>
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
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    color: 'var(--text)',
    background: 'var(--surface)',
    fontFamily: 'var(--font-body)',
    cursor: 'pointer',
    outline: 'none',
  }

  const btnStyle = (disabled) => ({
    padding: '6px 14px',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    background: disabled ? 'var(--surface-raised)' : 'var(--surface)',
    color: disabled ? 'var(--text-tertiary)' : 'var(--text)',
    cursor: disabled ? 'default' : 'pointer',
    fontSize: 12,
    fontFamily: 'var(--font-body)',
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

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
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
          <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 60, textAlign: 'center' }}>
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
