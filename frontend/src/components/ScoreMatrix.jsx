/**
 * components/ScoreMatrix.jsx — Digital Atelier 34×3 mandate probability table.
 *
 * No 1px solid borders — uses tonal row alternation.
 * Newsreader for practice area labels.
 * JetBrains Mono for probability values.
 * 5-band heatmap from design-system.css --score-* vars.
 */

import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import Sparkline from './Sparkline'

/** Map a 0–1 probability to the correct heatmap band. */
function scoreBand(v) {
  if (v == null)  return { bg: 'var(--color-surface-container-high)', text: 'var(--color-on-surface-variant)', label: '—' }
  if (v >= 0.9)   return { bg: 'var(--score-4)', text: 'var(--color-on-primary)' }
  if (v >= 0.7)   return { bg: 'var(--score-3)', text: 'var(--color-on-primary)' }
  if (v >= 0.5)   return { bg: 'var(--score-2)', text: 'var(--color-on-surface)' }
  if (v >= 0.3)   return { bg: 'var(--score-1)', text: 'var(--color-on-surface)' }
  return           { bg: 'var(--score-0)', text: 'var(--color-on-surface-variant)' }
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
      whiteSpace: 'nowrap',
      transition: 'background 150ms ease-out',
    }}>
      {display}
    </td>
  )
}

function PracticeAreaLabel({ pa }) {
  const label = pa
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')

  return (
    <span style={{
      fontFamily: 'var(--font-editorial)',
      fontWeight: 500,
      fontSize: 13,
      color: 'var(--color-on-surface)',
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
        color: 'var(--color-on-surface-variant)', fontSize: 13,
        fontFamily: 'var(--font-data)',
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
    fontWeight: 700,
    fontSize: '0.6875rem',
    color: 'var(--color-on-surface-variant)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    background: 'var(--color-surface-container-low)',
    whiteSpace: 'nowrap',
    fontFamily: 'var(--font-data)',
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
          {rows.map(({ pa, s30, s60, s90, history }, i) => (
            <tr
              key={pa}
              onClick={() => companyId && navigate(`/companies/${companyId}`)}
              style={{
                cursor: companyId ? 'pointer' : 'default',
                transition: 'background 150ms ease-out',
              }}
              onMouseEnter={e => { if (companyId) e.currentTarget.style.background = 'var(--color-surface-container-high)' }}
              onMouseLeave={e => { e.currentTarget.style.background = i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent' }}
            >
              <td style={{
                padding: '7px 16px',
                background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'var(--color-surface-container-lowest)',
              }}>
                <PracticeAreaLabel pa={pa} />
              </td>
              <ScoreCell value={s30} />
              <ScoreCell value={s60} />
              <ScoreCell value={s90} />
              {showSparklines && (
                <td style={{
                  padding: '4px 14px',
                  background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'var(--color-surface-container-lowest)',
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
