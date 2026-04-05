/**
 * pages/SearchPage.jsx — P22 Redesign
 * 
 * Digital Atelier company search.
 * Editorial Brief header. Tonal surface result rows. Ghost border input.
 * Now using injected CSS to maintain the DM typography stack strictly.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { companies as companiesApi } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'

const SEARCH_CSS = `
.search-root {
  max-width: 700px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.search-header-tag {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-secondary);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 6px;
  display: block;
}
.search-title {
  font-family: var(--font-editorial);
  font-size: 1.75rem;
  font-weight: 500;
  color: var(--color-primary);
  letter-spacing: -0.01em;
  margin-bottom: 6px;
  margin-top: 0;
}
.search-subtitle {
  font-family: var(--font-data);
  font-size: 0.875rem;
  color: var(--color-on-surface-variant);
  letter-spacing: 0.01em;
  line-height: 1.6;
  margin-bottom: 2rem;
}

.search-form {
  display: flex;
  gap: 10px;
  margin-bottom: 1.5rem;
}
.search-input {
  flex: 1;
  padding: 10px 16px;
  outline: 1px solid rgba(197, 198, 206, 0.15);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: var(--color-on-surface);
  background: var(--color-surface-container-lowest);
  font-family: var(--font-data);
  box-shadow: var(--shadow-ambient);
  transition: outline-color var(--transition-fast);
  border: none;
}
.search-input:focus {
  outline: 1px solid rgba(197, 198, 206, 0.40);
}
.search-btn {
  padding: 10px 22px;
  background: linear-gradient(to bottom, var(--color-primary), var(--color-primary-container));
  color: var(--color-on-primary);
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: 0.8125rem;
  font-family: var(--font-data);
  transition: opacity var(--transition-fast);
  white-space: nowrap;
  border: none;
}
.search-btn:not(:disabled) {
  cursor: pointer;
}
.search-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.search-error {
  color: var(--color-error);
  font-size: 0.8125rem;
  font-family: var(--font-data);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  margin-bottom: 16px;
}

.search-results {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-ambient);
}
.search-result-item {
  display: flex;
  align-items: center;
  padding: 14px 18px;
  cursor: pointer;
  gap: 12px;
  transition: background var(--transition-fast);
}
.search-result-item:hover {
  background: var(--color-surface-container-high) !important;
}
.search-result-primary {
  flex: 1;
  min-width: 0;
}
.search-result-name {
  font-family: var(--font-data);
  font-weight: 600;
  color: var(--color-on-surface);
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.search-result-match {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  color: var(--color-on-surface-variant);
  margin-top: 2px;
}
.search-result-score {
  font-size: 0.6875rem;
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--color-on-secondary-container);
  background: var(--color-secondary-container);
  padding: 3px 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.search-empty {
  padding: 3rem 2rem;
  text-align: center;
  color: var(--color-on-surface-variant);
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-ambient);
}
.search-empty-icon {
  font-size: 28px;
  margin-bottom: 8px;
}
.search-empty-title {
  font-family: var(--font-data);
  font-weight: 600;
  font-size: 0.8125rem;
  color: var(--color-on-surface);
}
.search-empty-text {
  font-family: var(--font-data);
  font-size: 0.75rem;
  margin-top: 4px;
  color: var(--color-on-surface-variant);
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('search-styles')) {
    const el = document.createElement('style')
    el.id = 'search-styles'
    el.textContent = SEARCH_CSS
    document.head.appendChild(el)
  }
}

export default function SearchPage() {
  injectCSS()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

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
      <div className="search-root">
        {/* Editorial header */}
        <div style={{ marginBottom: 6 }}>
          <span className="search-header-tag">Intelligence Search</span>
        </div>
        <h1 className="search-title">Search Companies</h1>
        <p className="search-subtitle">
          Find a company to view its 34×3 mandate probability matrix
        </p>

        {/* Search form */}
        <form onSubmit={handleSearch} className="search-form">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. Shopify, Rogers, CIBC…"
            autoFocus
            className="search-input"
          />
          <button
            type="submit"
            disabled={loading || q.trim().length < 2}
            className="search-btn"
          >
            {loading ? '…' : 'Search'}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="search-error">{error}</div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div className="search-results">
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
            <div className="search-empty">
              <div className="search-empty-icon">🔍</div>
              <div className="search-empty-title">No matches for "{q}"</div>
              <div className="search-empty-text">Try a different name or ticker symbol.</div>
            </div>
          ) : (
            <div className="search-results">
              {results.map((r, i) => (
                <div
                  key={r.company_id}
                  onClick={() => navigate(`/companies/${r.company_id}`)}
                  className="search-result-item"
                  style={{
                    background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent',
                  }}
                >
                  <div className="search-result-primary">
                    <div className="search-result-name">{r.name}</div>
                    {r.matched_alias !== r.name && (
                      <div className="search-result-match">Matched: {r.matched_alias}</div>
                    )}
                  </div>
                  <span className="search-result-score">
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
