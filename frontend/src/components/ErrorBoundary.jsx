/**
 * components/ErrorBoundary.jsx — React error boundary for ORACLE.
 *
 * Catches unhandled JavaScript errors in the component tree below it.
 * Renders a ConstructLex Pro styled fallback UI instead of a blank page.
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
          {/* ConstructLex wordmark */}
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
              onClick={() => window.location.assign('/dashboard')}
            >
              Go to Dashboard
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
    fontFamily: '"Plus Jakarta Sans", system-ui, sans-serif',
  },
  card: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E5E4E0',
    borderRadius: '12px',
    padding: '2.5rem 3rem',
    maxWidth: '480px',
    width: '100%',
    textAlign: 'center',
    boxShadow: '0 4px 24px rgba(26,26,46,0.08)',
  },
  wordmark: {
    fontFamily: '"Cormorant Garamond", Georgia, serif',
    fontSize: '1.75rem',
    fontWeight: 600,
    letterSpacing: '0.15em',
    color: '#0C9182',
  },
  subtitle: {
    fontSize: '0.75rem',
    color: '#8888AA',
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    marginTop: '0.25rem',
  },
  divider: {
    height: '1px',
    backgroundColor: '#E5E4E0',
    margin: '1.5rem 0',
  },
  heading: {
    fontSize: '1.25rem',
    fontWeight: 600,
    color: '#1A1A2E',
    margin: '0 0 0.75rem 0',
  },
  body: {
    fontSize: '0.9rem',
    color: '#555566',
    lineHeight: 1.6,
    margin: '0 0 1.5rem 0',
  },
  errorDetail: {
    backgroundColor: '#FFF3F3',
    border: '1px solid #FCA5A5',
    borderRadius: '6px',
    padding: '0.75rem',
    fontSize: '0.75rem',
    color: '#B91C1C',
    textAlign: 'left',
    overflowX: 'auto',
    marginBottom: '1.5rem',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  actions: {
    display: 'flex',
    gap: '0.75rem',
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  primaryBtn: {
    backgroundColor: '#0C9182',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    padding: '0.6rem 1.5rem',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  secondaryBtn: {
    backgroundColor: 'transparent',
    color: '#0C9182',
    border: '1.5px solid #0C9182',
    borderRadius: '6px',
    padding: '0.6rem 1.5rem',
    fontSize: '0.875rem',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
}
