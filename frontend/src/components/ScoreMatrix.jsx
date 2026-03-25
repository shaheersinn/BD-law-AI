/**
 * components/ScoreMatrix.jsx
 *
 * 34 × 3 mandate probability table.
 * Colour scale: white (0.0) → teal (#0C9182) (1.0)
 * Sorted by highest 30d score descending.
 * Clicking a row navigates to company detail (via onRowClick prop).
 */

import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'

// Convert a 0–1 probability to a background-colour string on white→teal scale
function scoreToColor(score) {
  if (score == null) return '#f9fafb'
  const clamped = Math.max(0, Math.min(1, score))
  // Interpolate between #ffffff and #0C9182
  const r = Math.round(255 - clamped * (255 - 12))
  const g = Math.round(255 - clamped * (255 - 145))
  const b = Math.round(255 - clamped * (255 - 130))
  return `rgb(${r},${g},${b})`
}

function ScoreCell({ value }) {
  const display = value != null ? (value * 100).toFixed(0) + '%' : '—'
  return (
    <td
      style={{
        background: scoreToColor(value),
        textAlign: 'center',
        padding: '6px 10px',
        fontSize: '0.8rem',
        fontFamily: 'JetBrains Mono, monospace',
        color: value != null && value > 0.6 ? '#fff' : '#374151',
        border: '1px solid #f0f0f0',
        whiteSpace: 'nowrap',
      }}
    >
      {display}
    </td>
  )
}

export default function ScoreMatrix({ scores, companyId }) {
  const navigate = useNavigate()

  const rows = useMemo(() => {
    if (!scores) return []
    return Object.entries(scores)
      .map(([pa, horizons]) => ({
        pa,
        s30: horizons['30d'] ?? null,
        s60: horizons['60d'] ?? null,
        s90: horizons['90d'] ?? null,
      }))
      .sort((a, b) => (b.s30 ?? 0) - (a.s30 ?? 0))
  }, [scores])

  if (!rows.length) {
    return (
      <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No scores available.</p>
    )
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ background: '#f9fafb' }}>
            <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 600, color: '#374151', border: '1px solid #e5e7eb' }}>
              Practice Area
            </th>
            <th style={{ textAlign: 'center', padding: '8px 12px', fontWeight: 600, color: '#374151', border: '1px solid #e5e7eb' }}>
              30d
            </th>
            <th style={{ textAlign: 'center', padding: '8px 12px', fontWeight: 600, color: '#374151', border: '1px solid #e5e7eb' }}>
              60d
            </th>
            <th style={{ textAlign: 'center', padding: '8px 12px', fontWeight: 600, color: '#374151', border: '1px solid #e5e7eb' }}>
              90d
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ pa, s30, s60, s90 }) => (
            <tr
              key={pa}
              onClick={() => companyId && navigate(`/companies/${companyId}`)}
              style={{ cursor: companyId ? 'pointer' : 'default' }}
            >
              <td style={{
                padding: '6px 12px',
                border: '1px solid #f0f0f0',
                color: '#1f2937',
                fontWeight: 500,
                textTransform: 'capitalize',
              }}>
                {pa.replace(/_/g, ' ')}
              </td>
              <ScoreCell value={s30} />
              <ScoreCell value={s60} />
              <ScoreCell value={s90} />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
