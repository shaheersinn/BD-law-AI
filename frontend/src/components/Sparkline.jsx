/**
 * components/Sparkline.jsx — Inline SVG sparkline for 7-day score history.
 *
 * Takes an array of 1–7 float values (mandate probabilities).
 * Renders a 80×24 polyline normalized to min/max of the series.
 * Color mirrors score heatmap. Digital Atelier tokens.
 */

export default function Sparkline({ values = [], width = 80, height = 24, color }) {
  if (!values || values.length < 2) {
    return (
      <svg width={width} height={height} style={{ display: 'block' }}>
        <line
          x1={0} y1={height / 2} x2={width} y2={height / 2}
          stroke="var(--color-surface-container-high)" strokeWidth={1.5} strokeDasharray="3,3"
        />
      </svg>
    )
  }

  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 0.01

  const pad = 2
  const points = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (width - 2 * pad)
    const y = height - pad - ((v - min) / range) * (height - 2 * pad)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')

  // Last value drives the colour
  const last = values[values.length - 1]
  const strokeColor = color || (
    last >= 0.9 ? 'var(--score-4)' :
    last >= 0.7 ? 'var(--score-3)' :
    last >= 0.5 ? 'var(--score-2)' :
    last >= 0.3 ? 'var(--score-1)' :
                  'var(--color-on-surface-variant)'
  )

  // Area fill (light tinted)
  const firstPt = points.split(' ')[0]
  const lastPt  = points.split(' ')[values.length - 1]
  const areaPoints = `${firstPt.split(',')[0]},${height} ${points} ${lastPt.split(',')[0]},${height}`

  return (
    <svg width={width} height={height} style={{ display: 'block', overflow: 'visible' }}>
      {/* Area fill */}
      <polygon
        points={areaPoints}
        fill={strokeColor}
        fillOpacity={0.1}
      />
      {/* Line */}
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* End dot */}
      {(() => {
        const lastCoord = points.split(' ')[values.length - 1].split(',')
        return (
          <circle
            cx={parseFloat(lastCoord[0])}
            cy={parseFloat(lastCoord[1])}
            r={2.5}
            fill={strokeColor}
          />
        )
      })()}
    </svg>
  )
}
