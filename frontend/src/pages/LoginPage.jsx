/**
 * pages/LoginPage.jsx — P3 Redesign
 *
 * Split layout: navy gradient left panel with signal category bars,
 * clean right panel with ghost-border form. DM Serif Display + DM Sans.
 * No inline styles — all via injected CSS class sheet.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/auth'

const LOGIN_CSS = `
.lp2-root {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  min-height: 100vh;
}
@media (max-width: 980px) {
  .lp2-root { grid-template-columns: 1fr; }
  .lp2-left  { display: none; }
}

/* ── Left panel ── */
.lp2-left {
  background: linear-gradient(165deg, var(--color-primary) 0%, var(--color-primary-container) 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 4rem;
  position: relative;
  overflow: hidden;
}
.lp2-left-glow {
  position: absolute;
  top: -20%; right: -10%;
  width: 60%; height: 60%;
  background: radial-gradient(circle, rgba(200,240,223,0.07), transparent 70%);
  pointer-events: none;
}
.lp2-brand {
  position: relative;
  z-index: 1;
  margin-bottom: 3rem;
}
.lp2-logo-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 1.75rem;
}
.lp2-logo-icon {
  width: 40px; height: 40px;
  border-radius: 8px;
  background: rgba(255,255,255,.08);
  display: grid; place-items: center;
  flex-shrink: 0;
}
.lp2-logo-o {
  font-family: var(--font-editorial);
  font-size: 16px;
  color: #fff;
  font-weight: 400;
}
.lp2-brand-name {
  font-family: var(--font-editorial);
  font-size: 2.8rem;
  font-weight: 400;
  color: #fff;
  line-height: 1;
  letter-spacing: -0.02em;
}
.lp2-brand-sub {
  font-family: var(--font-data);
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255,255,255,.4);
  margin-top: 4px;
}
.lp2-desc {
  font-family: var(--font-data);
  font-size: 0.88rem;
  color: rgba(255,255,255,.45);
  line-height: 1.65;
  max-width: 340px;
  margin-bottom: 2.5rem;
}

/* Signal category bars */
.lp2-bars { display: flex; flex-direction: column; gap: 10px; margin-bottom: 3rem; }
.lp2-bar-row { display: flex; align-items: center; gap: 10px; }
.lp2-bar-label {
  font-family: var(--font-data);
  font-size: 0.65rem;
  font-weight: 600;
  color: rgba(255,255,255,.55);
  width: 80px;
  flex-shrink: 0;
}
.lp2-bar-track {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: rgba(255,255,255,.08);
  overflow: hidden;
}
.lp2-bar-fill {
  height: 100%;
  border-radius: 3px;
  animation: lp2-grow 1.2s ease-out forwards;
  transform-origin: left;
}
@keyframes lp2-grow {
  from { transform: scaleX(0); }
  to   { transform: scaleX(1); }
}

/* Bottom stats */
.lp2-stats {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 2.5rem;
}
.lp2-stat-val {
  font-family: var(--font-editorial);
  font-size: 1.3rem;
  font-weight: 400;
  color: #fff;
  line-height: 1;
}
.lp2-stat-label {
  font-family: var(--font-data);
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: rgba(255,255,255,.4);
  margin-top: 3px;
}

