/**
 * pages/SearchPage.jsx — Digital Atelier company search.
 * Editorial Brief header. Tonal surface result rows. Ghost border input.
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
        {/* Editorial header */}
        <div style={{ marginBottom: 6 }}>
          <span style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.6875rem',
            fontWeight: 700,
            color: 'var(--color-secondary)',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}>
            Intelligence Search
          </span>
        </div>
        <h1 style={{
          fontFamily: 'var(--font-editorial)',
          fontSize: '1.5rem',
          fontWeight: 500,
          color: 'var(--color-primary)',
          letterSpacing: '-0.01em',
          marginBottom: 6,
        }}>
          Search Companies
        </h1>
        <p style={{
          fontFamily: 'var(--font-data)',
          fontSize: '0.875rem',
          color: 'var(--color-on-surface-variant)',
          letterSpacing: '0.01em',
          lineHeight: 1.6,
          marginBottom: '2rem',
        }}>
          Find a company to view its 34×3 mandate probability matrix
        </p>

        {/* Search form */}
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, marginBottom: '1.5rem' }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. Shopify, Rogers, CIBC…"
            autoFocus
            style={{
              flex: 1, padding: '10px 16px',
              outline: '1px solid rgba(197, 198, 206, 0.15)',
              borderRadius: 'var(--radius-md)',
              fontSize: 14,
              color: 'var(--color-on-surface)',
              background: 'var(--color-surface-container-lowest)',
              fontFamily: 'var(--font-data)',
              boxShadow: 'var(--shadow-ambient)',
              transition: 'outline-color 150ms ease-out',
            }}
            onFocus={e => e.target.style.outline = '1px solid rgba(197, 198, 206, 0.40)'}
            onBlur={e  => e.target.style.outline = '1px solid rgba(197, 198, 206, 0.15)'}
          />
          <button
            type="submit"
            disabled={loading || q.trim().length < 2}
            style={{
              padding: '10px 22px',
              background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
              color: 'var(--color-on-primary)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 700, cursor: loading ? 'default' : 'pointer',
              fontSize: 13, fontFamily: 'var(--font-data)',
              opacity: q.trim().length < 2 ? 0.5 : 1,
              transition: 'opacity 150ms ease-out',
              whiteSpace: 'nowrap',
            }}
          >
            {loading ? '…' : 'Search'}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div style={{
            color: 'var(--color-error)',
            fontSize: 13, fontFamily: 'var(--font-data)',
            background: 'var(--color-error-bg)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            marginBottom: 16,
          }}>
            {error}
          </div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div style={{
            background: 'var(--color-surface-container-lowest)',
            borderRadius: 'var(--radius-xl)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-ambient)',
          }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{
                padding: '14px 18px',
                background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent',
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
              color: 'var(--color-on-surface-variant)',
              background: 'var(--color-surface-container-lowest)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-ambient)',
            }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>🔍</div>
              <div style={{
                fontFamily: 'var(--font-data)',
                fontWeight: 600,
                fontSize: 13,
                color: 'var(--color-on-surface)',
              }}>No matches for "{q}"</div>
              <div style={{
                fontFamily: 'var(--font-data)',
                fontSize: 12,
                marginTop: 4,
                color: 'var(--color-on-surface-variant)',
              }}>Try a different name or ticker symbol.</div>
            </div>
          ) : (
            <div style={{
              background: 'var(--color-surface-container-lowest)',
              borderRadius: 'var(--radius-xl)',
              overflow: 'hidden',
              boxShadow: 'var(--shadow-ambient)',
            }}>
              {results.map((r, i) => (
                <div
                  key={r.company_id}
                  onClick={() => navigate(`/companies/${r.company_id}`)}
                  style={{
                    display: 'flex', alignItems: 'center',
                    padding: '14px 18px', cursor: 'pointer', gap: 12,
                    background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent',
                    transition: 'background 150ms ease-out',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
                  onMouseLeave={e => e.currentTarget.style.background = i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent'}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontFamily: 'var(--font-data)',
                      fontWeight: 600,
                      color: 'var(--color-on-surface)',
                      fontSize: 14,
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {r.name}
                    </div>
                    {r.matched_alias !== r.name && (
                      <div style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: 11,
                        color: 'var(--color-on-surface-variant)',
                        marginTop: 2,
                      }}>
                        Matched: {r.matched_alias}
                      </div>
                    )}
                  </div>
                  <span style={{
                    fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 600,
                    color: 'var(--color-on-secondary-container)',
                    background: 'var(--color-secondary-container)',
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-full)',
                    flexShrink: 0,
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
