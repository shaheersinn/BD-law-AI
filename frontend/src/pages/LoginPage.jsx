/**
 * pages/LoginPage.jsx — ConstructLex Pro login.
 *
 * Split layout: left brand panel (teal gradient) + right form.
 * Cormorant Garamond wordmark. Plus Jakarta Sans body.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, error, clearError } = useAuthStore()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError?.()
    setLoading(true)
    const ok = await login(email, password)
    setLoading(false)
    if (ok) navigate('/dashboard', { replace: true })
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      fontFamily: 'var(--font-body)',
      background: 'var(--bg)',
    }}>
      {/* ── Left brand panel ─────────────────────────────────────────────── */}
      <div style={{
        width: 420,
        flexShrink: 0,
        background: 'linear-gradient(160deg, var(--accent-dark) 0%, var(--accent) 55%, var(--accent-2) 100%)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '3rem',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Subtle geometric pattern */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.06,
          backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)',
          backgroundSize: '28px 28px',
        }} />

        <div style={{ position: 'relative' }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 700, fontSize: 42,
            color: '#fff',
            letterSpacing: '0.04em',
            lineHeight: 1,
            marginBottom: 8,
          }}>
            ORACLE
          </div>
          <div style={{
            color: 'rgba(255,255,255,0.7)', fontSize: 13,
            letterSpacing: '0.12em', textTransform: 'uppercase',
            fontWeight: 500,
          }}>
            BD Intelligence Platform
          </div>
        </div>

        <div style={{ position: 'relative' }}>
          <blockquote style={{
            margin: 0,
            fontFamily: 'var(--font-display)',
            fontSize: 20, fontWeight: 600,
            color: 'rgba(255,255,255,0.9)',
            lineHeight: 1.4,
            fontStyle: 'italic',
          }}>
            "Predict the mandate before the call goes out."
          </blockquote>
          <div style={{
            marginTop: 12,
            fontSize: 11, color: 'rgba(255,255,255,0.55)',
            letterSpacing: '0.08em', textTransform: 'uppercase',
          }}>
            Halcyon Legal · Toronto
          </div>
        </div>
      </div>

      {/* ── Right form panel ──────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem',
      }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          <h1 style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 700, fontSize: 28,
            color: 'var(--text)',
            marginBottom: 6,
          }}>
            Sign in
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: '2rem', margin: '0 0 2rem' }}>
            Access your BD intelligence dashboard
          </p>

          {error && (
            <div style={{
              background: 'var(--error-bg)',
              border: '1px solid var(--error)',
              borderRadius: 'var(--radius-md)',
              padding: '10px 14px',
              fontSize: 13,
              color: 'var(--error)',
              marginBottom: '1.25rem',
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{
                display: 'block', fontSize: 12, fontWeight: 600,
                color: 'var(--text-secondary)', marginBottom: 6,
                textTransform: 'uppercase', letterSpacing: '0.07em',
              }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@halcyon.legal"
                required
                autoFocus
                style={{
                  width: '100%', padding: '10px 14px',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 13, color: 'var(--text)',
                  background: 'var(--surface)',
                  boxSizing: 'border-box', outline: 'none',
                  transition: 'border-color var(--transition)',
                  fontFamily: 'var(--font-body)',
                }}
                onFocus={e => e.target.style.borderColor = 'var(--accent)'}
                onBlur={e  => e.target.style.borderColor = 'var(--border)'}
              />
            </div>

            <div style={{ marginBottom: '1.75rem' }}>
              <label style={{
                display: 'block', fontSize: 12, fontWeight: 600,
                color: 'var(--text-secondary)', marginBottom: 6,
                textTransform: 'uppercase', letterSpacing: '0.07em',
              }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  width: '100%', padding: '10px 14px',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 13, color: 'var(--text)',
                  background: 'var(--surface)',
                  boxSizing: 'border-box', outline: 'none',
                  transition: 'border-color var(--transition)',
                  fontFamily: 'var(--font-body)',
                }}
                onFocus={e => e.target.style.borderColor = 'var(--accent)'}
                onBlur={e  => e.target.style.borderColor = 'var(--border)'}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%', padding: '11px',
                background: loading ? 'var(--border)' : 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                color: loading ? 'var(--text-tertiary)' : '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                fontSize: 13, fontWeight: 700,
                cursor: loading ? 'default' : 'pointer',
                fontFamily: 'var(--font-body)',
                letterSpacing: '0.04em',
                transition: 'background var(--transition)',
              }}
            >
              {loading ? 'Signing in…' : 'Sign in →'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
