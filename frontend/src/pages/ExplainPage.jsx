/**
 * pages/ExplainPage.jsx — P24 Redesign
 * 
 * Digital Atelier SHAP explanations.
 * Now standardized on DM Serif and DM Sans via injected CSS block.
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { scores as scoresApi } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { SkeletonCard } from '../components/Skeleton'

const EXP_CSS = `
.exp-root {
  max-width: 900px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.exp-back-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-on-surface-variant);
  font-size: 0.8125rem;
  padding: 0;
  margin-bottom: 1.5rem;
  font-family: var(--font-data);
}
.exp-back-btn:hover {
  color: var(--color-primary);
}
.exp-title {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 1.75rem;
  color: var(--color-primary);
  margin-bottom: 0.5rem;
  margin-top: 0;
  letter-spacing: -0.01em;
}
.exp-subtitle {
  color: var(--color-on-surface-variant);
  font-size: 0.8125rem;
  margin-bottom: 2rem;
  margin-top: 0;
  font-family: var(--font-data);
  letter-spacing: 0.01em;
}

/* Empty/Error states */
.exp-error {
  color: var(--color-error);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-size: 0.8125rem;
  font-family: var(--font-data);
}
.exp-empty {
  padding: 3rem 2rem;
  text-align: center;
  color: var(--color-on-surface-variant);
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-ambient);
  font-family: var(--font-data);
}

/* SHAP Cards */
.exp-card {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  padding: 1.5rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-ambient);
}
.exp-card-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 4px;
}
.exp-card-pa {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 1.125rem;
  color: var(--color-primary);
  text-transform: capitalize;
  letter-spacing: -0.01em;
}
.exp-card-score {
  font-family: var(--font-mono);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-on-surface);
}
.exp-card-meta {
  font-size: 0.6875rem;
  color: var(--color-on-surface-variant);
  margin-bottom: 1.25rem;
  font-family: var(--font-mono);
}

.exp-section-title {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 10px;
}
.exp-feature-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 12px;
  align-items: center;
  padding: 7px 8px;
  border-radius: var(--radius-md);
}
.exp-feature-name {
  font-size: 0.75rem;
  color: var(--color-on-surface);
  font-family: var(--font-data);
}

.exp-cf-item {
  padding: 8px 12px;
  background: var(--color-success-bg);
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  font-size: 0.75rem;
  color: var(--color-on-surface);
  font-family: var(--font-data);
}
.exp-cf-strong {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
}
.exp-cf-red {
  margin-left: 8px;
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  color: var(--color-success);
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('exp-styles')) {
    const el = document.createElement('style')
    el.id = 'exp-styles'
    el.textContent = EXP_CSS
    document.head.appendChild(el)
  }
}

function ShapBar({ value, maxAbs }) {
  const pct = (Math.abs(value) / maxAbs) * 100
  const colorToken = value >= 0 ? 'var(--color-secondary)' : 'var(--color-error)'
  const txtColor = value >= 0 ? 'var(--color-success)' : 'var(--color-error)'
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
          width: \`\${pct}%\`, height: '100%', borderRadius: 3,
          background: colorToken,
          transition: 'width 0.3s ease',
        }} />
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: txtColor,
        minWidth: 48,
        textAlign: 'right',
      }}>
        {value >= 0 ? '+' : ''}{value?.toFixed(3)}
      </span>
    </div>
  )
}

export default function ExplainPage() {
  injectCSS()
  const { id } = useParams()
  const navigate = useNavigate()
  const [explanations, setExplanations] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    scoresApi.explain(id)
      .then(setExplanations)
      .catch((err) => setError(err.message || 'Failed to load explanations'))
      .finally(() => setLoading(false))
  }, [id])

  return (
    <AppShell>
      <div className="exp-root">
        <button className="exp-back-btn" onClick={() => navigate(\`/companies/\${id}\`)}>
          ← Company Detail
        </button>

        <h1 className="exp-title">SHAP Explanations</h1>
        <p className="exp-subtitle">Feature contributions for the top 5 highest-scoring practice areas</p>

        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} height={160} />)}
          </div>
        )}

        {error && <div className="exp-error">{error}</div>}

        {!loading && !error && !explanations?.length && (
          <div className="exp-empty">
            <div style={{ fontSize: 24, marginBottom: 8 }}>📊</div>
            <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--color-on-surface)' }}>No explanations available</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>Scores must reach 40%+ threshold before SHAP explanations are generated.</div>
          </div>
        )}

        {!loading && explanations?.map((exp, i) => {
          const maxAbs = Math.max(...(exp.top_shap_features?.map(f => Math.abs(f.shap_value)) || [1]))
          return (
            <div key={i} className="exp-card">
              <div className="exp-card-header">
                <div className="exp-card-pa">{exp.practice_area?.replace(/_/g, ' ')}</div>
                <div className="exp-card-score">{(exp.score * 100).toFixed(1)}%</div>
              </div>
              <div className="exp-card-meta">
                {exp.horizon}d horizon{exp.base_value != null ? \` · base \${(exp.base_value * 100).toFixed(1)}%\` : ''}
              </div>

              {exp.top_shap_features?.length > 0 && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <div className="exp-section-title">Feature Contributions</div>
                  {exp.top_shap_features.map((f, j) => (
                    <div key={j} className="exp-feature-row" style={{ background: j % 2 === 0 ? 'transparent' : 'var(--color-surface-container-low)' }}>
                      <span className="exp-feature-name">{f.feature}</span>
                      <ShapBar value={f.shap_value} maxAbs={maxAbs} />
                    </div>
                  ))}
                </div>
              )}

              {exp.counterfactuals?.length > 0 && (
                <div>
                  <div className="exp-section-title">What Would Lower This Score</div>
                  {exp.counterfactuals.map((cf, j) => (
                    <div key={j} className="exp-cf-item">
                      <strong className="exp-cf-strong">{cf.feature}</strong>
                      <span style={{ color: 'var(--color-on-surface-variant)' }}> → {cf.direction} it</span>
                      {cf.estimated_score_reduction && (
                        <span className="exp-cf-red">
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
