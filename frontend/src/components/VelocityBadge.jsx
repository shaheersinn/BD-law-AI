/**
 * components/VelocityBadge.jsx — Digital Atelier velocity indicator.
 *
 * Positive = secondary-container (emerald) with up arrow
 * Negative = error-bg with down arrow
 * Near-zero = surface-container-high (neutral)
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
    fontSize: small ? 10 : 11,
    fontFamily: 'var(--font-data)',
    fontWeight: 700,
    padding: small ? '1px 6px' : '3px 8px',
    borderRadius: 'var(--radius-full)',
    letterSpacing: '0.03em',
    textTransform: 'uppercase',
    ...(isRising
      ? { color: 'var(--color-on-secondary-container)', background: 'var(--color-secondary-container)' }
      : isFalling
        ? { color: 'var(--color-error)', background: 'var(--color-error-bg)' }
        : { color: 'var(--color-on-surface-variant)', background: 'var(--color-surface-container-high)' }),
  }

  return (
    <span style={style}>
      {isRising ? '↑' : isFalling ? '↓' : '—'}
      {abs >= 0.05 && ` ${pct}%`}
    </span>
  )
}
