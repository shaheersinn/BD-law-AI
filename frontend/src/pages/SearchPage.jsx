/**
 * pages/SearchPage.jsx — Fuzzy company name search.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { companies as companiesApi } from '../api/client'

const S = {
  page:  { minHeight: '100vh', background: '#F8F7F4', fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif' },
  main:  { maxWidth: 700, margin: '0 auto', padding: '3rem 1.5rem' },
  h1:    { fontSize: '1.5rem', fontWeight: 700, color: '#111827', marginBottom: '0.25rem' },
  sub:   { color: '#6b7280', fontSize: '0.875rem', marginBottom: '2rem' },
  row:   { display: 'flex', gap: 10, marginBottom: '1.5rem' },
  input: { flex: 1, padding: '10px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: '0.9rem', outline: 'none' },
  btn:   { padding: '10px 20px', background: 'linear-gradient(135deg,#0C9182,#059669)', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', fontSize: '0.875rem' },
  result:{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden' },
  item:  { display: 'flex', alignItems: 'center', padding: '14px 18px', borderBottom: '1px solid #f3f4f6', cursor: 'pointer', gap: 10 },
  name:  { fontWeight: 600, color: '#111827', fontSize: '0.9rem' },
  alias: { fontSize: '0.78rem', color: '#9ca3af' },
  score: { marginLeft: 'auto', fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace', color: '#0C9182', background: '#ecfdf5', padding: '2px 8px', borderRadius: 4 },
  back:  { color: '#6b7280', fontSize: '0.875rem', textDecoration: 'none', display: 'inline-block', marginBottom: '1rem' },
}

export default function SearchPage() {
  const navigate = useNavigate()
  const [q, setQ]           = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (q.trim().length < 2) return
    setLoading(true)
    setError(null)
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
    <div style={S.page}>
      <main style={S.main}>
        <a href="/dashboard" style={S.back}>← Dashboard</a>
        <h1 style={S.h1}>Search Companies</h1>
        <p style={S.sub}>Find a company to view its mandate probability scores</p>

        <form onSubmit={handleSearch} style={S.row}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. Shopify, Rogers, CIBC…"
            autoFocus
            style={S.input}
          />
          <button type="submit" disabled={loading || q.trim().length < 2} style={S.btn}>
            {loading ? '…' : 'Search'}
          </button>
        </form>

        {error && (
          <p style={{ color: '#ef4444', fontSize: '0.875rem', marginBottom: 12 }}>{error}</p>
        )}

        {results !== null && (
          results.length === 0 ? (
            <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No matches found for "{q}".</p>
          ) : (
            <div style={S.result}>
              {results.map((r) => (
                <div
                  key={r.company_id}
                  style={S.item}
                  onClick={() => navigate(`/companies/${r.company_id}`)}
                >
                  <div>
                    <div style={S.name}>{r.name}</div>
                    {r.matched_alias !== r.name && (
                      <div style={S.alias}>Matched: {r.matched_alias}</div>
                    )}
                  </div>
                  <span style={S.score}>{(r.score * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          )
        )}
      </main>
    </div>
  )
}
