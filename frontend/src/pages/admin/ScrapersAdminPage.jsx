/**
 * pages/admin/ScrapersAdminPage.jsx — ConstructLex Pro scraper health dashboard.
 */

import { useEffect, useState } from 'react'
import AppShell from '../../components/layout/AppShell'
import { Skeleton } from '../../components/Skeleton'

const POLL_INTERVAL = 60_000  // 60 seconds

function StatusDot({ isHealthy, failures }) {
  const color = !isHealthy || failures >= 3 ? 'var(--error)'
    : failures >= 1 ? 'var(--warning)'
    : 'var(--success)'
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
      const res = await fetch('/api/v1/scrapers/health', {
        headers: { Authorization: `Bearer ${sessionStorage.getItem('oracle_token')}` },
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
    padding: '9px 14px', fontSize: 10, fontWeight: 600,
    color: 'var(--text-tertiary)', textTransform: 'uppercase',
    letterSpacing: '0.08em', textAlign: 'left',
    background: 'var(--surface-raised)', border: 'none',
    borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap',
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: 12 }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 30, color: 'var(--text)', margin: 0 }}>
            Scraper Health
          </h1>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {lastRefresh && (
              <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                Updated {lastRefresh.toLocaleTimeString('en-CA', { timeStyle: 'short' })}
              </span>
            )}
            <button onClick={loadScrapers} style={{ padding: '6px 14px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', background: 'var(--surface)', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font-body)' }}>
              Refresh
            </button>
          </div>
        </div>

        {/* Summary badges */}
        <div style={{ display: 'flex', gap: 12, marginBottom: '1.75rem', flexWrap: 'wrap' }}>
          {[
            { label: 'Healthy', count: healthy, color: 'var(--success)', bg: 'var(--success-bg)' },
            { label: 'Degraded', count: degraded, color: 'var(--warning)', bg: 'var(--warning-bg)' },
            { label: 'Failing', count: failing, color: 'var(--error)', bg: 'var(--error-bg)' },
          ].map(({ label, count, color, bg }) => (
            <div key={label} style={{
              padding: '10px 20px', borderRadius: 'var(--radius-md)',
              background: bg, border: `1px solid ${color}44`,
              textAlign: 'center',
            }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color }}>{count}</div>
              <div style={{ fontSize: 10, color, textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>

        {error && (
          <div style={{ color: 'var(--error)', background: 'var(--error-bg)', border: '1px solid var(--error)', borderRadius: 'var(--radius-md)', padding: '10px 14px', fontSize: 13, marginBottom: '1rem' }}>
            Failed to load scraper health: {error}
          </div>
        )}

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
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
                    <tr key={s.source_id} style={{ borderBottom: '1px solid var(--surface-raised)', background: i % 2 === 0 ? 'transparent' : 'var(--surface-raised)' }}>
                      <td style={{ padding: '9px 14px', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text)', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        <StatusDot isHealthy={s.is_healthy} failures={s.consecutive_failures} />
                        {s.source_id}
                      </td>
                      <td style={{ padding: '9px 14px', textAlign: 'center' }}>
                        <span style={{
                          fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                          ...(!s.is_healthy || s.consecutive_failures >= 3
                            ? { background: 'var(--error-bg)', color: 'var(--error)' }
                            : s.consecutive_failures >= 1
                            ? { background: 'var(--warning-bg)', color: 'var(--warning)' }
                            : { background: 'var(--success-bg)', color: 'var(--success)' })
                        }}>
                          {!s.is_healthy || s.consecutive_failures >= 3 ? 'FAILING'
                            : s.consecutive_failures >= 1 ? 'DEGRADED'
                            : 'HEALTHY'}
                        </span>
                      </td>
                      <td style={{ padding: '9px 14px', fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>{formatDate(s.last_run_at)}</td>
                      <td style={{ padding: '9px 14px', fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>{formatDate(s.last_success_at)}</td>
                      <td style={{ padding: '9px 14px', textAlign: 'right', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text)' }}>{s.avg_records_per_run?.toFixed(0) ?? '—'}</td>
                      <td style={{ padding: '9px 14px', textAlign: 'right', fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text)' }}>{formatDuration(s.avg_duration_seconds)}</td>
                      <td style={{ padding: '9px 14px', textAlign: 'right', fontSize: 12, fontFamily: 'var(--font-mono)', color: s.reliability_score >= 0.8 ? 'var(--success)' : s.reliability_score >= 0.5 ? 'var(--warning)' : 'var(--error)' }}>
                        {s.reliability_score != null ? `${(s.reliability_score * 100).toFixed(0)}%` : '—'}
                      </td>
                      <td style={{ padding: '9px 14px', textAlign: 'center', fontSize: 10, fontFamily: 'var(--font-mono)', color: s.circuit_breaker_state === 'open' ? 'var(--error)' : 'var(--text-tertiary)' }}>
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
