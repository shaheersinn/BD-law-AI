/**
 * pages/ExplainPage.jsx — SHAP explanations for top 5 practice areas.
 */

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { scores as scoresApi } from '../api/client'

const S = {
  page:  { minHeight: '100vh', background: '#F8F7F4', fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif' },
  main:  { maxWidth: 900, margin: '0 auto', padding: '2rem 1.5rem' },
  back:  { color: '#6b7280', fontSize: '0.875rem', textDecoration: 'none', display: 'inline-block', marginBottom: '1.25rem' },
  h1:    { fontSize: '1.4rem', fontWeight: 700, color: '#111827', marginBottom: '1.5rem' },
  card:  { background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.5rem', marginBottom: '1.25rem' },
  pa:    { fontSize: '1rem', fontWeight: 700, color: '#0C9182', textTransform: 'capitalize', marginBottom: 4 },
  score: { fontSize: '0.85rem', color: '#6b7280', marginBottom: '1rem' },
  h3:    { fontSize: '0.8rem', fontWeight: 600, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 },
  feat:  { display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #f9fafb', fontSize: '0.85rem' },
  cf:    { padding: '5px 10px', background: '#f0fdf4', borderRadius: 6, fontSize: '0.8rem', color: '#166534', marginBottom: 4 },
}

function FeatureRow({ feature, shap_value }) {
  const sign = shap_value >= 0 ? '+' : ''
  return (
    <div style={S.feat}>
      <span style={{ color: '#374151' }}>{feature}</span>
      <span style={{ fontFamily: 'JetBrains Mono, monospace', color: shap_value >= 0 ? '#059669' : '#dc2626' }}>
        {sign}{shap_value?.toFixed(3)}
      </span>
    </div>
  )
}

export default function ExplainPage() {
  const { id } = useParams()
  const [explanations, setExplanations] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    scoresApi.explain(id)
      .then(setExplanations)
      .catch((err) => setError(err.message || 'Failed to load explanations'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={S.page}><main style={S.main}><p style={{ color: '#9ca3af' }}>Loading…</p></main></div>
  if (error)   return <div style={S.page}><main style={S.main}><p style={{ color: '#ef4444' }}>{error}</p></main></div>

  return (
    <div style={S.page}>
      <main style={S.main}>
        <a href={`/companies/${id}`} style={S.back}>← Company Detail</a>
        <h1 style={S.h1}>SHAP Explanations — Top Practice Areas</h1>

        {!explanations?.length ? (
          <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No explanations available yet.</p>
        ) : (
          explanations.map((exp, i) => (
            <div key={i} style={S.card}>
              <div style={S.pa}>{exp.practice_area?.replace(/_/g, ' ')}</div>
              <div style={S.score}>
                Score {(exp.score * 100).toFixed(1)}% · {exp.horizon}d horizon
                {exp.base_value != null && ` · Base ${(exp.base_value * 100).toFixed(1)}%`}
              </div>

              {exp.top_shap_features?.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div style={S.h3}>Top SHAP Features</div>
                  {exp.top_shap_features.map((f, j) => (
                    <FeatureRow key={j} feature={f.feature} shap_value={f.shap_value} />
                  ))}
                </div>
              )}

              {exp.counterfactuals?.length > 0 && (
                <div>
                  <div style={S.h3}>Counterfactuals (what would lower this score)</div>
                  {exp.counterfactuals.map((cf, j) => (
                    <div key={j} style={S.cf}>
                      {cf.feature}: {cf.direction} → score reduction {cf.reduction ? `−${(cf.reduction * 100).toFixed(1)}%` : '?'}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </main>
    </div>
  )
}
