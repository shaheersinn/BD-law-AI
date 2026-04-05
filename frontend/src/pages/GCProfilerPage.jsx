/**
 * pages/GCProfilerPage.jsx — P13 Redesign
 * 
 * General Counsel and CLO profiles with relationship mapping and tenure tracking.
 * DM Serif Display + DM Sans, no inline styles.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, Search } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { clients } from '../api/client'

const GC_CSS = `
.gc-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.gc-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}

/* Search */
.gc-search-wrap {
  position: relative;
  margin-bottom: 1.5rem;
}
.gc-search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-on-surface-variant);
  pointer-events: none;
}
.gc-search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-surface-container-high);
  background: var(--color-surface-container-low);
  font-family: var(--font-data);
  font-size: 0.875rem;
  color: var(--color-on-surface);
  outline: none;
  transition: border-color var(--transition-fast);
}
.gc-search-input:focus { border-color: var(--color-secondary); }

/* Table */
.gc-table {
  width: 100%;
  border-collapse: collapse;
}
.gc-th {
  padding: 9px 12px;
  text-align: left;
  font-family: var(--font-data);
  font-weight: 700;
  font-size: 0.625rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-on-surface-variant);
  background: var(--color-surface-container-low);
  white-space: nowrap;
}
.gc-tr {
  transition: background var(--transition-fast);
}
.gc-tr:nth-child(even) { background: var(--color-surface-container-low); }
.gc-tr:hover { background: var(--color-surface-container-high) !important; }

.gc-td {
  padding: 13px 12px;
  white-space: nowrap;
}
.gc-td-name {
  font-family: var(--font-editorial);
  font-size: 1.05rem;
  font-weight: 400;
  color: var(--color-primary);
}
.gc-td-meta {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.gc-td-mono {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--color-on-surface);
}

.gc-btn-view {
  padding: 6px 14px;
  border-radius: var(--radius-md);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: 1px solid var(--color-secondary);
  background: transparent;
  color: var(--color-secondary);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.gc-btn-view:hover:not(:disabled) {
  background: var(--color-secondary);
  color: #fff;
}
.gc-btn-view:disabled {
  border-color: var(--color-surface-container-high);
  color: var(--color-on-surface-variant);
  cursor: default;
}

@media (max-width: 980px) {
  .gc-metrics { grid-template-columns: 1fr; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('gc-styles')) {
    const el = document.createElement('style')
    el.id = 'gc-styles'
    el.textContent = GC_CSS
    document.head.appendChild(el)
  }
}

function relationshipColor(status) {
  if (!status) return 'default'
  const s = status.toLowerCase()
  if (s === 'active') return 'green'
  if (s === 'warm') return 'gold'
  if (s === 'cold') return 'default'
  return 'default'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d)) return dateStr
  return d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}

function avgTenure(data) {
  const vals = data.map(d => Number(d.tenure_years ?? d.tenure ?? 0)).filter(v => !isNaN(v) && v > 0)
  if (!vals.length) return '—'
  return \`\${(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1)}y\`
}

export default function GCProfilerPage() {
  injectCSS()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    clients.list()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load GC directory'))
      .finally(() => setLoading(false))
  }, [])

  const handleRetry = () => {
    setError(null)
    setLoading(true)
    clients.list()
      .then(r => setData(r || []))
      .catch(err => setError(err.message || 'Failed to load GC directory'))
      .finally(() => setLoading(false))
  }

  const activeCount = useMemo(() =>
    data.filter(c => c.relationship_status?.toLowerCase() === 'active').length,
    [data]
  )

  const filtered = useMemo(() => {
    if (!query.trim()) return data
    const q = query.toLowerCase()
    return data.filter(c =>
      (c.name ?? c.contact_name ?? '').toLowerCase().includes(q) ||
      (c.company_name ?? c.company ?? '').toLowerCase().includes(q)
    )
  }, [data, query])

  if (error) {
    return (
      <AppShell>
        <div style={{ padding: '2rem' }}>
          <ErrorState message={error} onRetry={handleRetry} />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="gc-root">
        <PageHeader
          tag="Relationship Intelligence"
          title="GC Profiler"
          subtitle="General Counsel and CLO profiles with relationship mapping and tenure tracking"
        />

        {/* Metric cards */}
        <div className="gc-metrics">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={100} radius={12} />)
          ) : (
            <>
              <MetricCard label="Total GCs" value={data.length} sub="in directory" accent="navy" />
              <MetricCard label="Active Relationships" value={activeCount} sub="currently engaged" accent="teal" />
              <MetricCard label="Avg Tenure" value={avgTenure(data)} sub="years in role" accent="gold" />
            </>
          )}
        </div>

        {/* GC/CLO Directory */}
        <Panel title="GC / CLO Directory">
          {/* Search input */}
          <div className="gc-search-wrap">
            <Search size={14} className="gc-search-icon" />
            <input
              type="text"
              placeholder="Search by name or company…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              className="gc-search-input"
            />
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} height={44} radius={6} style={{ opacity: 1 - i * 0.08 }} />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={<Users size={32} />}
              title={query ? 'No matches found' : 'No GC profiles available'}
              message={query ? \`No results for "\${query}"\` : 'GC/CLO profiles will populate as client data is collected'}
            />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="gc-table">
                <thead>
                  <tr>
                    {['Name', 'Company', 'Title', 'Tenure', 'Last Contact', 'Relationship', 'Action'].map(h => (
                      <th key={h} className="gc-th">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((gc, i) => (
                    <tr key={gc.id ?? gc.contact_id ?? i} className="gc-tr">
                      <td className="gc-td gc-td-name">{gc.name ?? gc.contact_name ?? '—'}</td>
                      <td className="gc-td gc-td-meta">{gc.company_name ?? gc.company ?? '—'}</td>
                      <td className="gc-td gc-td-meta">{gc.title ?? gc.role ?? 'General Counsel'}</td>
                      <td className="gc-td gc-td-mono">{gc.tenure_years != null ? \`\${gc.tenure_years}y\` : gc.tenure ?? '—'}</td>
                      <td className="gc-td gc-td-meta">{formatDate(gc.last_contact ?? gc.last_contact_date)}</td>
                      <td className="gc-td">
                        <Tag
                          label={gc.relationship_status ?? 'Unknown'}
                          color={relationshipColor(gc.relationship_status)}
                        />
                      </td>
                      <td className="gc-td">
                        <button
                          onClick={() => gc.company_id && navigate(\`/companies/\${gc.company_id}\`)}
                          disabled={!gc.company_id}
                          className="gc-btn-view"
                        >
                          View Profile
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </AppShell>
  )
}
