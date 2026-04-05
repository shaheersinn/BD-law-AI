/**
 * pages/FeedbackPage.jsx — P23 Redesign
 *
 * Feedback Loop UI (Digital Atelier)
 * Three sections: Confirm a Mandate, Prediction Accuracy, Drift Alerts
 * Reborn with strict CSS injection and DM typography stack.
 */

import { useEffect, useState } from 'react'
import { companies as companiesApi, feedback as feedbackApi } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { SkeletonTable } from '../components/Skeleton'

const FEEDBACK_CSS = `
.fb-root {
  max-width: 860px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.fb-title {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 1.75rem;
  color: var(--color-primary);
  margin-bottom: 6px;
  margin-top: 0;
  letter-spacing: -0.01em;
}
.fb-subtitle {
  color: var(--color-on-surface-variant);
  font-size: 0.875rem;
  margin-bottom: 2.5rem;
  margin-top: 0;
  font-family: var(--font-data);
}
.fb-card {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-ambient);
  padding: 2rem;
  margin-bottom: 2rem;
}
.fb-card-title {
  font-family: var(--font-editorial);
  font-size: 1.5rem;
  font-weight: 500;
  color: var(--color-primary);
  margin-top: 0;
  margin-bottom: 4px;
  letter-spacing: -0.01em;
}
.fb-card-subtitle {
  color: var(--color-on-surface-variant);
  font-size: 0.8125rem;
  margin-bottom: 1.5rem;
  margin-top: 0;
  font-family: var(--font-data);
}

/* Forms */
.fb-input {
  width: 100%;
  padding: 10px 14px;
  outline: 1px solid rgba(197, 198, 206, 0.15);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  color: var(--color-on-surface);
  background: var(--color-surface-container-lowest);
  font-family: var(--font-data);
  box-sizing: border-box;
  margin-top: 4px;
  border: none;
  transition: outline-color var(--transition-fast);
}
.fb-input:focus {
  outline: 1px solid rgba(197, 198, 206, 0.40);
}
.fb-label {
  display: block;
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  margin-bottom: 2px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-family: var(--font-data);
}
.fb-btn-primary {
  background: linear-gradient(to bottom, var(--color-primary), var(--color-primary-container));
  color: var(--color-on-primary);
  border-radius: var(--radius-md);
  padding: 10px 24px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-data);
  border: none;
}
.fb-btn-primary:disabled {
  opacity: 0.6;
  cursor: default;
}

/* Alerts */
.fb-alert-success {
  background: var(--color-success-bg);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin-bottom: 1.25rem;
  font-size: 0.8125rem;
  color: var(--color-success);
  font-family: var(--font-data);
}
.fb-alert-error {
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin-bottom: 1.25rem;
  font-size: 0.8125rem;
  color: var(--color-error);
  font-family: var(--font-data);
}

/* Table */
.fb-table {
  width: 100%;
  border-collapse: collapse;
}
.fb-th {
  text-align: left;
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 14px;
  font-family: var(--font-data);
  background: var(--color-surface-container-low);
  white-space: nowrap;
}
.fb-td {
  padding: 13px 14px;
  font-size: 0.8125rem;
  color: var(--color-on-surface);
  vertical-align: middle;
  font-family: var(--font-data);
}
.fb-td-pa {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 0.875rem;
}
.fb-td-badge {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  background: var(--color-secondary-container);
  color: var(--color-on-secondary-container);
  border-radius: var(--radius-full);
  padding: 2px 8px;
}
.fb-td-mono {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}

/* Drift Alerts */
.fb-drift-item {
  border-left: 4px solid var(--color-on-surface-variant);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  margin-bottom: 1rem;
}
.fb-drift-title {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 1rem;
  color: var(--color-on-surface);
  margin-bottom: 4px;
  letter-spacing: -0.01em;
}
.fb-drift-meta {
  font-size: 0.75rem;
  color: var(--color-on-surface-variant);
  font-family: var(--font-data);
}
.fb-drift-val {
  font-family: var(--font-mono);
  font-size: 1.125rem;
  font-weight: 700;
}
.fb-drift-stat {
  display: flex;
  gap: 2rem;
  margin-top: 0.75rem;
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('fb-styles')) {
    const el = document.createElement('style')
    el.id = 'fb-styles'
    el.textContent = FEEDBACK_CSS
    document.head.appendChild(el)
  }
}

const PRACTICE_AREAS = [
  'ma_corporate', 'litigation_dispute_resolution', 'regulatory_compliance',
  'employment_labour', 'insolvency_restructuring', 'securities_capital_markets',
  'competition_antitrust', 'privacy_cybersecurity', 'environmental_indigenous_energy',
  'tax', 'real_estate_construction', 'banking_finance', 'intellectual_property',
  'immigration_corporate', 'infrastructure_project_finance', 'wills_estates',
  'administrative_public_law', 'arbitration_international_dispute', 'class_actions',
  'construction_infrastructure_disputes', 'defamation_media_law',
  'financial_regulatory_osfi_fintrac', 'franchise_distribution',
  'health_law_life_sciences', 'insurance_reinsurance', 'international_trade_customs',
  'mining_natural_resources', 'municipal_land_use', 'not_for_profit_charity',
  'pension_benefits', 'product_liability', 'sports_entertainment',
  'technology_fintech_regulatory', 'data_privacy_technology',
]

const PA_LABEL = (pa) => pa.replace(/_/g, ' ').replace(/\\b\\w/g, (c) => c.toUpperCase())

function ConfirmMandateForm() {
  const [companyQuery, setCompanyQuery]     = useState('')
  const [companyResults, setCompanyResults] = useState([])
  const [selectedCompany, setSelectedCompany] = useState(null)
  const [practiceArea, setPracticeArea]     = useState('')
  const [confirmedAt, setConfirmedAt]       = useState('')
  const [source, setSource]                 = useState('')
  const [evidenceUrl, setEvidenceUrl]       = useState('')
  const [notes, setNotes]                   = useState('')
  const [submitting, setSubmitting]         = useState(false)
  const [result, setResult]                 = useState(null)
  const [error, setError]                   = useState(null)

  const handleCompanySearch = async (e) => {
    const q = e.target.value
    setCompanyQuery(q)
    setSelectedCompany(null)
    if (q.trim().length < 2) { setCompanyResults([]); return }
    try {
      const data = await companiesApi.search(q.trim(), 8)
      setCompanyResults(data || [])
    } catch {
      setCompanyResults([])
    }
  }

  const selectCompany = (c) => {
    setSelectedCompany(c)
    setCompanyQuery(c.name)
    setCompanyResults([])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedCompany || !practiceArea || !confirmedAt || !source) return
    setSubmitting(true); setError(null); setResult(null)
    try {
      const res = await feedbackApi.confirmMandate({
        company_id: selectedCompany.id,
        practice_area: practiceArea,
        confirmed_at: confirmedAt,
        source,
        evidence_url: evidenceUrl || null,
        notes: notes || null,
      })
      setResult(res)
      setCompanyQuery(''); setSelectedCompany(null); setPracticeArea('')
      setConfirmedAt(''); setSource(''); setEvidenceUrl(''); setNotes('')
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fb-card">
      <h2 className="fb-card-title">Confirm a Mandate</h2>
      <p className="fb-card-subtitle">
        Record a confirmed mandate outcome. ORACLE will compute how many days in advance it predicted this.
      </p>

      {result && <div className="fb-alert-success">{result.message}</div>}
      {error && <div className="fb-alert-error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
          <div style={{ gridColumn: '1 / -1', position: 'relative' }}>
            <label className="fb-label">Company</label>
            <input
              value={companyQuery}
              onChange={handleCompanySearch}
              placeholder="Search by name…"
              required
              className="fb-input"
            />
            {companyResults.length > 0 && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: 'var(--color-surface-container-lowest)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-ambient)', zIndex: 10, maxHeight: 200, overflowY: 'auto' }}>
                {companyResults.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => selectCompany(c)}
                    style={{ display: 'block', width: '100%', textAlign: 'left', padding: '10px 14px', background: 'none', border: 'none', fontSize: 13, color: 'var(--color-on-surface)', cursor: 'pointer', fontFamily: 'var(--font-data)' }}
                  >
                    {c.name}
                    {c.sector && <span style={{ color: 'var(--color-on-surface-variant)', marginLeft: 8, fontSize: 11 }}>{c.sector}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="fb-label">Practice Area</label>
            <select
              value={practiceArea}
              onChange={(e) => setPracticeArea(e.target.value)}
              required
              className="fb-input"
            >
              <option value="">Select…</option>
              {PRACTICE_AREAS.map((pa) => (
                <option key={pa} value={pa}>{PA_LABEL(pa)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="fb-label">Date Confirmed</label>
            <input
              type="date"
              value={confirmedAt}
              onChange={(e) => setConfirmedAt(e.target.value)}
              required
              className="fb-input"
            />
          </div>

          <div>
            <label className="fb-label">Source</label>
            <input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="e.g. CanLII, Law firm press release…"
              required
              className="fb-input"
            />
          </div>

          <div>
            <label className="fb-label">Evidence URL (optional)</label>
            <input
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              placeholder="https://…"
              className="fb-input"
            />
          </div>

          <div style={{ gridColumn: '1 / -1' }}>
            <label className="fb-label">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Additional context…"
              className="fb-input"
              style={{ resize: 'vertical' }}
            />
          </div>
        </div>

        <div style={{ marginTop: '1.25rem' }}>
          <button type="submit" className="fb-btn-primary" disabled={submitting || !selectedCompany}>
            {submitting ? 'Saving…' : 'Confirm Mandate'}
          </button>
        </div>
      </form>
    </div>
  )
}

function AccuracyTable() {
  const [rows, setRows]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays]       = useState(90)

  useEffect(() => {
    setLoading(true)
    feedbackApi.accuracy(days)
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [days])

  const precisionColor = (p) => {
    if (p >= 0.7) return 'var(--color-success)'
    if (p >= 0.5) return 'var(--color-warning)'
    return 'var(--color-error)'
  }

  return (
    <div className="fb-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1.25rem' }}>
        <div>
          <h2 className="fb-card-title">Prediction Accuracy</h2>
          <p className="fb-card-subtitle">How often ORACLE's predictions were correct before confirmed mandates</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="fb-input"
          style={{ width: 'auto', marginTop: 0 }}
        >
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={180}>Last 180 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      {loading ? (
        <SkeletonTable rows={6} />
      ) : !rows || rows.length === 0 ? (
        <p style={{ color: 'var(--color-on-surface-variant)', fontSize: 13, textAlign: 'center', padding: '2rem 0', fontFamily: 'var(--font-data)' }}>
          No confirmed mandates in this window yet. Confirm mandates above to start tracking accuracy.
        </p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="fb-table">
            <thead>
              <tr>
                <th className="fb-th">Practice Area</th>
                <th className="fb-th" style={{ textAlign: 'center' }}>Horizon</th>
                <th className="fb-th" style={{ textAlign: 'center' }}>Confirmed</th>
                <th className="fb-th" style={{ textAlign: 'center' }}>Precision</th>
                <th className="fb-th" style={{ textAlign: 'center' }}>Avg Lead Days</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-container-low)' }}>
                  <td className="fb-td">
                    <span className="fb-td-pa">{PA_LABEL(r.practice_area)}</span>
                  </td>
                  <td className="fb-td" style={{ textAlign: 'center' }}>
                    <span className="fb-td-badge">{r.horizon}d</span>
                  </td>
                  <td className="fb-td fb-td-mono" style={{ textAlign: 'center' }}>
                    {r.n_total}
                  </td>
                  <td className="fb-td" style={{ textAlign: 'center' }}>
                    <span className="fb-td-mono" style={{ fontWeight: 600, color: precisionColor(r.precision) }}>
                      {(r.precision * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="fb-td fb-td-mono" style={{ textAlign: 'center', color: 'var(--color-on-surface-variant)' }}>
                    {r.avg_lead_days != null ? `${r.avg_lead_days}d` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function DriftAlerts() {
  const [alerts, setAlerts] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    feedbackApi.drift()
      .then(setAlerts)
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false))
  }, [])

  const deltaColor = (delta) => delta < -0.15 ? 'var(--color-error)' : 'var(--color-warning)'
  const deltaBg = (delta) => delta < -0.15 ? 'var(--color-error-bg)' : '#fffbeb' /* warning bg fallback */

  return (
    <div className="fb-card">
      <h2 className="fb-card-title">Model Drift Alerts</h2>
      <p className="fb-card-subtitle">
        Practice areas where prediction accuracy has dropped &gt; 10 percentage points (detected by Agent 031 weekly)
      </p>

      {loading ? (
        <SkeletonTable rows={3} />
      ) : !alerts || alerts.length === 0 ? (
        <div className="fb-alert-success" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>✓</span>
          No open drift alerts. All practice areas are performing within expected accuracy bounds.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {alerts.map((a) => (
            <div
              key={a.id}
              className="fb-drift-item"
              style={{
                borderColor: deltaColor(a.delta),
                background: deltaBg(a.delta),
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="fb-drift-title">{PA_LABEL(a.practice_area)}</div>
                  <div className="fb-drift-meta">
                    Detected {a.detected_at ? new Date(a.detected_at).toLocaleDateString() : '—'}
                    {a.ks_pvalue != null && ` · KS p-value: ${a.ks_pvalue.toFixed(3)}`}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="fb-drift-val" style={{ color: deltaColor(a.delta) }}>
                    {(a.delta * 100).toFixed(1)}pp
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-on-surface-variant)' }}>accuracy change</div>
                </div>
              </div>
              <div className="fb-drift-stat">
                <div>
                  <span style={{ fontSize: 11, color: 'var(--color-on-surface-variant)', display: 'block', fontFamily: 'var(--font-data)' }}>Before</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600 }}>
                    {(a.accuracy_before * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span style={{ fontSize: 11, color: 'var(--color-on-surface-variant)', display: 'block', fontFamily: 'var(--font-data)' }}>After</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color: deltaColor(a.delta) }}>
                    {(a.accuracy_after * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span style={{ fontSize: 11, color: 'var(--color-on-surface-variant)', display: 'block', fontFamily: 'var(--font-data)' }}>Status</span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.05em', fontFamily: 'var(--font-data)' }}>
                    {a.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function FeedbackPage() {
  injectCSS()
  return (
    <AppShell>
      <div className="fb-root">
        <h1 className="fb-title">Mandate Feedback</h1>
        <p className="fb-subtitle">
          Close the intelligence loop — record outcomes, measure accuracy, track model drift.
        </p>

        <ConfirmMandateForm />
        <AccuracyTable />
        <DriftAlerts />
      </div>
    </AppShell>
  )
}
