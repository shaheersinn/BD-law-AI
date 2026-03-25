/**
 * components/LoadingSkeleton.jsx — Skeleton loading states.
 *
 * Shape-matched to the content they replace.
 * Animated via cl-skeleton CSS class (@keyframes cl-skeleton-pulse).
 * Never use spinners — use these instead.
 */

// ── Primitive ─────────────────────────────────────────────────────────────────

export function SkeletonBlock({ width = '100%', height = 16, style = {} }) {
  return (
    <div
      className="cl-skeleton"
      style={{ width, height, borderRadius: 6, ...style }}
    />
  )
}

export function SkeletonText({ width = '100%', lines = 1, gap = 8 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="cl-skeleton-text"
          style={{
            width: i === lines - 1 && lines > 1 ? '70%' : width,
          }}
        />
      ))}
    </div>
  )
}

// ── Composed skeletons ────────────────────────────────────────────────────────

/** Dashboard velocity table skeleton */
export function VelocityTableSkeleton({ rows = 8 }) {
  return (
    <div>
      <SkeletonBlock height={32} style={{ marginBottom: 12, borderRadius: 8 }} />
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1.2fr 80px 80px',
            gap: 16,
            padding: '12px 0',
            borderBottom: '1px solid var(--cl-border)',
            alignItems: 'center',
          }}
        >
          <SkeletonText width={`${60 + (i % 4) * 10}%`} />
          <SkeletonText width="60%" />
          <SkeletonBlock height={22} style={{ borderRadius: 999 }} />
          <SkeletonBlock height={22} style={{ borderRadius: 6 }} />
        </div>
      ))}
    </div>
  )
}

/** Score matrix skeleton */
export function ScoreMatrixSkeleton({ rows = 10 }) {
  return (
    <div>
      <SkeletonBlock height={36} style={{ marginBottom: 8, borderRadius: 8 }} />
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            display: 'grid',
            gridTemplateColumns: '2fr 80px 80px 80px',
            gap: 8,
            padding: '8px 0',
            borderBottom: '1px solid var(--cl-border)',
            alignItems: 'center',
          }}
        >
          <SkeletonText width={`${50 + (i % 5) * 8}%`} />
          <SkeletonBlock height={28} style={{ borderRadius: 4 }} />
          <SkeletonBlock height={28} style={{ borderRadius: 4 }} />
          <SkeletonBlock height={28} style={{ borderRadius: 4 }} />
        </div>
      ))}
    </div>
  )
}

/** Signal feed skeleton */
export function SignalFeedSkeleton({ items = 6 }) {
  return (
    <div>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} style={{ padding: '12px 0', borderBottom: '1px solid var(--cl-border)' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
            <SkeletonBlock width={90} height={18} style={{ borderRadius: 4 }} />
            <SkeletonBlock width={60} height={18} style={{ borderRadius: 999 }} />
          </div>
          <SkeletonText lines={2} />
          <div style={{ marginTop: 6 }}>
            <SkeletonText width="35%" />
          </div>
        </div>
      ))}
    </div>
  )
}

/** Company stat row skeleton */
export function StatRowSkeleton() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i}>
          <SkeletonText width="50%" lines={1} />
          <div style={{ marginTop: 5 }}>
            <SkeletonText width="80%" lines={1} />
          </div>
        </div>
      ))}
    </div>
  )
}

/** Trend chart skeleton */
export function TrendChartSkeleton() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="cl-card" style={{ padding: '1rem' }}>
          <SkeletonText width="70%" />
          <div style={{ marginTop: 10 }}>
            <SkeletonBlock height={40} style={{ borderRadius: 6 }} />
          </div>
        </div>
      ))}
    </div>
  )
}
