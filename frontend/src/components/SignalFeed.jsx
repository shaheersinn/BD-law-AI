/**
 * components/SignalFeed.jsx
 *
 * Paginated list of signals, newest first.
 * Filter controls: signal_type, practice_area, company (via props).
 */

import { useState } from 'react'

const PAGE_SIZE = 20

function ConfidenceBadge({ score }) {
  if (score == null) return null
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? '#059669' : pct >= 50 ? '#d97706' : '#ef4444'
  return (
    <span style={{
      fontSize: '0.7rem',
      fontFamily: 'JetBrains Mono, monospace',
      color,
      background: `${color}15`,
      padding: '1px 6px',
      borderRadius: 4,
      marginLeft: 6,
    }}>
      {pct}%
    </span>
  )
}

export default function SignalFeed({ signals = [], filterControls = true }) {
  const [page, setPage] = useState(0)
  const [typeFilter, setTypeFilter] = useState('')

  const filtered = typeFilter
    ? signals.filter((s) => s.signal_type === typeFilter)
    : signals

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const page_items = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  // Unique signal types for filter dropdown
  const signalTypes = [...new Set(signals.map((s) => s.signal_type))].sort()

  return (
    <div>
      {filterControls && signalTypes.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(0) }}
            style={{
              padding: '6px 10px',
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              fontSize: '0.875rem',
              color: '#374151',
            }}
          >
            <option value="">All signal types</option>
            {signalTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      )}

      {page_items.length === 0 ? (
        <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No signals found.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {page_items.map((s, i) => (
            <div key={`${s.source_id}-${i}`} style={{
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              padding: '12px 16px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: '#0C9182',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}>
                  {s.signal_type}
                </span>
                <ConfidenceBadge score={s.confidence_score} />
                {s.practice_area_hints && (
                  <span style={{
                    marginLeft: 'auto',
                    fontSize: '0.7rem',
                    color: '#6b7280',
                    background: '#f3f4f6',
                    padding: '1px 6px',
                    borderRadius: 4,
                  }}>
                    {s.practice_area_hints}
                  </span>
                )}
              </div>
              {s.signal_text && (
                <p style={{ fontSize: '0.875rem', color: '#374151', margin: '4px 0', lineHeight: 1.5 }}>
                  {s.signal_text.length > 200 ? s.signal_text.slice(0, 200) + '…' : s.signal_text}
                </p>
              )}
              <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: 4 }}>
                {s.scraped_at ? new Date(s.scraped_at).toLocaleString() : ''}
                {s.source_url && (
                  <a
                    href={s.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ marginLeft: 8, color: '#0C9182' }}
                  >
                    Source ↗
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, marginTop: 16, alignItems: 'center' }}>
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            style={{
              padding: '6px 14px',
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              background: page === 0 ? '#f9fafb' : '#fff',
              cursor: page === 0 ? 'default' : 'pointer',
              fontSize: '0.875rem',
            }}
          >
            ← Prev
          </button>
          <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            style={{
              padding: '6px 14px',
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              background: page >= totalPages - 1 ? '#f9fafb' : '#fff',
              cursor: page >= totalPages - 1 ? 'default' : 'pointer',
              fontSize: '0.875rem',
            }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
