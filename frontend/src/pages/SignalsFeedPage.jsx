/**
 * pages/SignalsFeedPage.jsx — Global recent signals feed.
 */

import { useEffect, useState } from 'react'
import { signals as signalsApi } from '../api/client'
import SignalFeed from '../components/SignalFeed'

const S = {
  page: { minHeight: '100vh', background: '#F8F7F4', fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif' },
  main: { maxWidth: 900, margin: '0 auto', padding: '2rem 1.5rem' },
  back: { color: '#6b7280', fontSize: '0.875rem', textDecoration: 'none', display: 'inline-block', marginBottom: '1.25rem' },
  h1:   { fontSize: '1.4rem', fontWeight: 700, color: '#111827', marginBottom: '0.25rem' },
  sub:  { color: '#6b7280', fontSize: '0.875rem', marginBottom: '1.5rem' },
  row:  { display: 'flex', gap: 10, marginBottom: '1.5rem', alignItems: 'center' },
  input:{ flex: 1, padding: '9px 14px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: '0.875rem', outline: 'none' },
  btn:  { padding: '9px 18px', background: 'linear-gradient(135deg,#0C9182,#059669)', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, cursor: 'pointer', fontSize: '0.875rem' },
}

export default function SignalsFeedPage() {
  const [companyId, setCompanyId] = useState('')
  const [signals, setSignals]     = useState([])
  const [loading, setLoading]     = useState(false)
  const [searched, setSearched]   = useState(false)

  const fetchSignals = async (e) => {
    e && e.preventDefault()
    if (!companyId) return
    setLoading(true)
    try {
      const data = await signalsApi.list(companyId, { limit: 200 })
      setSignals(data || [])
    } catch {
      setSignals([])
    } finally {
      setLoading(false)
      setSearched(true)
    }
  }

  return (
    <div style={S.page}>
      <main style={S.main}>
        <a href="/dashboard" style={S.back}>← Dashboard</a>
        <h1 style={S.h1}>Signal Feed</h1>
        <p style={S.sub}>Recent signals for a company (last 90 days)</p>

        <form onSubmit={fetchSignals} style={S.row}>
          <input
            type="number"
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            placeholder="Company ID (e.g. 42)"
            style={S.input}
          />
          <button type="submit" disabled={loading || !companyId} style={S.btn}>
            {loading ? '…' : 'Fetch'}
          </button>
        </form>

        {searched && (
          loading ? (
            <p style={{ color: '#9ca3af' }}>Loading…</p>
          ) : (
            <SignalFeed signals={signals} />
          )
        )}
      </main>
    </div>
  )
}
