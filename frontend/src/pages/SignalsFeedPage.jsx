/**
 * pages/SignalsFeedPage.jsx — ConstructLex Pro global signal feed.
 */

import { useEffect, useState } from 'react'
import { signals as signalsApi } from '../api/client'
import SignalFeed from '../components/SignalFeed'
import AppShell  from '../components/layout/AppShell'

export default function SignalsFeedPage() {
  const [signals, setSignals]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [limit, setLimit]       = useState(100)

  const load = (lim) => {
    setLoading(true)
    signalsApi.list(null, { limit: lim })
      .then(setSignals)
      .catch((err) => setError(err.message || 'Failed to load signals'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(limit) }, [])

  return (
    <AppShell>
      <div style={{ maxWidth: 860, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '0.5rem', flexWrap: 'wrap', gap: 12 }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 30, color: 'var(--text)', margin: 0 }}>
            Signal Feed
          </h1>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {[50, 100, 200].map((n) => (
              <button
                key={n}
                onClick={() => { setLimit(n); load(n) }}
                style={{
                  padding: '5px 12px',
                  border: '1px solid',
                  borderColor: limit === n ? 'var(--accent)' : 'var(--border)',
                  borderRadius: 'var(--radius-md)',
                  background: limit === n ? 'var(--accent-light)' : 'var(--surface)',
                  color: limit === n ? 'var(--accent)' : 'var(--text-secondary)',
                  fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font-body)',
                }}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: '1.75rem', margin: '0 0 1.75rem' }}>
          Latest signals across all companies and sources
        </p>

        {error && (
          <div style={{ color: 'var(--error)', background: 'var(--error-bg)', border: '1px solid var(--error)', borderRadius: 'var(--radius-md)', padding: '10px 14px', fontSize: 13, marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <SignalFeed signals={signals} loading={loading} />
      </div>
    </AppShell>
  )
}
