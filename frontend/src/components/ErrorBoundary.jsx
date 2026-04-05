/**
 * components/ErrorBoundary.jsx — React error boundary for ORACLE.
 *
 * Catches unhandled JavaScript errors in the component tree below it.
 * Renders a Digital Atelier styled fallback UI instead of a blank page.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <App />
 *   </ErrorBoundary>
 *
 * The boundary resets when the user clicks "Try again" (forces re-mount
 * of the subtree by toggling an internal key).
 */

import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
    this.handleReset = this.handleReset.bind(this)
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })

    // Forward to Sentry if available (injected via index.html or window.Sentry)
    if (typeof window !== 'undefined' && window.__sentryHub) {
      try {
        window.__sentryHub.captureException(error, { extra: errorInfo })
      } catch (_) {
        // Sentry unavailable — continue silently
      }
    }

    // Log to console for debugging
    console.error('[ORACLE ErrorBoundary]', error, errorInfo)
  }

  handleReset() {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    const isDev = import.meta.env.DEV
    const errorMessage = this.state.error?.message || 'An unexpected error occurred.'

    return (
      <div style={styles.container}>
        <div style={styles.card}>
          {/* ORACLE wordmark */}
          <div style={styles.wordmark}>ORACLE</div>
          <div style={styles.subtitle}>BD Intelligence Platform</div>

          <div style={styles.divider} />

          <h2 style={styles.heading}>Something went wrong</h2>
          <p style={styles.body}>
            An unexpected error occurred in the application. Our team has been notified.
          </p>

          {isDev && (
            <pre style={styles.errorDetail}>
              {errorMessage}
              {this.state.errorInfo?.componentStack || ''}
            </pre>
          )}

          <div style={styles.actions}>
            <button style={styles.primaryBtn} onClick={this.handleReset}>
              Try again
            </button>
            <button
              style={styles.secondaryBtn}
              onClick={() => window.location.assign('/constructlex')}
            >
              Go to command center
            </button>
          </div>
        </div>
      </div>
    )
  }
}

// ── Inline styles (CSS variables may not load when boundary catches errors) ──

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#F8F7F4',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem',
    fontFamily: '"Manrope", system-ui, sans-serif',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: '16px',
    padding: '2.5rem 3rem',
    maxWidth: '480px',
    width: '100%',
    textAlign: 'center',
    boxShadow: '0 4px 24px rgba(26,40,64,0.08)',
  },
  wordmark: {
    fontFamily: 'var(--font-editorial)',
    fontSize: '1.75rem',
    fontWeight: 500,
    letterSpacing: '-0.01em',
    color: '#1a2840',
  },
  subtitle: {
    fontSize: '0.6875rem',
    color: '#71717A',
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    marginTop: '0.25rem',
    fontFamily: '"Manrope", sans-serif',
    fontWeight: 700,
  },
  divider: {
    height: '1px',
    backgroundColor: '#F0F0F0',
    margin: '1.5rem 0',
  },
  heading: {
    fontFamily: 'var(--font-editorial)',
    fontSize: '1.25rem',
    fontWeight: 500,
    color: '#1a2840',
    margin: '0 0 0.75rem 0',
  },
  body: {
    fontSize: '0.9rem',
    color: '#71717A',
    lineHeight: 1.6,
    margin: '0 0 1.5rem 0',
    fontFamily: '"Manrope", sans-serif',
  },
  errorDetail: {
    backgroundColor: '#FFF3F3',
    borderRadius: '8px',
    padding: '0.75rem',
    fontSize: '0.75rem',
    color: '#B91C1C',
    textAlign: 'left',
    overflowX: 'auto',
    marginBottom: '1.5rem',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    fontFamily: '"JetBrains Mono", monospace',
  },
  actions: {
    display: 'flex',
    gap: '0.75rem',
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  primaryBtn: {
    background: 'linear-gradient(to bottom, #1a2840, #253650)',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '8px',
    padding: '0.6rem 1.5rem',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: '"Manrope", sans-serif',
  },
  secondaryBtn: {
    backgroundColor: '#E8F5E9',
    color: '#2E7D32',
    border: 'none',
    borderRadius: '8px',
    padding: '0.6rem 1.5rem',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: '"Manrope", sans-serif',
  },
}
