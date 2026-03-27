/**
 * components/TrendCharts.jsx — Digital Atelier signal volume chart.
 * Navy/emerald palette. No border on tooltip. Tonal grid.
 */

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--color-surface-container-lowest)',
      borderRadius: 'var(--radius-xl)',
      padding: '10px 14px',
      boxShadow: 'var(--shadow-ambient)',
      fontFamily: 'var(--font-data)',
    }}>
      <div style={{ fontWeight: 600, color: 'var(--color-on-surface)', marginBottom: 6, fontSize: 12 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ fontSize: 11, color: p.color, display: 'flex', gap: 6 }}>
          <span>{p.name}:</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{p.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

export default function TrendCharts({ data = [], loading = false }) {
  if (loading) {
    return <div style={{ height: 280, borderRadius: 'var(--radius-xl)' }} className="skeleton" />
  }

  if (!data.length) {
    return (
      <div style={{
        height: 280,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--color-on-surface-variant)',
        fontSize: 13,
        fontFamily: 'var(--font-data)',
      }}>
        No trend data available yet.
      </div>
    )
  }

  const chartData = data
    .slice(0, 20)
    .map((d) => ({
      ...d,
      name: d.practice_area
        ?.replace(/_/g, ' ')
        .split(' ')
        .map((w) => w[0]?.toUpperCase() + w.slice(1, 3))
        .join(' ') || d.practice_area,
    }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: -10, bottom: 48 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-container-high)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)' }}
          angle={-40}
          textAnchor="end"
          interval={0}
          tickLine={false}
          axisLine={{ stroke: 'var(--color-surface-container-high)' }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-mono)' }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--color-surface-container-low)' }} />
        <Bar dataKey="count_7d"  name="7 days"  fill="var(--color-secondary-container)"  radius={[2, 2, 0, 0]} />
        <Bar dataKey="count_30d" name="30 days" fill="var(--color-secondary)"  radius={[2, 2, 0, 0]} />
        <Bar dataKey="count_90d" name="90 days" fill="var(--color-primary)"    radius={[2, 2, 0, 0]} opacity={0.6} />
      </BarChart>
    </ResponsiveContainer>
  )
}
