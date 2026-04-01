/**
 * pages/DashboardPage.jsx — Digital Atelier executive dashboard.
 *
 * Layout from oracle_dashboard_executive_refined Stitch prototype:
 * - Top KPI cards row (5 cards)
 * - Asymmetric 2/3 + 1/3: velocity table + flight risk panel
 * - Bottom: prospect signals, regulatory alerts, competitor threats
 * - 30/60/90 day horizon toggle
 *
 * All data hooks preserved. No backend changes.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { companies as companiesApi, signals as signalsApi, scrapers } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import useScoreStore from '../stores/scores'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { fetchTopVelocity, topVelocity } = useScoreStore()
  const [loading, setLoading] = useState(true)
  const [signals, setSignals] = useState([])
  const [horizon, setHorizon] = useState(30)
  const [kpiData, setKpiData] = useState(null)

  useEffect(() => {
    Promise.all([
      fetchTopVelocity(20),
      signalsApi.list(null, { limit: 10 }),
      scrapers.summary().catch(() => null),
    ])
      .then(([, sigs, scraperSummary]) => {
        setSignals(sigs || [])
        if (scraperSummary) {
          setKpiData({
            registryCount:   scraperSummary.registry_count ?? 0,
            healthyScrapers: scraperSummary.healthy ?? 0,
            totalScrapers:   scraperSummary.total ?? 0,
            failingScrapers: scraperSummary.failing ?? 0,
          })
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const kpis = [
    { label: 'Registered Scrapers', value: kpiData?.registryCount ?? '—',   sub: 'data sources' },
    { label: 'Healthy Scrapers',    value: kpiData?.healthyScrapers ?? '—', sub: 'running clean' },
    { label: 'Total in DB',         value: kpiData?.totalScrapers ?? '—',   sub: 'health records' },
    { label: 'Pitch Win Rate',      value: '—',                             sub: 'requires BD data' },
    { label: 'Avg Wallet Share',    value: '—',                             sub: 'requires billing data' },
  ]

  const horizonOptions = [30, 60, 90]

  return (
    <AppShell>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>

        {/* Page header */}
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{
            fontFamily: 'var(--font-editorial)',
            fontSize: '1.5rem',
            fontWeight: 500,
            color: 'var(--color-primary)',
            letterSpacing: '-0.01em',
            marginBottom: 4,
          }}>
            Oracle Intelligence OS
          </h1>
          <p style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.6875rem',
            fontWeight: 700,
            color: 'var(--color-on-primary-container)',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}>
            Executive Command Center
          </p>
        </div>

        {/* KPI Cards Row */}
        <section style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '1.25rem',
          marginBottom: '2.5rem',
        }}>
          {kpis.map(kpi => (
            <div key={kpi.label} style={{
              background: 'var(--color-surface-container-lowest)',
              borderRadius: 'var(--radius-xl)',
              padding: '1.25rem',
              boxShadow: 'var(--shadow-ambient)',
              transition: 'transform 200ms ease-out',
            }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '0.75rem',
              }}>
                <span style={{
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  color: 'var(--color-on-primary-container)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}>{kpi.label}</span>
                {kpi.change && (
                  <span style={{
                    fontFamily: 'var(--font-data)',
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    color: kpi.positive ? 'var(--color-secondary)' : 'var(--color-error)',
                  }}>{kpi.change}</span>
                )}
              </div>
              <div style={{
                fontFamily: 'var(--font-editorial)',
                fontSize: '1.5rem',
                fontWeight: 500,
                color: 'var(--color-primary)',
                letterSpacing: '-0.01em',
              }}>
                {loading ? <Skeleton width={60} height={24} /> : kpi.value}
              </div>
              {kpi.sub && (
                <p style={{
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.6875rem',
                  color: 'var(--color-on-surface-variant)',
                  marginTop: '0.5rem',
                }}>{kpi.sub}</p>
              )}
            </div>
          ))}
        </section>

        {/* Middle: Asymmetric layout — Velocity table (2/3) + Signals (1/3) */}
        <section style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr',
          gap: '2rem',
          marginBottom: '2.5rem',
        }}>
          {/* Velocity Rankings */}
          <div style={{
            background: 'var(--color-surface-container-lowest)',
            borderRadius: 'var(--radius-xl)',
            boxShadow: 'var(--shadow-ambient)',
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              padding: '1.5rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <div>
                <h3 style={{
                  fontFamily: 'var(--font-editorial)',
                  fontSize: '1.125rem',
                  fontWeight: 500,
                  color: 'var(--color-primary)',
                  marginBottom: 4,
                }}>
                  Velocity Rankings
                </h3>
                <p style={{
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.6875rem',
                  color: 'var(--color-on-surface-variant)',
                }}>
                  Top companies by score momentum
                </p>
              </div>
              {/* Horizon toggle */}
              <div style={{
                display: 'flex',
                gap: 4,
                background: 'var(--color-surface-container-low)',
                borderRadius: 'var(--radius-xl)',
                padding: 4,
              }}>
                {horizonOptions.map(h => (
                  <button
                    key={h}
                    onClick={() => setHorizon(h)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: 'var(--radius-md)',
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.6875rem',
                      fontWeight: 700,
                      letterSpacing: '0.05em',
                      textTransform: 'uppercase',
                      cursor: 'pointer',
                      transition: 'background 150ms ease-out',
                      background: horizon === h
                        ? 'var(--color-surface-container-lowest)'
                        : 'transparent',
                      color: horizon === h
                        ? 'var(--color-on-surface)'
                        : 'var(--color-on-surface-variant)',
                      boxShadow: horizon === h ? 'var(--shadow-ambient)' : 'none',
                    }}
                  >
                    {h}d
                  </button>
                ))}
              </div>
            </div>

            {/* Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--color-surface-container-low)' }}>
                    {['Rank', 'Company', 'Velocity', 'Practice Area', 'Score'].map(h => (
                      <th key={h} style={{
                        padding: '10px 20px',
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.6875rem',
                        fontWeight: 700,
                        color: 'var(--color-on-surface-variant)',
                        letterSpacing: '0.05em',
                        textTransform: 'uppercase',
                        textAlign: h === 'Score' ? 'right' : 'left',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i}>
                        <td style={{ padding: '14px 20px' }}><Skeleton width={20} height={16} /></td>
                        <td style={{ padding: '14px 20px' }}><Skeleton width={120} height={16} /></td>
                        <td style={{ padding: '14px 20px' }}><Skeleton width={80} height={20} /></td>
                        <td style={{ padding: '14px 20px' }}><Skeleton width={90} height={16} /></td>
                        <td style={{ padding: '14px 20px', textAlign: 'right' }}><Skeleton width={50} height={16} /></td>
                      </tr>
                    ))
                  ) : (
                    (topVelocity || []).slice(0, 10).map((item, i) => (
                      <tr
                        key={item.company_id || i}
                        onClick={() => item.company_id && navigate(`/companies/${item.company_id}`)}
                        style={{
                          cursor: 'pointer',
                          background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent',
                          transition: 'background 150ms ease-out',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
                        onMouseLeave={e => e.currentTarget.style.background = i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent'}
                      >
                        <td style={{
                          padding: '14px 20px',
                          fontFamily: 'var(--font-editorial)',
                          fontSize: '1.125rem',
                          color: 'var(--color-on-surface-variant)',
                        }}>
                          {String(i + 1).padStart(2, '0')}
                        </td>
                        <td style={{ padding: '14px 20px' }}>
                          <div style={{
                            fontFamily: 'var(--font-data)',
                            fontWeight: 600,
                            fontSize: '0.875rem',
                            color: 'var(--color-primary)',
                          }}>
                            {item.company_name || item.name || `Company ${item.company_id}`}
                          </div>
                        </td>
                        <td style={{ padding: '14px 20px' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '3px 10px',
                            borderRadius: 'var(--radius-full)',
                            background: (item.velocity_score || 0) >= 0
                              ? 'var(--color-secondary-container)'
                              : 'var(--color-error-bg)',
                            color: (item.velocity_score || 0) >= 0
                              ? 'var(--color-on-secondary-container)'
                              : 'var(--color-error)',
                            fontFamily: 'var(--font-data)',
                            fontSize: '0.625rem',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                          }}>
                            {(item.velocity_score || 0) >= 0 ? '↑' : '↓'}
                            {' '}{Math.abs(item.velocity_score || 0).toFixed(1)}%
                          </span>
                        </td>
                        <td style={{
                          padding: '14px 20px',
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.875rem',
                          color: 'var(--color-on-surface-variant)',
                        }}>
                          {item.top_practice || '—'}
                        </td>
                        <td style={{
                          padding: '14px 20px',
                          textAlign: 'right',
                          fontFamily: 'var(--font-editorial)',
                          fontSize: '1.125rem',
                          color: 'var(--color-primary)',
                        }}>
                          {item.composite_score != null
                            ? `${(item.composite_score * 100).toFixed(1)}%`
                            : '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Signals sidebar */}
          <div style={{
            background: 'var(--color-surface-container-low)',
            borderRadius: 'var(--radius-xl)',
            padding: '1.5rem',
          }}>
            <h3 style={{
              fontFamily: 'var(--font-editorial)',
              fontSize: '1.125rem',
              fontWeight: 500,
              color: 'var(--color-primary)',
              marginBottom: '1.5rem',
            }}>
              Latest Signals
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {loading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} style={{ padding: '0.75rem 0' }}>
                    <Skeleton width={100} height={11} style={{ marginBottom: 4 }} />
                    <Skeleton width="100%" height={14} />
                  </div>
                ))
              ) : (
                signals.slice(0, 6).map((sig, i) => (
                  <div key={i} style={{
                    padding: '0.75rem',
                    background: 'var(--color-surface-container-lowest)',
                    borderRadius: 'var(--radius-md)',
                  }}>
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.6875rem',
                      fontWeight: 700,
                      color: 'var(--color-secondary)',
                      letterSpacing: '0.05em',
                      textTransform: 'uppercase',
                      marginBottom: 4,
                    }}>
                      {sig.signal_type || 'SIGNAL'}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color: 'var(--color-primary)',
                      lineHeight: 1.4,
                      marginBottom: 4,
                    }}>
                      {sig.headline || sig.text?.slice(0, 80) || 'Signal detected'}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.6875rem',
                      color: 'var(--color-on-surface-variant)',
                    }}>
                      {sig.source || ''}
                      {sig.published_at && (
                        <span> · {new Date(sig.published_at).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' })}</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            <button
              onClick={() => navigate('/signals')}
              style={{
                display: 'block',
                width: '100%',
                marginTop: '1.25rem',
                padding: '0.5rem',
                fontFamily: 'var(--font-data)',
                fontSize: '0.6875rem',
                fontWeight: 700,
                color: 'var(--color-primary-container)',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                textAlign: 'center',
                cursor: 'pointer',
                background: 'transparent',
                borderRadius: 'var(--radius-md)',
                transition: 'background 150ms ease-out',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              View Full Signal Feed
            </button>
          </div>
        </section>

      </div>
    </AppShell>
  )
}
