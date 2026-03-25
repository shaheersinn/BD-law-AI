/**
 * pages/LoginPage.jsx — JWT login form.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/auth'

const styles = {
  page: {
    minHeight: '100vh',
    background: '#F8F7F4',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif',
    padding: '2rem',
  },
  card: {
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: 16,
    padding: '2.5rem',
    width: '100%',
    maxWidth: 400,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  logo: {
    width: 48,
    height: 48,
    borderRadius: 12,
    background: 'linear-gradient(135deg, #0C9182, #059669)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '1.5rem',
  },
  title: { fontSize: '1.5rem', fontWeight: 700, color: '#111827', marginBottom: 4 },
  sub:   { fontSize: '0.875rem', color: '#6b7280', marginBottom: '1.75rem' },
  label: { display: 'block', fontSize: '0.875rem', fontWeight: 500, color: '#374151', marginBottom: 6 },
  input: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid #d1d5db',
    borderRadius: 8,
    fontSize: '0.875rem',
    color: '#111827',
    boxSizing: 'border-box',
    marginBottom: '1rem',
    outline: 'none',
  },
  btn: {
    width: '100%',
    padding: '11px',
    background: 'linear-gradient(135deg, #0C9182, #059669)',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: '0.9rem',
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: 4,
  },
  error: {
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: 8,
    padding: '10px 14px',
    fontSize: '0.875rem',
    color: '#991b1b',
    marginBottom: '1rem',
  },
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, error, clearError } = useAuthStore()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearError()
    setLoading(true)
    const ok = await login(email, password)
    setLoading(false)
    if (ok) navigate('/dashboard', { replace: true })
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <span style={{ color: '#fff', fontSize: 22, fontWeight: 700 }}>O</span>
        </div>
        <h1 style={styles.title}>ORACLE</h1>
        <p style={styles.sub}>BigLaw BD Intelligence Platform</p>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="admin@halcyon.legal"
            required
            autoFocus
            style={styles.input}
          />
          <label style={styles.label}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            style={styles.input}
          />
          <button type="submit" disabled={loading} style={styles.btn}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
