/**
 * pages/DashboardPage.jsx — Company list with top scores + trend charts.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { trends as trendsApi } from '../api/client'
import TrendCharts from '../components/TrendCharts'
import useAuthStore from '../stores/auth'

const S = {
  page:    { minHeight: '100vh', background: '#F8F7F4', fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif' },
  nav:     { background: '#fff', borderBottom: '1px solid #e5e7eb', padding: '0 2rem', display: 'flex', alignItems: 'center', height: 56, gap: 16 },
  brand:   { fontWeight: 700, color: '#0C9182', fontSize: '1.1rem', textDecoration: 'none' },
  navLink: { color: '#374151', fontSize: '0.875rem', textDecoration: 'none', fontWeight: 500, padding: '4px 8px', borderRadius: 6 },
  main:    { maxWidth: 1100, margin: '0 auto', padding: '2rem 1.5rem' },
  h1:      { fontSize: '1.5rem', fontWeight: 700, color: '#111827', marginBottom: '0.25rem' },
  sub:     { color: '#6b7280', fontSize: '0.875rem', marginBottom: '1.5rem' },
  card:    { background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.5rem', marginBottom: '1.5rem' },
  cardH:   { fontSize: '1rem', fontWeight: 600, color: '#374151', marginBottom: '1rem' },
  btn:     { padding: '8px 16px', background: 'linear-gradient(135deg,#0C9182,#059669)', color: '#fff', border: 'none', borderRadius: 8, fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer', textDecoration: 'none', display: 'inline-block' },
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [trendData, setTrendData]   = useState([])
  const [trendLoading, setTrendLoading] = useState(true)

  useEffect(() => {
    trendsApi.practiceAreas()
      .then(setTrendData)
      .catch(() => setTrendData([]))
      .finally(() => setTrendLoading(false))
  }, [])

  return (
    <div style={S.page}>
      <nav style={S.nav}>
        <a href="/dashboard" style={S.brand}>ORACLE</a>
        <a href="/search" style={S.navLink}>Search</a>
        <a href="/signals" style={S.navLink}>Signals</a>
        {user?.role === 'admin' && <a href="/admin/scrapers" style={S.navLink}>Admin</a>}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>{user?.email}</span>
          <button onClick={logout} style={{ ...S.btn, background: '#f3f4f6', color: '#374151', fontWeight: 500 }}>
            Sign out
          </button>
        </div>
      </nav>

      <main style={S.main}>
        <h1 style={S.h1}>BD Intelligence Dashboard</h1>
        <p style={S.sub}>Mandate probability signals across 34 practice areas</p>

        <div style={{ display: 'flex', gap: 12, marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <a href="/search" style={S.btn}>Search Companies</a>
          <a href="/signals" style={{ ...S.btn, background: '#f9fafb', color: '#374151', border: '1px solid #e5e7eb' }}>
            Recent Signals
          </a>
        </div>

        <div style={S.card}>
          <h2 style={S.cardH}>Signal Volume by Practice Area</h2>
          {trendLoading ? (
            <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>Loading trends…</p>
          ) : (
            <TrendCharts data={trendData} />
          )}
        </div>

        <div style={S.card}>
          <h2 style={S.cardH}>Getting Started</h2>
          <p style={{ fontSize: '0.875rem', color: '#6b7280', lineHeight: 1.6 }}>
            Use the <strong>Search Companies</strong> button to find a company and view its
            34×3 mandate probability matrix. Click any row in the score matrix to drill down
            into SHAP explanations.
          </p>
        </div>
      </main>
    </div>
  )
}
