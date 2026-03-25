/**
 * components/VelocityBadge.jsx — Visual velocity indicator.
 *
 * Positive = rising mandate probability (teal arrow up)
 * Negative = declining (muted arrow down)
 * Near-zero = flat (dash)
 */

export default function VelocityBadge({ velocity, size = 'md' }) {
  if (velocity == null) return null

  const abs = Math.abs(velocity)
  const isRising  = velocity >= 0.05
  const isFalling = velocity <= -0.05
  const pct = (abs * 100).toFixed(0)

  const small = size === 'sm'
  const style = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: small ? 3 : 4,
    fontSize: small ? 10 : 12,
    fontFamily: 'var(--font-mono)',
    fontWeight: 600,
    padding: small ? '1px 6px' : '3px 8px',
    borderRadius: 999,
    ...(isRising  ? { color: 'var(--success)', background: 'var(--success-bg)', border: '1px solid var(--success)' } :
        isFalling ? { color: 'var(--text-secondary)', background: 'var(--surface-raised)', border: '1px solid var(--border)' } :
                    { color: 'var(--text-tertiary)', background: 'var(--surface-raised)', border: '1px solid var(--border)' }),
  }

  return (
    <span style={style}>
      {isRising ? '↑' : isFalling ? '↓' : '—'}
      {abs >= 0.05 && ` ${pct}%`}
    </span>
  )
}
