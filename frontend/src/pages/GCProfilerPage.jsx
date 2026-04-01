/**
 * pages/GCProfilerPage.jsx — route /gc-profiler
 * General Counsel and CLO profiles with relationship mapping and tenure tracking.
 */

import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, Search } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import { PageHeader, MetricCard, Panel, Tag, EmptyState, ErrorState } from '../components/ui/Primitives'
import { clients } from '../api/client'

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
  return `${(vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1)}y`
}

export default function GCProfilerPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState([])
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [hoveredRow, setHoveredRow] = useState(null)

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
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>
        <PageHeader
          tag="Relationship Intelligence"
          title="GC Profiler"
          subtitle="General Counsel and CLO profiles with relationship mapping and tenure tracking"
        />

        {/* Metric cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
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
          <div style={{ marginBottom: '1rem', position: 'relative' }}>
            <Search
              size={14}
              style={{
                position: 'absolute',
                left: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-on-surface-variant)',
                pointerEvents: 'none',
              }}
            />
            <input
              type="text"
              placeholder="Search by name or company…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              style={{
                width: '100%',
                boxSizing: 'border-box',
                padding: '0.5rem 0.75rem 0.5rem 2.25rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-surface-container-high)',
                background: 'var(--color-surface-container-low)',
                fontFamily: 'var(--font-data)',
                fontSize: '0.875rem',
                color: 'var(--color-on-surface)',
                outline: 'none',
                transition: 'border-color 0.15s',
              }}
              onFocus={e => { e.target.style.borderColor = 'var(--color-secondary)' }}
              onBlur={e => { e.target.style.borderColor = 'var(--color-surface-container-high)' }}
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
              message={query ? `No results for "${query}"` : 'GC/CLO profiles will populate as client data is collected'}
            />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-data)', fontSize: '0.8125rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--color-surface-container-high)' }}>
                    {['Name', 'Company', 'Title', 'Tenure', 'Last Contact', 'Relationship', 'Action'].map(h => (
                      <th key={h} style={{
                        padding: '0.5rem 0.75rem',
                        textAlign: 'left',
                        fontWeight: 700,
                        fontSize: '0.625rem',
                        letterSpacing: '0.05em',
                        textTransform: 'uppercase',
                        color: 'var(--color-on-surface-variant)',
                        whiteSpace: 'nowrap',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((gc, i) => (
                    <tr
                      key={gc.id ?? gc.contact_id ?? i}
                      onMouseEnter={() => setHoveredRow(i)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={{
                        borderBottom: '1px solid var(--color-surface-container-high)',
                        background: hoveredRow === i ? 'var(--color-surface-container-low)' : 'transparent',
                        transition: 'background 0.12s',
                        cursor: 'default',
                      }}
                    >
                      <td style={{ padding: '0.625rem 0.75rem', fontWeight: 600, color: 'var(--color-on-surface)', whiteSpace: 'nowrap' }}>
                        {gc.name ?? gc.contact_name ?? '—'}
                      </td>
                      <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {gc.company_name ?? gc.company ?? '—'}
                      </td>
                      <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {gc.title ?? gc.role ?? 'General Counsel'}
                      </td>
                      <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface)', whiteSpace: 'nowrap' }}>
                        {gc.tenure_years != null ? `${gc.tenure_years}y` : gc.tenure ?? '—'}
                      </td>
                      <td style={{ padding: '0.625rem 0.75rem', color: 'var(--color-on-surface-variant)', whiteSpace: 'nowrap' }}>
                        {formatDate(gc.last_contact ?? gc.last_contact_date)}
                      </td>
                      <td style={{ padding: '0.625rem 0.75rem' }}>
                        <Tag
                          label={gc.relationship_status ?? 'Unknown'}
                          color={relationshipColor(gc.relationship_status)}
                        />
                      </td>
                      <td style={{ padding: '0.625rem 0.75rem' }}>
                        <button
                          onClick={() => gc.company_id && navigate(`/companies/${gc.company_id}`)}
                          disabled={!gc.company_id}
                          style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: 'var(--radius-md)',
                            fontFamily: 'var(--font-data)',
                            fontSize: '0.6875rem',
                            fontWeight: 700,
                            letterSpacing: '0.04em',
                            textTransform: 'uppercase',
                            border: '1px solid var(--color-secondary)',
                            background: 'transparent',
                            color: gc.company_id ? 'var(--color-secondary)' : 'var(--color-on-surface-variant)',
                            borderColor: gc.company_id ? 'var(--color-secondary)' : 'var(--color-surface-container-high)',
                            cursor: gc.company_id ? 'pointer' : 'default',
                            whiteSpace: 'nowrap',
                          }}
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
