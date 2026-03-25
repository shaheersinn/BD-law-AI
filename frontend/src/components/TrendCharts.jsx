/**
 * components/TrendCharts.jsx
 *
 * Recharts bar chart showing signal volume per practice area
 * over 7d / 30d / 90d windows.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

export default function TrendCharts({ data = [] }) {
  if (!data.length) {
    return (
      <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No trend data available.</p>
    )
  }

  const chartData = data
    .slice(0, 20) // top 20 practice areas
    .map((d) => ({
      name: d.practice_area.replace(/_/g, ' ').slice(0, 18),
      '7d':  d.count_7d,
      '30d': d.count_30d,
      '90d': d.count_90d,
    }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: '#6b7280' }}
          angle={-35}
          textAnchor="end"
          interval={0}
        />
        <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
        <Tooltip
          contentStyle={{ fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: 6 }}
        />
        <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: 8 }} />
        <Bar dataKey="7d"  fill="#0C9182" name="7 days"  radius={[3, 3, 0, 0]} />
        <Bar dataKey="30d" fill="#059669" name="30 days" radius={[3, 3, 0, 0]} />
        <Bar dataKey="90d" fill="#d1fae5" name="90 days" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
