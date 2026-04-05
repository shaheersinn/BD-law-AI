/**
 * pages/SignalsFeedPage.jsx — P5 Redesign
 *
 * Signal feed. Tonal surfaces, signal type chips, pill-style limit buttons.
 * No inline styles. Everything uses injected CSS.
 */

import { useEffect, useState } from 'react'
import { signals as signalsApi } from '../api/client'
import SignalFeed from '../components/SignalFeed'
import AppShell  from '../components/layout/AppShell'

const SIGNALS_CSS = `
.sig-root {
  max-width: 860px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.sig-header-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
  gap: 12px;
}
.sig-title {
  font-family: var(--font-editorial);
  font-weight: 400;
  font-size: 1.6rem;
  color: var(--color-primary);
  margin: 0;
  letter-spacing: -0.01em;
}
.sig-limits {
  display: flex;
  gap: 4px;
  align-items: center;
  background: var(--color-surface-container-low);
  border-radius: var(--radius-xl);
  padding: 4px;
}
.sig-limit-btn {
  padding: 5px 12px;
  border-radius: var(--radius-md);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  cursor: pointer;
  border: none;
  transition: background var(--transition-fast), color var(--transition-fast), box-shadow var(--transition-fast);
}
.sig-limit-btn.active {
  background: var(--color-surface-container-lowest);
  color: var(--color-on-surface);
  box-shadow: var(--shadow-ambient);
}
.sig-limit-btn.inactive {
  background: transparent;
  color: var(--color-on-surface-variant);
  box-shadow: none;
}
.sig-subtitle {
  font-family: var(--font-data);
  color: var(--color-on-surface-variant);
  font-size: 0.875rem;
  letter-spacing: 0.01em;
  margin-bottom: 1.75rem;
}
.sig-error {
  color: var(--color-error);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 13px;
  font-family: var(--font-data);
  margin-bottom: 1rem;
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('sig-styles')) {
    const el = document.createElement('style')
    el.id = 'sig-styles'
    el.textContent = SIGNALS_CSS
    document.head.appendChild(el)
  }
}

export default function SignalsFeedPage() {
  injectCSS()
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
      <div className="sig-root">
        <div className="sig-header-row">
          <h1 className="sig-title">Signal Feed</h1>
          <div className="sig-limits">
            {[50, 100, 200].map((n) => (
              <button
                key={n}
                onClick={() => { setLimit(n); load(n) }}
                className={`sig-limit-btn ${limit === n ? 'active' : 'inactive'}`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <p className="sig-subtitle">Latest signals across all companies and sources</p>

        {error && <div className="sig-error">{error}</div>}

        <SignalFeed signals={signals} loading={loading} />
      </div>
    </AppShell>
  )
}
