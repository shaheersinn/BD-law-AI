/**
 * pages/admin/ScrapersAdminPage.jsx — Scraper health dashboard (admin only).
 */

import { useEffect, useState } from 'react'

const API_URL = '/api/v1/scrapers/health'

const S = {
  page:  { minHeight: '100vh', background: '#F8F7F4', fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif' },
  main:  { maxWidth: 1100, margin: '0 auto', padding: '2rem 1.5rem' },
  back:  { color: '#6b7280', fontSize: '0.875rem', textDecoration: 'none', display: 'inline-block', marginBottom: '1.25rem' },
  h1:    { fontSize: '1.4rem', fontWeight: 700, color: '#111827', marginBottom: '1.5rem' },
  table: { width: '100%', background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, borderCollapse: 'collapse', overflow: 'hidden' },
  th:    { padding: '10px 14px', textAlign: 'left', fontSize: '0.75rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', borderBottom: '1px solid #e5e7eb', background: '#f9fafb' },
  td:    { padding: '10px 14px', fontSize: '0.85rem', color: '#374151', borderBottom: '1px solid #f3f4f6' },
}

function HealthBadge({ healthy }) {
  return (
    <span style={{
      fontSize: '0.75rem',
      fontWeight: 600,
      padding: '2px 8px',
      borderRadius: 999,
      background: healthy ? '#d1fae5' : '#fee2e2',
      color: healthy ? '#065f46' : '#991b1b',
    }}>
      {healthy ? 'Healthy' : 'Unhealthy'}
    </span>
  )
}

export default function ScrapersAdminPage() {
  const [scrapers, setScrapers] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  useEffect(() => {
    const token = sessionStorage.getItem('bdforlaw_token')
    fetch(API_URL, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.json())
      .then((data) => setScrapers(Array.isArray(data) ? data : data.scrapers || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={S.page}>
      <main style={S.main}>
        <a href="/dashboard" style={S.back}>← Dashboard</a>
        <h1 style={S.h1}>Scraper Health</h1>

        {loading && <p style={{ color: '#9ca3af' }}>Loading…</p>}
        {error   && <p style={{ color: '#ef4444' }}>Error: {error}</p>}

        {!loading && !error && (
          <table style={S.table}>
            <thead>
              <tr>
                {['Source', 'Status', 'Last Success', 'Failures', 'Reliability'].map((h) => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scrapers.length === 0 ? (
                <tr><td colSpan={5} style={{ ...S.td, textAlign: 'center', color: '#9ca3af' }}>No data</td></tr>
              ) : (
                scrapers.map((s, i) => (
                  <tr key={i}>
                    <td style={S.td}>{s.source_name || s.source_id}</td>
                    <td style={S.td}><HealthBadge healthy={s.is_healthy} /></td>
                    <td style={S.td}>{s.last_success_at ? new Date(s.last_success_at).toLocaleString() : '—'}</td>
                    <td style={{ ...S.td, color: s.total_failures > 5 ? '#dc2626' : '#374151' }}>{s.total_failures}</td>
                    <td style={S.td}>{(s.reliability_score * 100).toFixed(0)}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </main>
    </div>
  )
}