/* ── Right panel ── */
.lp2-right {
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 3rem 2rem;
}
.lp2-form-wrap {
  width: 100%;
  max-width: 340px;
}
.lp2-form-title {
  font-family: var(--font-editorial);
  font-size: 1.3rem;
  font-weight: 400;
  color: var(--color-primary);
  margin: 0 0 6px;
}
.lp2-form-sub {
  font-family: var(--font-data);
  font-size: 0.82rem;
  color: var(--color-on-surface-variant);
  margin: 0 0 1.75rem;
}
.lp2-error {
  background: var(--color-error-bg);
  color: var(--color-error);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-family: var(--font-data);
  font-size: 0.8rem;
  margin-bottom: 1rem;
}
.lp2-field { margin-bottom: 1rem; }
.lp2-label {
  display: block;
  font-family: var(--font-data);
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 5px;
}
.lp2-input {
  width: 100%;
  padding: 11px 14px;
  font-family: var(--font-data);
  font-size: 0.875rem;
  color: var(--color-on-surface);
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-md);
  outline: 1px solid rgba(197,198,206,.2);
  border: none;
  transition: outline-color var(--transition-fast);
  box-sizing: border-box;
}
.lp2-input:focus {
  outline: 1px solid rgba(197,198,206,.5);
}
.lp2-input::placeholder { color: var(--color-on-surface-variant); opacity: 0.5; }
.lp2-submit {
  width: 100%;
  padding: 12px 20px;
  margin-top: 0.5rem;
  background: linear-gradient(to bottom, var(--color-primary), var(--color-primary-container));
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-data);
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}
.lp2-submit:disabled { opacity: 0.5; cursor: not-allowed; }
.lp2-submit:not(:disabled):hover { opacity: 0.88; }
.lp2-footer-note {
  font-family: var(--font-data);
  font-size: 0.65rem;
  color: var(--color-on-surface-variant);
  text-align: center;
  margin-top: 1.5rem;
  line-height: 1.55;
}
`

function injectLoginCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('lp2-styles')) {
    const el = document.createElement('style')
    el.id = 'lp2-styles'
    el.textContent = LOGIN_CSS
    document.head.appendChild(el)
  }
}

const SIGNAL_BARS = [
  { label: 'Filings',     width: '82%', opacity: 0.85 },
  { label: 'Litigation',  width: '68%', opacity: 0.72 },
  { label: 'Enforcement', width: '55%', opacity: 0.60 },
  { label: 'Jobs',        width: '74%', opacity: 0.78 },
  { label: 'Geospatial',  width: '42%', opacity: 0.50 },
  { label: 'News/People', width: '61%', opacity: 0.65 },
]

export default function LoginPage() {
  injectLoginCSS()
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState(null)
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) return
    setLoading(true); setError(null)
    try {
      await login(email, password)
      navigate('/constructlex', { replace: true })
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="lp2-root">
      {/* ── Left: Brand + Signals ── */}
      <div className="lp2-left">
        <div className="lp2-left-glow" />

        <div className="lp2-brand">
          <div className="lp2-logo-row">
            <div className="lp2-logo-icon">
              <span className="lp2-logo-o">O</span>
            </div>
            <div>
              <div className="lp2-brand-name">ORACLE</div>
              <div className="lp2-brand-sub">BD Intelligence Platform</div>
            </div>
          </div>
          <p className="lp2-desc">
            28 signal types. 34 practice areas. 30/60/90 day horizons.
            Predict who needs a lawyer — before they call.
          </p>
        </div>

        {/* Signal category bars */}
        <div className="lp2-bars">
          {SIGNAL_BARS.map((bar, i) => (
            <div key={bar.label} className="lp2-bar-row">
              <span className="lp2-bar-label">{bar.label}</span>
              <div className="lp2-bar-track">
                <div
                  className="lp2-bar-fill"
                  style={{
                    width: bar.width,
                    background: `rgba(200,240,223,${bar.opacity})`,
                    animationDelay: `${i * 0.1}s`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Bottom stats */}
        <div className="lp2-stats">
          {[
            { val: '34', label: 'Practice Areas' },
            { val: '28', label: 'Signal Types'   },
            { val: '6',  label: 'Categories'     },
          ].map(s => (
            <div key={s.label}>
              <div className="lp2-stat-val">{s.val}</div>
              <div className="lp2-stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right: Form ── */}
      <div className="lp2-right">
        <div className="lp2-form-wrap">
          <h1 className="lp2-form-title">Sign in</h1>
          <p className="lp2-form-sub">Access your firm's intelligence dashboard</p>

          {error && <div className="lp2-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="lp2-field">
              <label className="lp2-label" htmlFor="login-email">Username or Email</label>
              <input
                id="login-email"
                className="lp2-input"
                type="text"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin"
                autoFocus
                required
              />
            </div>

            <div className="lp2-field" style={{ marginBottom: '1.5rem' }}>
              <label className="lp2-label" htmlFor="login-password">Password</label>
              <input
                id="login-password"
                className="lp2-input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="admin"
                required
              />
            </div>

            <button
              type="submit"
              className="lp2-submit"
              disabled={loading || !email || !password}
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="lp2-footer-note">
            Contact your firm administrator for access credentials
          </p>
        </div>
      </div>
    </div>
  )
}
