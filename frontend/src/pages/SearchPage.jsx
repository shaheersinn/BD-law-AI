/**
 * pages/SearchPage.jsx — ConstructLex Pro company search.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { companies as companiesApi } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'

export default function SearchPage() {
  const navigate = useNavigate()
  const [q, setQ]             = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (q.trim().length < 2) return
    setLoading(true); setError(null)
    try {
      const data = await companiesApi.search(q.trim(), 15)
      setResults(data)
    } catch (err) {
      setError(err.message || 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 700, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 700, fontSize: 30,
          color: 'var(--text)', marginBottom: 6,
        }}>
          Search Companies
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: '2rem', margin: '0 0 2rem' }}>
          Find a company to view its 34×3 mandate probability matrix
        </p>

        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, marginBottom: '1.5rem' }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. Shopify, Rogers, CIBC…"
            autoFocus
            style={{
              flex: 1, padding: '10px 16px',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              fontSize: 14, color: 'var(--text)',
              background: 'var(--surface)',
              outline: 'none',
              fontFamily: 'var(--font-body)',
              boxShadow: 'var(--shadow-sm)',
              transition: 'border-color var(--transition)',
            }}
            onFocus={e => e.target.style.borderColor = 'var(--accent)'}
            onBlur={e  => e.target.style.borderColor = 'var(--border)'}
          />
          <button
            type="submit"
            disabled={loading || q.trim().length < 2}
            style={{
              padding: '10px 22px',
              background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
              color: '#fff', border: 'none',
              borderRadius: 'var(--radius-md)',
              fontWeight: 700, cursor: loading ? 'default' : 'pointer',
              fontSize: 13, fontFamily: 'var(--font-body)',
              opacity: q.trim().length < 2 ? 0.5 : 1,
              transition: 'opacity var(--transition)',
              whiteSpace: 'nowrap',
            }}
          >
            {loading ? '…' : 'Search'}
          </button>
        </form>

        {error && (
          <div style={{
            color: 'var(--error)', fontSize: 13,
            background: 'var(--error-bg)', border: '1px solid var(--error)',
            borderRadius: 'var(--radius-md)', padding: '10px 14px', marginBottom: 16,
          }}>
            {error}
          </div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)', overflow: 'hidden',
          }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{
                padding: '14px 18px',
                borderBottom: i < 4 ? '1px solid var(--surface-raised)' : 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}>
                <div>
                  <Skeleton width={180} height={14} style={{ marginBottom: 6 }} />
                  <Skeleton width={120} height={11} />
                </div>
                <Skeleton width={36} height={20} />
              </div>
            ))}
          </div>
        )}

        {/* Results */}
        {!loading && results !== null && (
          results.length === 0 ? (
            <div style={{
              padding: '3rem 2rem', textAlign: 'center',
              color: 'var(--text-tertiary)',
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
            }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>🔍</div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>No matches for "{q}"</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Try a different name or ticker symbol.</div>
            </div>
          ) : (
            <div style={{
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)', overflow: 'hidden',
              boxShadow: 'var(--shadow-sm)',
            }}>
              {results.map((r, i) => (
                <div
                  key={r.company_id}
                  onClick={() => navigate(`/companies/${r.company_id}`)}
                  style={{
                    display: 'flex', alignItems: 'center',
                    padding: '14px 18px', cursor: 'pointer', gap: 12,
                    borderBottom: i < results.length - 1 ? '1px solid var(--surface-raised)' : 'none',
                    transition: 'background var(--transition)',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {r.name}
                    </div>
                    {r.matched_alias !== r.name && (
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>
                        Matched: {r.matched_alias}
                      </div>
                    )}
                  </div>
                  <span style={{
                    fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 600,
                    color: 'var(--accent)', background: 'var(--accent-light)',
                    padding: '3px 8px', borderRadius: 999, flexShrink: 0,
                    border: '1px solid var(--accent-light)',
                  }}>
                    {(r.score * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </AppShell>
  )
}
