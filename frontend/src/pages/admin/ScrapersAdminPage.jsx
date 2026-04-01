/**
 * pages/admin/ScrapersAdminPage.jsx — Digital Atelier scraper health dashboard.
 */

import { useEffect, useState } from 'react'
import AppShell from '../../components/layout/AppShell'
import { Skeleton } from '../../components/Skeleton'

const POLL_INTERVAL = 60_000  // 60 seconds

function StatusDot({ isHealthy, failures }) {
  const color = !isHealthy || failures >= 3 ? 'var(--color-error)'
    : failures >= 1 ? 'var(--color-warning)'
    : 'var(--color-success)'
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8,
      borderRadius: '50%', background: color, marginRight: 8,
      boxShadow: `0 0 4px ${color}`,
    }} />
  )
}

function formatDuration(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  return `${(seconds / 60).toFixed(1)}m`
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-CA', { dateStyle: 'short', timeStyle: 'short' })
}

export function ScrapersAdminPage() {
  const [scrapers, setScrapers] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)

  const loadScrapers = async () => {
    try {
      const res = await fetch('/api/scrapers/health', {
        headers: { Authorization: `Bearer ${sessionStorage.getItem('bdforlaw_token')}` },
      })
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      setScrapers(Array.isArray(data) ? data : data.scrapers || [])
      setLastRefresh(new Date())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadScrapers()
    const timer = setInterval(loadScrapers, POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [])

  const healthy   = scrapers.filter(s => s.is_healthy && s.consecutive_failures < 1).length
  const degraded  = scrapers.filter(s => s.consecutive_failures >= 1 && s.consecutive_failures < 3).length
  const failing   = scrapers.filter(s => !s.is_healthy || s.consecutive_failures >= 3).length

  const thStyle = {
    padding: '10px 14px',
    fontSize: '0.6875rem',
    fontWeight: 700,
    color: 'var(--color-on-surface-variant)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    textAlign: 'left',
    background: 'var(--color-surface-container-low)',
    fontFamily: 'var(--font-data)',
    whiteSpace: 'nowrap',
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: 12 }}>
          <h1 style={{
            fontFamily: 'var(--font-editorial)',
            fontWeight: 500,
            fontSize: '1.75rem',
            color: 'var(--color-primary)',
            margin: 0,
            letterSpacing: '-0.01em',
          }}>
            Scraper Health
          </h1>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {lastRefresh && (
              <span style={{ fontSize: 11, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-mono)' }}>
                Updated {lastRefresh.toLocaleTimeString('en-CA', { timeStyle: 'short' })}
              </span>
            )}
            <button onClick={loadScrapers} style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-surface-container-high)',
              color: 'var(--color-on-surface-variant)',
              fontSize: '0.6875rem',
              fontWeight: 700,
              cursor: 'pointer',
              fontFamily: 'var(--font-data)',
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
            }}>
              Refresh
            </button>
          </div>
        </div>

        {/* Summary badges */}
        <div style={{ display: 'flex', gap: 12, marginBottom: '1.75rem', flexWrap: 'wrap' }}>
          {[
            { label: 'Healthy', count: healthy, color: 'var(--color-success)', bg: 'var(--color-success-bg)' },
            { label: 'Degraded', count: degraded, color: 'var(--color-warning)', bg: 'var(--color-warning-bg)' },
            { label: 'Failing', count: failing, color: 'var(--color-error)', bg: 'var(--color-error-bg)' },
          ].map(({ label, count, color, bg }) => (
            <div key={label} style={{
              padding: '10px 20px', borderRadius: 'var(--radius-xl)',
              background: bg,
              textAlign: 'center',
              boxShadow: 'var(--shadow-ambient)',
            }}>
              <div style={{ fontFamily: 'var(--font-editorial)', fontSize: '1.5rem', fontWeight: 500, color, letterSpacing: '-0.01em' }}>{count}</div>
              <div style={{ fontSize: '0.6875rem', fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 2, fontFamily: 'var(--font-data)' }}>{label}</div>
            </div>
          ))}
        </div>

        {error && (
          <div style={{
            color: 'var(--color-error)',
            background: 'var(--color-error-bg)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            fontSize: 13,
            marginBottom: '1rem',
            fontFamily: 'var(--font-data)',
          }}>
            Failed to load scraper health: {error}
          </div>
        )}

        <div style={{
          background: 'var(--color-surface-container-lowest)',
          borderRadius: 'var(--radius-xl)',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-ambient)',
        }}>
          {loading ? (
            <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={36} />)}
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ ...thStyle }}>Source</th>
                    <th style={{ ...thStyle, textAlign: 'center' }}>Status</th>
                    <th style={{ ...thStyle }}>Last Run</th>
                    <th style={{ ...thStyle }}>Last Success</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Records / Run</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Avg Duration</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Reliability</th>
                    <th style={{ ...thStyle, textAlign: 'center' }}>Circuit</th>
                  </tr>
                </thead>
                <tbody>
                  {scrapers.map((s, i) => (
                    <tr key={s.source_id} style={{
                      background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-container-low)',
                    }}>
                      <td style={{ padding: '9px 14px', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--color-on-surface)', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        <StatusDot isHealthy={s.is_healthy} failures={s.consecutive_failures} />
                        {s.source_id}
                      </td>
                      <td style={{ padding: '9px 14px', textAlign: 'center' }}>
                        <span style={{
                          fontSize: '0.6875rem', fontWeight: 700, padding: '2px 8px',
                          borderRadius: 'var(--radius-full)',
                          fontFamily: 'var(--font-data)',
                          ...(!s.is_healthy || s.consecutive_failures >= 3
                            ? { background: 'var(--color-error-bg)', color: 'var(--color-error)' }
                            : s.consecutive_failures >= 1
                            ? { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' }
                            : { background: 'var(--color-success-bg)', color: 'var(--color-success)' })
                        }}>
                          {!s.is_healthy || s.consecutive_failures >= 3 ? 'FAILING'
                            : s.consecutive_failures >= 1 ? 'DEGRADED'
                            : 'HEALTHY'}
                        </span>
                      </td>
                      <td style={{ padding: '9px 14px', fontSize: 11, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>{formatDate(s.last_run_at)}</td>
                      <td style={{ padding: '9px 14px', fontSize: 11, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>{formatDate(s.last_success_at)}</td>
                      <td style={{ padding: '9px 14px', textAlign: 'right', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--color-on-surface)' }}>{s.avg_records_per_run?.toFixed(0) ?? '—'}</td>
                      <td style={{ padding: '9px 14px', textAlign: 'right', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--color-on-surface)' }}>{formatDuration(s.avg_duration_seconds)}</td>
                      <td style={{ padding: '9px 14px', textAlign: 'right', fontSize: 12, fontFamily: 'var(--font-mono)', color: s.reliability_score >= 0.8 ? 'var(--color-success)' : s.reliability_score >= 0.5 ? 'var(--color-warning)' : 'var(--color-error)' }}>
                        {s.reliability_score != null ? `${(s.reliability_score * 100).toFixed(0)}%` : '—'}
                      </td>
                      <td style={{ padding: '9px 14px', textAlign: 'center', fontSize: '0.6875rem', fontFamily: 'var(--font-mono)', color: s.circuit_breaker_state === 'open' ? 'var(--color-error)' : 'var(--color-on-surface-variant)' }}>
                        {s.circuit_breaker_state || 'closed'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}

export default ScrapersAdminPage
