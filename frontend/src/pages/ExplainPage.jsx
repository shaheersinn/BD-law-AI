/**
 * pages/ExplainPage.jsx — Digital Atelier SHAP explanations.
 * No borders. Tonal surface cards. Newsreader headlines.
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
      <div style={{
        flex: 1,
        background: 'var(--color-surface-container-high)',
        borderRadius: 3,
        height: 6,
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%', borderRadius: 3,
          background: value >= 0 ? 'var(--color-secondary)' : 'var(--color-error)',
          transition: 'width 0.3s ease',
        }} />
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: value >= 0 ? 'var(--color-success)' : 'var(--color-error)',
        minWidth: 48,
        textAlign: 'right',
      }}>
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
        <button
          onClick={() => navigate(`/companies/${id}`)}
          style={{
            background: 'none',
            cursor: 'pointer',
            color: 'var(--color-on-surface-variant)',
            fontSize: 13,
            padding: 0,
            marginBottom: '1.5rem',
            fontFamily: 'var(--font-data)',
          }}
        >
          ← Company Detail
        </button>

        <h1 style={{
          fontFamily: 'var(--font-editorial)',
          fontWeight: 500,
          fontSize: '1.75rem',
          color: 'var(--color-primary)',
          marginBottom: '0.5rem',
          letterSpacing: '-0.01em',
        }}>
          SHAP Explanations
        </h1>
        <p style={{
          color: 'var(--color-on-surface-variant)',
          fontSize: 13,
          marginBottom: '2rem',
          fontFamily: 'var(--font-data)',
          letterSpacing: '0.01em',
        }}>
          Feature contributions for the top 5 highest-scoring practice areas
        </p>

        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} height={160} />)}
          </div>
        )}

        {error && (
          <div style={{
            color: 'var(--color-error)',
            background: 'var(--color-error-bg)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 16px',
            fontSize: 13,
            fontFamily: 'var(--font-data)',
          }}>
            {error}
          </div>
        )}

        {!loading && !error && !explanations?.length && (
          <div style={{
            padding: '3rem 2rem',
            textAlign: 'center',
            color: 'var(--color-on-surface-variant)',
            background: 'var(--color-surface-container-lowest)',
            borderRadius: 'var(--radius-xl)',
            boxShadow: 'var(--shadow-ambient)',
            fontFamily: 'var(--font-data)',
          }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>📊</div>
            <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--color-on-surface)' }}>No explanations available</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>Scores must reach 40%+ threshold before SHAP explanations are generated.</div>
          </div>
        )}

        {!loading && explanations?.map((exp, i) => {
          const maxAbs = Math.max(...(exp.top_shap_features?.map(f => Math.abs(f.shap_value)) || [1]))
          return (
            <div key={i} style={{
              background: 'var(--color-surface-container-lowest)',
              borderRadius: 'var(--radius-xl)',
              padding: '1.5rem',
              marginBottom: '1.25rem',
              boxShadow: 'var(--shadow-ambient)',
            }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 4 }}>
                <div style={{
                  fontFamily: 'var(--font-editorial)',
                  fontWeight: 500,
                  fontSize: 18,
                  color: 'var(--color-primary)',
                  textTransform: 'capitalize',
                  letterSpacing: '-0.01em',
                }}>
                  {exp.practice_area?.replace(/_/g, ' ')}
                </div>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 20,
                  fontWeight: 700,
                  color: 'var(--color-on-surface)',
                }}>
                  {(exp.score * 100).toFixed(1)}%
                </div>
              </div>
              <div style={{
                fontSize: 11,
                color: 'var(--color-on-surface-variant)',
                marginBottom: '1.25rem',
                fontFamily: 'var(--font-mono)',
              }}>
                {exp.horizon}d horizon{exp.base_value != null ? ` · base ${(exp.base_value * 100).toFixed(1)}%` : ''}
              </div>

              {exp.top_shap_features?.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{
                    fontFamily: 'var(--font-data)',
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    color: 'var(--color-on-surface-variant)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 10,
                  }}>
                    Feature Contributions
                  </div>
                  {exp.top_shap_features.map((f, j) => (
                    <div key={j} style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 2fr',
                      gap: 12,
                      alignItems: 'center',
                      padding: '7px 8px',
                      borderRadius: 'var(--radius-md)',
                      background: j % 2 === 0 ? 'transparent' : 'var(--color-surface-container-low)',
                    }}>
                      <span style={{
                        fontSize: 12,
                        color: 'var(--color-on-surface)',
                        fontFamily: 'var(--font-data)',
                      }}>
                        {f.feature}
                      </span>
                      <ShapBar value={f.shap_value} maxAbs={maxAbs} />
                    </div>
                  ))}
                </div>
              )}

              {exp.counterfactuals?.length > 0 && (
                <div>
                  <div style={{
                    fontFamily: 'var(--font-data)',
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    color: 'var(--color-on-surface-variant)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 8,
                  }}>
                    What Would Lower This Score
                  </div>
                  {exp.counterfactuals.map((cf, j) => (
                    <div key={j} style={{
                      padding: '8px 12px',
                      background: 'var(--color-success-bg)',
                      borderRadius: 'var(--radius-md)',
                      marginBottom: 6,
                      fontSize: 12,
                      color: 'var(--color-on-surface)',
                      fontFamily: 'var(--font-data)',
                    }}>
                      <strong style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{cf.feature}</strong>
                      <span style={{ color: 'var(--color-on-surface-variant)' }}> → {cf.direction} it</span>
                      {cf.estimated_score_reduction && (
                        <span style={{
                          marginLeft: 8,
                          fontFamily: 'var(--font-mono)',
                          fontSize: 11,
                          color: 'var(--color-success)',
                        }}>
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
