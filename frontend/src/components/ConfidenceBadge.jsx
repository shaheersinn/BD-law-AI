/**
 * components/ConfidenceBadge.jsx — Confidence score badge.
 *
 * Color bands:
 *   ≥ 0.9  → green  "Very High"
 *   0.7–0.9 → teal   "High"
 *   0.5–0.7 → amber  "Medium"
 *   < 0.5  → red    "Low"
 */

export default function ConfidenceBadge({ score, showLabel = false }) {
  if (score == null) return null

  const pct = Math.round(score * 100)

  let cls, label
  if (score >= 0.9) {
    cls = 'cl-badge cl-badge-green'
    label = 'Very High'
  } else if (score >= 0.7) {
    cls = 'cl-badge cl-badge-teal'
    label = 'High'
  } else if (score >= 0.5) {
    cls = 'cl-badge cl-badge-amber'
    label = 'Medium'
  } else {
    cls = 'cl-badge cl-badge-red'
    label = 'Low'
  }

  return (
    <span className={cls}>
      {pct}%{showLabel && ` · ${label}`}
    </span>
  )
}

/** Velocity badge: signed percentage */
export function VelocityBadge({ velocity }) {
  if (velocity == null) return null

  const pct = (velocity * 100).toFixed(1)
  const sign = velocity > 0 ? '+' : ''

  let cls
  if (velocity > 0.15)       cls = 'cl-badge cl-vel-positive'
  else if (velocity < -0.15) cls = 'cl-badge cl-vel-negative'
  else                        cls = 'cl-badge cl-vel-neutral'

  return (
    <span className={cls}>
      {sign}{pct}%
    </span>
  )
}
