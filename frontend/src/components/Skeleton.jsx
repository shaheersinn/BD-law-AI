/**
 * components/Skeleton.jsx — Loading skeleton components.
 *
 * CSS-animated shimmer placeholders. No spinners.
 * Usage:
 *   <Skeleton width="100%" height={20} />
 *   <SkeletonText lines={3} />
 *   <SkeletonCard />
 *   <SkeletonRow />
 *   <SkeletonTable rows={5} cols={4} />
 */

export function Skeleton({ width = '100%', height = 16, radius = 6, style = {} }) {
  return (
    <div
      className="skeleton"
      style={{ width, height, borderRadius: radius, flexShrink: 0, ...style }}
    />
  )
}

export function SkeletonText({ lines = 3, style = {} }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, ...style }}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 ? '65%' : '100%'}
          height={14}
        />
      ))}
    </div>
  )
}

export function SkeletonCard({ height = 120, style = {} }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '1.5rem',
      ...style,
    }}>
      <Skeleton width="40%" height={18} style={{ marginBottom: 16 }} />
      <Skeleton height={height} />
    </div>
  )
}

export function SkeletonRow({ cols = 4, style = {} }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(${cols}, 1fr)`,
      gap: 12,
      ...style,
    }}>
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} height={36} />
      ))}
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {/* Header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: `200px repeat(${cols - 1}, 1fr)`,
        gap: 4, marginBottom: 4,
      }}>
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} height={32} />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} style={{
          display: 'grid',
          gridTemplateColumns: `200px repeat(${cols - 1}, 1fr)`,
          gap: 4,
        }}>
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} height={28} style={{ opacity: 1 - r * 0.08 }} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonCompanyHeader() {
  return (
    <div style={{ marginBottom: '2rem' }}>
      <Skeleton width={320} height={28} style={{ marginBottom: 12 }} />
      <Skeleton width={200} height={14} />
    </div>
  )
}
