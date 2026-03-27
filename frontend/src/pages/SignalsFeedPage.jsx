/**
 * pages/SignalsFeedPage.jsx — Digital Atelier signal feed.
 * Tonal surfaces, signal type chips, pill-style limit buttons.
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
          <h1 style={{
            fontFamily: 'var(--font-editorial)',
            fontWeight: 500,
            fontSize: '1.5rem',
            color: 'var(--color-primary)',
            margin: 0,
            letterSpacing: '-0.01em',
          }}>
            Signal Feed
          </h1>
          {/* Limit pills */}
          <div style={{
            display: 'flex',
            gap: 4,
            alignItems: 'center',
            background: 'var(--color-surface-container-low)',
            borderRadius: 'var(--radius-xl)',
            padding: 4,
          }}>
            {[50, 100, 200].map((n) => (
              <button
                key={n}
                onClick={() => { setLimit(n); load(n) }}
                style={{
                  padding: '5px 12px',
                  borderRadius: 'var(--radius-md)',
                  background: limit === n
                    ? 'var(--color-surface-container-lowest)'
                    : 'transparent',
                  color: limit === n
                    ? 'var(--color-on-surface)'
                    : 'var(--color-on-surface-variant)',
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                  cursor: 'pointer',
                  boxShadow: limit === n ? 'var(--shadow-ambient)' : 'none',
                  transition: 'background 150ms ease-out',
                }}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <p style={{
          fontFamily: 'var(--font-data)',
          color: 'var(--color-on-surface-variant)',
          fontSize: '0.875rem',
          letterSpacing: '0.01em',
          marginBottom: '1.75rem',
        }}>
          Latest signals across all companies and sources
        </p>

        {error && (
          <div style={{
            color: 'var(--color-error)',
            background: 'var(--color-error-bg)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            fontSize: 13,
            fontFamily: 'var(--font-data)',
            marginBottom: '1rem',
          }}>
            {error}
          </div>
        )}

        <SignalFeed signals={signals} loading={loading} />
      </div>
    </AppShell>
  )
}
