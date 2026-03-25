/**
 * pages/DashboardPage.jsx — ConstructLex Pro dashboard.
 *
 * Phase 8B changes:
 * - AppShell + Sidebar (no inline nav bar)
 * - Top 20 highest-velocity companies table (calls /v1/scores/top-velocity)
 * - Trend charts below velocity table
 * - Skeleton loading states
 * - Stat cards row
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { trends as trendsApi, scores as scoresApi } from '../api/client'
import TrendCharts from '../components/TrendCharts'
import VelocityBadge from '../components/VelocityBadge'
import { SkeletonCard, Skeleton } from '../components/Skeleton'
import AppShell from '../components/layout/AppShell'

// ── Shared card style ──────────────────────────────────────────────────────────
const card = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-lg)',
  padding: '1.5rem',
  marginBottom: '1.5rem',
  boxShadow: 'var(--shadow-sm)',
}

const cardTitle = {
  fontFamily: 'var(--font-display)',
  fontWeight: 700,
  fontSize: 18,
  color: 'var(--text)',
  marginBottom: '1rem',
  letterSpacing: '0.01em',
}

function PageHeader() {
  return (
    <div style={{ marginBottom: '2rem' }}>
      <h1 style={{
        fontFamily: 'var(--font-display)',
        fontWeight: 700, fontSize: 32,
        color: 'var(--text)', margin: 0, marginBottom: 6,
        letterSpacing: '0.02em',
      }}>
        BD Intelligence
      </h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: 13, margin: 0 }}>
        Mandate probability signals across 34 practice areas
      </p>
    </div>
  )
}

function VelocityRow({ item, rank }) {
  const navigate = useNavigate()
  return (
    <tr
      onClick={() => navigate(`/companies/${item.company_id}`)}
      style={{ cursor: 'pointer', borderBottom: '1px solid var(--surface-raised)' }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-hover)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-tertiary)', width: 32 }}>
        {rank}
      </td>
      <td style={{ padding: '10px 12px' }}>
        <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text)' }}>{item.company_name || `Company ${item.company_id}`}</div>
        {item.sector && <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 1 }}>{item.sector}</div>}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
        <VelocityBadge velocity={item.velocity_score} size="sm" />
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)' }}>
        {item.top_practice_area
          ? item.top_practice_area.replace(/_/g, ' ')
          : '—'}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--accent)' }}>
        {item.top_score_30d != null ? `${(item.top_score_30d * 100).toFixed(0)}%` : '—'}
      </td>
    </tr>
  )
}

export default function DashboardPage() {
  const [trendData,     setTrendData]     = useState([])
  const [velocityData,  setVelocityData]  = useState([])
  const [trendLoading,  setTrendLoading]  = useState(true)
  const [velLoading,    setVelLoading]    = useState(true)

  useEffect(() => {
    trendsApi.practiceAreas()
      .then(setTrendData)
      .catch(() => setTrendData([]))
      .finally(() => setTrendLoading(false))

    scoresApi.topVelocity?.(20)
      .then(setVelocityData)
      .catch(() => setVelocityData([]))
      .finally(() => setVelLoading(false))
  }, [])

  const thStyle = {
    padding: '8px 12px',
    fontSize: 10, fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    textAlign: 'left',
    background: 'var(--surface-raised)',
    border: 'none',
    borderBottom: '1px solid var(--border)',
    whiteSpace: 'nowrap',
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <PageHeader />

        {/* ── Top velocity table ───────────────────────────────────────────── */}
        <div style={card}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h2 style={cardTitle}>Highest Velocity Companies</h2>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Top 20 by 7-day mandate probability change</span>
          </div>

          {velLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} height={40} style={{ opacity: 1 - i * 0.08 }} />
              ))}
            </div>
          ) : velocityData.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
              <div style={{ fontSize: 24, marginBottom: 6 }}>⏱</div>
              Velocity data will appear after the first scoring run completes.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ ...thStyle, width: 32 }}>#</th>
                    <th style={thStyle}>Company</th>
                    <th style={{ ...thStyle, textAlign: 'center' }}>Velocity</th>
                    <th style={{ ...thStyle, textAlign: 'center' }}>Top Practice Area</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Score (30d)</th>
                  </tr>
                </thead>
                <tbody>
                  {velocityData.map((item, i) => (
                    <VelocityRow key={item.company_id} item={item} rank={i + 1} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Trend charts ─────────────────────────────────────────────────── */}
        <div style={card}>
          <h2 style={cardTitle}>Signal Volume by Practice Area</h2>
          <TrendCharts data={trendData} loading={trendLoading} />
        </div>
      </div>
    </AppShell>
  )
}
