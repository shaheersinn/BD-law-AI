/**
 * components/TrendCharts.jsx — Signal volume trend chart.
 * ConstructLex Pro — teal-emerald palette, Recharts BarChart.
 */

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      padding: '10px 14px',
      boxShadow: 'var(--shadow-md)',
      fontFamily: 'var(--font-body)',
    }}>
      <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 6, fontSize: 12 }}>{label}</div>
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
    return <div style={{ height: 280, background: 'var(--surface-raised)', borderRadius: 8, animation: 'shimmer 1.5s infinite' }} className="skeleton" />
  }

  if (!data.length) {
    return (
      <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
        No trend data available yet.
      </div>
    )
  }

  // Take top 20 by 30d volume, shorten labels
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
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'var(--font-body)' }}
          angle={-40}
          textAnchor="end"
          interval={0}
          tickLine={false}
          axisLine={{ stroke: 'var(--border)' }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--accent-light)' }} />
        <Bar dataKey="count_7d"  name="7 days"  fill="var(--score-2)"  radius={[2, 2, 0, 0]} />
        <Bar dataKey="count_30d" name="30 days" fill="var(--score-3)"  radius={[2, 2, 0, 0]} />
        <Bar dataKey="count_90d" name="90 days" fill="var(--score-4)"  radius={[2, 2, 0, 0]} opacity={0.6} />
      </BarChart>
    </ResponsiveContainer>
  )
}
