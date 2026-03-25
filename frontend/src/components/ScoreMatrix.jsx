/**
 * components/ScoreMatrix.jsx — 34×3 mandate probability table.
 *
 * ConstructLex Pro design system applied:
 * - 5-band heatmap (see design-system.css --score-* vars)
 * - Cormorant Garamond for practice area labels
 * - JetBrains Mono for probability values
 * - Optional sparklines column (7-day history per practice area)
 * - Sort by highest 30d score descending
 */

import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import Sparkline from './Sparkline'

/** Map a 0–1 probability to the correct heatmap band. */
function scoreBand(v) {
  if (v == null)  return { bg: 'var(--surface-raised)', text: 'var(--text-tertiary)', label: '—' }
  if (v >= 0.9)   return { bg: 'var(--score-4)', text: '#fff' }
  if (v >= 0.7)   return { bg: 'var(--score-3)', text: '#fff' }
  if (v >= 0.5)   return { bg: 'var(--score-2)', text: 'var(--text)' }
  if (v >= 0.3)   return { bg: 'var(--score-1)', text: 'var(--text)' }
  return           { bg: 'var(--score-0)', text: 'var(--text-secondary)' }
}

function ScoreCell({ value }) {
  const { bg, text } = scoreBand(value)
  const display = value != null ? (value * 100).toFixed(0) + '%' : '—'
  return (
    <td style={{
      background: bg,
      color: text,
      textAlign: 'center',
      padding: '7px 12px',
      fontSize: 12,
      fontFamily: 'var(--font-mono)',
      fontWeight: 500,
      border: '1px solid var(--bg)',
      whiteSpace: 'nowrap',
      transition: 'background var(--transition)',
    }}>
      {display}
    </td>
  )
}

function PracticeAreaLabel({ pa }) {
  // Humanise slug: "data_privacy_tech" → "Data Privacy & Tech"
  const label = pa
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')

  return (
    <span style={{
      fontFamily: 'var(--font-display)',
      fontWeight: 600,
      fontSize: 13,
      color: 'var(--text)',
      letterSpacing: '0.01em',
    }}>
      {label}
    </span>
  )
}

export default function ScoreMatrix({ scores, sparklines, companyId }) {
  const navigate = useNavigate()

  const rows = useMemo(() => {
    if (!scores) return []
    return Object.entries(scores)
      .map(([pa, horizons]) => ({
        pa,
        s30: horizons['30d'] ?? null,
        s60: horizons['60d'] ?? null,
        s90: horizons['90d'] ?? null,
        history: sparklines?.[pa] ?? [],
      }))
      .sort((a, b) => (b.s30 ?? 0) - (a.s30 ?? 0))
  }, [scores, sparklines])

  if (!rows.length) {
    return (
      <div style={{
        padding: '3rem 2rem', textAlign: 'center',
        color: 'var(--text-tertiary)', fontSize: 13,
      }}>
        <div style={{ fontSize: 32, marginBottom: 8 }}>—</div>
        No scores available yet. Scoring may still be pending.
      </div>
    )
  }

  const showSparklines = rows.some((r) => r.history.length > 1)

  const thStyle = {
    textAlign: 'center',
    padding: '10px 14px',
    fontWeight: 600,
    fontSize: 11,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    background: 'var(--surface-raised)',
    border: '1px solid var(--border)',
    whiteSpace: 'nowrap',
    fontFamily: 'var(--font-body)',
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{
        borderCollapse: 'collapse',
        width: '100%',
        fontSize: 13,
      }}>
        <thead>
          <tr>
            <th style={{ ...thStyle, textAlign: 'left', padding: '10px 16px', width: 200 }}>
              Practice Area
            </th>
            <th style={{ ...thStyle }}>30 Day</th>
            <th style={{ ...thStyle }}>60 Day</th>
            <th style={{ ...thStyle }}>90 Day</th>
            {showSparklines && (
              <th style={{ ...thStyle }}>7-Day Trend</th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map(({ pa, s30, s60, s90, history }) => (
            <tr
              key={pa}
              onClick={() => companyId && navigate(`/companies/${companyId}`)}
              style={{
                cursor: companyId ? 'pointer' : 'default',
                transition: 'background var(--transition)',
              }}
              onMouseEnter={e => { if (companyId) e.currentTarget.style.outline = '2px solid var(--accent-light)' }}
              onMouseLeave={e => { e.currentTarget.style.outline = 'none' }}
            >
              <td style={{
                padding: '7px 16px',
                border: '1px solid var(--bg)',
                background: 'var(--surface)',
              }}>
                <PracticeAreaLabel pa={pa} />
              </td>
              <ScoreCell value={s30} />
              <ScoreCell value={s60} />
              <ScoreCell value={s90} />
              {showSparklines && (
                <td style={{
                  padding: '4px 14px',
                  border: '1px solid var(--bg)',
                  background: 'var(--surface)',
                  verticalAlign: 'middle',
                }}>
                  <Sparkline values={history} width={80} height={22} />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
