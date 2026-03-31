/**
 * pages/LoginPage.jsx — Digital Atelier login.
 *
 * Glass header treatment, Newsreader Display-LG product name,
 * navy gradient CTA, ghost borders on inputs.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/auth'

export default function LoginPage() {
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
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      background: 'var(--color-surface)',
    }}>
      {/* Left — Brand panel */}
      <div style={{
        background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '4rem',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Decorative ambient glow */}
        <div style={{
          position: 'absolute',
          top: '-20%',
          right: '-10%',
          width: '60%',
          height: '60%',
          background: 'radial-gradient(circle, rgba(173,237,211,0.08), transparent 70%)',
          pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{
            fontFamily: 'var(--font-editorial)',
            fontSize: '3.5rem',
            fontWeight: 400,
            color: 'var(--color-on-primary)',
            lineHeight: 1.15,
            letterSpacing: '-0.02em',
            marginBottom: '1.5rem',
          }}>
            ORACLE
          </div>
          <div style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.6875rem',
            fontWeight: 700,
            color: 'var(--color-on-primary-container)',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            marginBottom: '2rem',
          }}>
            BD Intelligence Platform
          </div>
          <p style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.875rem',
            color: 'var(--color-on-primary-container)',
            lineHeight: 1.6,
            maxWidth: 360,
            letterSpacing: '0.01em',
          }}>
            28 signal types. 34 practice areas. 30/60/90 day horizons.
            Predict who needs a lawyer — before they call.
          </p>
        </div>

        {/* Bottom stats */}
        <div style={{
          position: 'absolute',
          bottom: '3rem',
          left: '4rem',
          display: 'flex',
          gap: '3rem',
        }}>
          {[
            { label: 'Practice Areas', value: '34' },
            { label: 'Signal Types', value: '28' },
            { label: 'Horizons', value: '3' },
          ].map(s => (
            <div key={s.label}>
              <div style={{
                fontFamily: 'var(--font-editorial)',
                fontSize: '1.5rem',
                fontWeight: 500,
                color: 'var(--color-on-primary)',
                letterSpacing: '-0.01em',
              }}>{s.value}</div>
              <div style={{
                fontFamily: 'var(--font-data)',
                fontSize: '0.6875rem',
                fontWeight: 700,
                color: 'var(--color-on-primary-container)',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
              }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right — Login form */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '3rem',
        background: 'var(--color-surface)',
      }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          {/* Form header */}
          <h2 style={{
            fontFamily: 'var(--font-editorial)',
            fontSize: '1.5rem',
            fontWeight: 500,
            color: 'var(--color-primary)',
            marginBottom: 6,
            letterSpacing: '-0.01em',
          }}>
            Sign In
          </h2>
          <p style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.875rem',
            color: 'var(--color-on-surface-variant)',
            marginBottom: '2rem',
            letterSpacing: '0.01em',
          }}>
            Access your firm's intelligence dashboard
          </p>

          {/* Error */}
          {error && (
            <div style={{
              background: 'var(--color-error-bg)',
              color: 'var(--color-error)',
              borderRadius: 'var(--radius-md)',
              padding: '10px 14px',
              fontSize: 13,
              fontFamily: 'var(--font-data)',
              marginBottom: '1rem',
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
          {/* Username / Email */}
            <div style={{ marginBottom: '1rem' }}>
              <label style={{
                display: 'block',
                fontFamily: 'var(--font-data)',
                fontSize: '0.6875rem',
                fontWeight: 700,
                color: 'var(--color-on-surface-variant)',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                marginBottom: 6,
              }}>
                Username or Email
              </label>
              <input
                type="text"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin"
                autoFocus
                required
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.875rem',
                  color: 'var(--color-on-surface)',
                  background: 'var(--color-surface-container-lowest)',
                  borderRadius: 'var(--radius-md)',
                  outline: '1px solid rgba(197, 198, 206, 0.15)',
                  transition: 'outline-color 150ms ease-out',
                }}
                onFocus={e => e.target.style.outline = '1px solid rgba(197, 198, 206, 0.40)'}
                onBlur={e => e.target.style.outline = '1px solid rgba(197, 198, 206, 0.15)'}
              />
            </div>

            {/* Password */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                fontFamily: 'var(--font-data)',
                fontSize: '0.6875rem',
                fontWeight: 700,
                color: 'var(--color-on-surface-variant)',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                marginBottom: 6,
              }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.875rem',
                  color: 'var(--color-on-surface)',
                  background: 'var(--color-surface-container-lowest)',
                  borderRadius: 'var(--radius-md)',
                  outline: '1px solid rgba(197, 198, 206, 0.15)',
                  transition: 'outline-color 150ms ease-out',
                }}
                onFocus={e => e.target.style.outline = '1px solid rgba(197, 198, 206, 0.40)'}
                onBlur={e => e.target.style.outline = '1px solid rgba(197, 198, 206, 0.15)'}
              />
            </div>

            {/* Submit — navy gradient */}
            <button
              type="submit"
              disabled={loading || !email || !password}
              style={{
                width: '100%',
                padding: '12px 20px',
                background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
                color: 'var(--color-on-primary)',
                borderRadius: 'var(--radius-md)',
                fontFamily: 'var(--font-data)',
                fontWeight: 600,
                fontSize: '0.875rem',
                cursor: loading ? 'default' : 'pointer',
                opacity: (!email || !password) ? 0.5 : 1,
                transition: 'opacity 150ms ease-out',
                letterSpacing: '0.01em',
              }}
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          {/* Footer */}
          <p style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.6875rem',
            color: 'var(--color-on-surface-variant)',
            textAlign: 'center',
            marginTop: '2rem',
            letterSpacing: '0.01em',
          }}>
            Contact your firm administrator for access credentials
          </p>
        </div>
      </div>
    </div>
  )
}
