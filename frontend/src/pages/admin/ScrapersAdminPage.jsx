/**
 * pages/admin/ScrapersAdminPage.jsx — Admin UI Update
 * Digital Atelier scraper health dashboard.
 * Applied injected CSS with strict DM formatting.
 */

import { useEffect, useState } from 'react'
import AppShell from '../../components/layout/AppShell'
import { Skeleton } from '../../components/Skeleton'

const POLL_INTERVAL = 60_000

const SADMIN_CSS = `
.sadm-root {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.sadm-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 12px;
}
.sadm-title {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 1.75rem;
  color: var(--color-primary);
  margin: 0;
  letter-spacing: -0.01em;
}
.sadm-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.sadm-updated {
  font-size: 0.6875rem;
  color: var(--color-on-surface-variant);
  font-family: var(--font-mono);
}
.sadm-btn-refresh {
  padding: 6px 14px;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-high);
  color: var(--color-on-surface-variant);
  font-size: 0.6875rem;
  font-weight: 700;
  cursor: pointer;
  font-family: var(--font-data);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border: none;
  transition: background var(--transition-fast);
}
.sadm-btn-refresh:hover {
  background: var(--color-outline-variant);
}

.sadm-badges {
  display: flex;
  gap: 12px;
  margin-bottom: 1.75rem;
  flex-wrap: wrap;
}
.sadm-badge-card {
  padding: 10px 20px;
  border-radius: var(--radius-xl);
  text-align: center;
  box-shadow: var(--shadow-ambient);
  flex: 1;
  min-width: 120px;
}
.sadm-badge-val {
  font-family: var(--font-editorial);
  font-size: 1.5rem;
  font-weight: 500;
  letter-spacing: -0.01em;
}
.sadm-badge-label {
  font-size: 0.6875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 2px;
  font-family: var(--font-data);
}

.sadm-error {
  color: var(--color-error);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 0.8125rem;
  margin-bottom: 1rem;
  font-family: var(--font-data);
}

.sadm-card {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-ambient);
}
.sadm-table {
  width: 100%;
  border-collapse: collapse;
}
.sadm-th {
  padding: 10px 14px;
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-align: left;
  background: var(--color-surface-container-low);
  font-family: var(--font-data);
  white-space: nowrap;
}
.sadm-tr {
  transition: background var(--transition-fast);
}
.sadm-td {
  padding: 9px 14px;
  font-size: 0.75rem;
  color: var(--color-on-surface-variant);
  white-space: nowrap;
}
.sadm-td-primary {
  font-family: var(--font-mono);
  color: var(--color-on-surface);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sadm-td-mono {
  font-family: var(--font-mono);
}
.sadm-tag {
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-family: var(--font-data);
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('sadm-styles')) {
    const el = document.createElement('style')
    el.id = 'sadm-styles'
    el.textContent = SADMIN_CSS
    document.head.appendChild(el)
  }
}

function StatusDot({ isHealthy, failures }) {
  const color = !isHealthy || failures >= 3 ? 'var(--color-error)'
    : failures >= 1 ? 'var(--color-warning)'
    : 'var(--color-success)'
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8,
      borderRadius: '50%', background: color, marginRight: 8,
      boxShadow: \`0 0 4px \${color}\`,
    }} />
  )
}

function formatDuration(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return \`\${seconds.toFixed(1)}s\`
  return \`\${(seconds / 60).toFixed(1)}m\`
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-CA', { dateStyle: 'short', timeStyle: 'short' })
}

export function ScrapersAdminPage() {
  injectCSS()
  const [scrapers, setScrapers] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)

  const loadScrapers = async () => {
    try {
      const res = await fetch('/api/scrapers/health', {
        headers: { Authorization: \`Bearer \${sessionStorage.getItem('bdforlaw_token')}\` },
      })
      if (!res.ok) throw new Error(\`\${res.status}\`)
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

  return (
    <AppShell>
      <div className="sadm-root">
        <div className="sadm-header">
          <h1 className="sadm-title">Scraper Health</h1>
          <div className="sadm-actions">
            {lastRefresh && (
              <span className="sadm-updated">Updated {lastRefresh.toLocaleTimeString('en-CA', { timeStyle: 'short' })}</span>
            )}
            <button onClick={loadScrapers} className="sadm-btn-refresh">Refresh</button>
          </div>
        </div>

        <div className="sadm-badges">
          {[
            { label: 'Healthy', count: healthy, color: 'var(--color-success)', bg: 'var(--color-success-bg)' },
            { label: 'Degraded', count: degraded, color: 'var(--color-warning)', bg: 'var(--color-warning-bg)' },
            { label: 'Failing', count: failing, color: 'var(--color-error)', bg: 'var(--color-error-bg)' },
          ].map(({ label, count, color, bg }) => (
            <div key={label} className="sadm-badge-card" style={{ background: bg }}>
              <div className="sadm-badge-val" style={{ color }}>{count}</div>
              <div className="sadm-badge-label" style={{ color }}>{label}</div>
            </div>
          ))}
        </div>

        {error && <div className="sadm-error">Failed to load scraper health: {error}</div>}

        <div className="sadm-card">
          {loading ? (
            <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} height={36} />)}
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="sadm-table">
                <thead>
                  <tr>
                    <th className="sadm-th">Source</th>
                    <th className="sadm-th" style={{ textAlign: 'center' }}>Status</th>
                    <th className="sadm-th">Last Run</th>
                    <th className="sadm-th">Last Success</th>
                    <th className="sadm-th" style={{ textAlign: 'right' }}>Records / Run</th>
                    <th className="sadm-th" style={{ textAlign: 'right' }}>Avg Duration</th>
                    <th className="sadm-th" style={{ textAlign: 'right' }}>Reliability</th>
                    <th className="sadm-th" style={{ textAlign: 'center' }}>Circuit</th>
                  </tr>
                </thead>
                <tbody>
                  {scrapers.map((s, i) => (
                    <tr key={s.source_id} className="sadm-tr" style={{ background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-container-low)' }}>
                      <td className="sadm-td sadm-td-primary">
                        <StatusDot isHealthy={s.is_healthy} failures={s.consecutive_failures} />
                        {s.source_id}
                      </td>
                      <td className="sadm-td" style={{ textAlign: 'center' }}>
                        <span className="sadm-tag" style={{
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
                      <td className="sadm-td sadm-td-mono">{formatDate(s.last_run_at)}</td>
                      <td className="sadm-td sadm-td-mono">{formatDate(s.last_success_at)}</td>
                      <td className="sadm-td sadm-td-mono" style={{ textAlign: 'right', color: 'var(--color-on-surface)' }}>{s.avg_records_per_run?.toFixed(0) ?? '—'}</td>
                      <td className="sadm-td sadm-td-mono" style={{ textAlign: 'right', color: 'var(--color-on-surface)' }}>{formatDuration(s.avg_duration_seconds)}</td>
                      <td className="sadm-td sadm-td-mono" style={{ textAlign: 'right', color: s.reliability_score >= 0.8 ? 'var(--color-success)' : s.reliability_score >= 0.5 ? 'var(--color-warning)' : 'var(--color-error)' }}>
                        {s.reliability_score != null ? \`\${(s.reliability_score * 100).toFixed(0)}%\` : '—'}
                      </td>
                      <td className="sadm-td sadm-td-mono" style={{ textAlign: 'center', color: s.circuit_breaker_state === 'open' ? 'var(--color-error)' : 'var(--color-on-surface-variant)' }}>
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
