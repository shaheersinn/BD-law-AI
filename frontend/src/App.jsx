/**
 * App.jsx — ORACLE Phase 0 placeholder.
 *
 * Full React dashboard is implemented in Phase 8A (functional) and
 * Phase 8B (ConstructLex Pro design system).
 *
 * ConstructLex Pro Design System:
 *   Background:    #F8F7F4 (warm off-white)
 *   Accent:        teal-emerald #0C9182 → #059669 gradient
 *   Display/nums:  Cormorant Garamond
 *   Body:          Plus Jakarta Sans
 *   Data/mono:     JetBrains Mono
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ComingSoon />} />
        <Route path="/login" element={<ComingSoon />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

function ComingSoon() {
  return (
    <div style={{
      minHeight: '100vh',
      background: '#F8F7F4',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif',
      padding: '2rem',
    }}>
      <div style={{ textAlign: 'center', maxWidth: '480px' }}>
        {/* Logo mark */}
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '16px',
          background: 'linear-gradient(135deg, #0C9182, #059669)',
          margin: '0 auto 2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <span style={{ color: 'white', fontSize: '28px', fontWeight: '700' }}>O</span>
        </div>

        <h1 style={{
          fontSize: '2rem',
          fontWeight: '700',
          color: '#1a1a1a',
          marginBottom: '0.5rem',
          letterSpacing: '-0.02em',
        }}>
          ORACLE
        </h1>

        <p style={{
          fontSize: '1rem',
          color: '#6b7280',
          marginBottom: '2rem',
          lineHeight: '1.6',
        }}>
          BigLaw BD Intelligence Platform
          <br />
          <span style={{ fontSize: '0.875rem' }}>Phase 0 — Scaffold complete</span>
        </p>

        <div style={{
          background: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '12px',
          padding: '1.5rem',
          textAlign: 'left',
        }}>
          <p style={{ fontSize: '0.875rem', color: '#374151', marginBottom: '1rem', fontWeight: '600' }}>
            Services
          </p>
          <ServiceStatus label="FastAPI Backend" url="/api/health" />
          <ServiceStatus label="API Docs" url="/api/docs" />
        </div>

        <p style={{ marginTop: '2rem', fontSize: '0.75rem', color: '#9ca3af' }}>
          Full dashboard ships in Phase 8A — Phase 8B (ConstructLex Pro UI)
        </p>
      </div>
    </div>
  )
}

function ServiceStatus({ label, url }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.75rem 0',
        borderBottom: '1px solid #f3f4f6',
        textDecoration: 'none',
        color: '#374151',
        fontSize: '0.875rem',
      }}
    >
      <span>{label}</span>
      <span style={{
        fontSize: '0.75rem',
        color: '#059669',
        background: '#ecfdf5',
        padding: '2px 8px',
        borderRadius: '4px',
      }}>
        {url}
      </span>
    </a>
  )
}

export default App
