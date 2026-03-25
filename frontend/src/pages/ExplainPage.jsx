/**
 * pages/ExplainPage.jsx — ConstructLex Pro SHAP explanations.
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { scores as scoresApi } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { SkeletonCard } from '../components/Skeleton'

function ShapBar({ value, maxAbs }) {
  const pct = (Math.abs(value) / maxAbs) * 100
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, background: 'var(--surface-raised)', borderRadius: 3, height: 6, overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%', borderRadius: 3,
          background: value >= 0 ? 'var(--accent)' : 'var(--error)',
          transition: 'width 0.3s ease',
        }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: value >= 0 ? 'var(--success)' : 'var(--error)', minWidth: 48, textAlign: 'right' }}>
        {value >= 0 ? '+' : ''}{value?.toFixed(3)}
      </span>
    </div>
  )
}

export default function ExplainPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [explanations, setExplanations] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    scoresApi.explain(id)
      .then(setExplanations)
      .catch((err) => setError(err.message || 'Failed to load explanations'))
      .finally(() => setLoading(false))
  }, [id])

  return (
    <AppShell>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <button onClick={() => navigate(`/companies/${id}`)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', fontSize: 13, padding: 0, marginBottom: '1.5rem', fontFamily: 'var(--font-body)' }}>
          ← Company Detail
        </button>

        <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 30, color: 'var(--text)', marginBottom: '0.5rem' }}>
          SHAP Explanations
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: '2rem', margin: '0 0 2rem' }}>
          Feature contributions for the top 5 highest-scoring practice areas
        </p>

        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} height={160} />)}
          </div>
        )}

        {error && (
          <div style={{ color: 'var(--error)', background: 'var(--error-bg)', border: '1px solid var(--error)', borderRadius: 'var(--radius-md)', padding: '12px 16px', fontSize: 13 }}>
            {error}
          </div>
        )}

        {!loading && !error && !explanations?.length && (
          <div style={{ padding: '3rem 2rem', textAlign: 'center', color: 'var(--text-tertiary)', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)' }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>📊</div>
            <div style={{ fontWeight: 600, fontSize: 13 }}>No explanations available</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>Scores must reach 40%+ threshold before SHAP explanations are generated.</div>
          </div>
        )}

        {!loading && explanations?.map((exp, i) => {
          const maxAbs = Math.max(...(exp.top_shap_features?.map(f => Math.abs(f.shap_value)) || [1]))
          return (
            <div key={i} style={{
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)', padding: '1.5rem',
              marginBottom: '1.25rem', boxShadow: 'var(--shadow-sm)',
            }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 4 }}>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--accent)', textTransform: 'capitalize' }}>
                  {exp.practice_area?.replace(/_/g, ' ')}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: 'var(--text)' }}>
                  {(exp.score * 100).toFixed(1)}%
                </div>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: '1.25rem', fontFamily: 'var(--font-mono)' }}>
                {exp.horizon}d horizon{exp.base_value != null ? ` · base ${(exp.base_value * 100).toFixed(1)}%` : ''}
              </div>

              {exp.top_shap_features?.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
                    Feature Contributions
                  </div>
                  {exp.top_shap_features.map((f, j) => (
                    <div key={j} style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 12, alignItems: 'center', padding: '5px 0', borderBottom: '1px solid var(--surface-raised)' }}>
                      <span style={{ fontSize: 12, color: 'var(--text)', fontFamily: 'var(--font-body)' }}>{f.feature}</span>
                      <ShapBar value={f.shap_value} maxAbs={maxAbs} />
                    </div>
                  ))}
                </div>
              )}

              {exp.counterfactuals?.length > 0 && (
                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>
                    What Would Lower This Score
                  </div>
                  {exp.counterfactuals.map((cf, j) => (
                    <div key={j} style={{
                      padding: '8px 12px', background: 'var(--success-bg)',
                      borderRadius: 'var(--radius-sm)', marginBottom: 6,
                      fontSize: 12, color: 'var(--text)',
                      border: '1px solid var(--success)',
                      borderLeft: '3px solid var(--success)',
                    }}>
                      <strong style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{cf.feature}</strong>
                      <span style={{ color: 'var(--text-secondary)' }}> → {cf.direction} it</span>
                      {cf.estimated_score_reduction && (
                        <span style={{ marginLeft: 8, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--success)' }}>
                          −{(cf.estimated_score_reduction * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </AppShell>
  )
}
