/**
 * pages/FeedbackPage.jsx — Phase 9: Feedback Loop UI (Digital Atelier)
 *
 * Three sections:
 *   1. Confirm a Mandate — partner form to record confirmed outcomes
 *   2. Prediction Accuracy — precision/lead-days table per practice area
 *   3. Drift Alerts — open model degradation warnings from Agent 031
 *
 * Route: /feedback  (require_partner via PrivateRoute)
 */

import { useEffect, useState } from 'react'
import { companies as companiesApi, feedback as feedbackApi } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { SkeletonTable } from '../components/Skeleton'

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

const PA_LABEL = (pa) =>
  pa.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

// ── Shared styles ──────────────────────────────────────────────────────────────

const card = {
  background: 'var(--color-surface-container-lowest)',
  borderRadius: 'var(--radius-xl)',
  boxShadow: 'var(--shadow-ambient)',
  padding: '2rem',
  marginBottom: '2rem',
}

const inputStyle = {
  width: '100%',
  padding: '10px 14px',
  outline: '1px solid rgba(197, 198, 206, 0.15)',
  borderRadius: 'var(--radius-md)',
  fontSize: 14,
  color: 'var(--color-on-surface)',
  background: 'var(--color-surface-container-lowest)',
  fontFamily: 'var(--font-data)',
  boxSizing: 'border-box',
  marginTop: 4,
}

const labelStyle = {
  display: 'block',
  fontSize: '0.6875rem',
  fontWeight: 700,
  color: 'var(--color-on-surface-variant)',
  marginBottom: 2,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
  fontFamily: 'var(--font-data)',
}

const btnPrimary = {
  background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
  color: 'var(--color-on-primary)',
  borderRadius: 'var(--radius-md)',
  padding: '10px 24px',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
  fontFamily: 'var(--font-data)',
}

const th = {
  textAlign: 'left',
  fontSize: '0.6875rem',
  fontWeight: 700,
  color: 'var(--color-on-surface-variant)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  paddingBottom: 10,
  fontFamily: 'var(--font-data)',
  background: 'var(--color-surface-container-low)',
  padding: '10px 14px',
}

const td = {
  padding: '10px 14px',
  fontSize: 13,
  color: 'var(--color-on-surface)',
  verticalAlign: 'middle',
  fontFamily: 'var(--font-data)',
}

// ── Section 1: Confirm a Mandate ──────────────────────────────────────────────

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
    <div style={card}>
      <h2 style={{ fontFamily: 'var(--font-editorial)', fontSize: '1.5rem', fontWeight: 500, color: 'var(--color-primary)', marginTop: 0, marginBottom: 4, letterSpacing: '-0.01em' }}>
        Confirm a Mandate
      </h2>
      <p style={{ color: 'var(--color-on-surface-variant)', fontSize: 13, marginBottom: '1.5rem', marginTop: 0, fontFamily: 'var(--font-data)' }}>
        Record a confirmed mandate outcome. ORACLE will compute how many days in advance it predicted this.
      </p>

      {result && (
        <div style={{ background: 'var(--color-success-bg)', borderRadius: 'var(--radius-md)', padding: '12px 16px', marginBottom: '1.25rem', fontSize: 13, color: 'var(--color-success)', fontFamily: 'var(--font-data)' }}>
          {result.message}
        </div>
      )}
      {error && (
        <div style={{ background: 'var(--color-error-bg)', borderRadius: 'var(--radius-md)', padding: '12px 16px', marginBottom: '1.25rem', fontSize: 13, color: 'var(--color-error)', fontFamily: 'var(--font-data)' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>

          {/* Company search */}
          <div style={{ gridColumn: '1 / -1', position: 'relative' }}>
            <label style={labelStyle}>Company</label>
            <input
              value={companyQuery}
              onChange={handleCompanySearch}
              placeholder="Search by name…"
              required
              style={inputStyle}
            />
            {companyResults.length > 0 && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, background: 'var(--color-surface-container-lowest)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-ambient)', zIndex: 10, maxHeight: 200, overflowY: 'auto' }}>
                {companyResults.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => selectCompany(c)}
                    style={{ display: 'block', width: '100%', textAlign: 'left', padding: '10px 14px', background: 'none', fontSize: 13, color: 'var(--color-on-surface)', cursor: 'pointer', fontFamily: 'var(--font-data)' }}
                  >
                    {c.name}
                    {c.sector && <span style={{ color: 'var(--color-on-surface-variant)', marginLeft: 8, fontSize: 11 }}>{c.sector}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Practice area */}
          <div>
            <label style={labelStyle}>Practice Area</label>
            <select
              value={practiceArea}
              onChange={(e) => setPracticeArea(e.target.value)}
              required
              style={{ ...inputStyle, appearance: 'none' }}
            >
              <option value="">Select…</option>
              {PRACTICE_AREAS.map((pa) => (
                <option key={pa} value={pa}>{PA_LABEL(pa)}</option>
              ))}
            </select>
          </div>

          {/* Date confirmed */}
          <div>
            <label style={labelStyle}>Date Confirmed</label>
            <input
              type="date"
              value={confirmedAt}
              onChange={(e) => setConfirmedAt(e.target.value)}
              required
              style={inputStyle}
            />
          </div>

          {/* Source */}
          <div>
            <label style={labelStyle}>Source</label>
            <input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="e.g. CanLII, Law firm press release…"
              required
              style={inputStyle}
            />
          </div>

          {/* Evidence URL */}
          <div>
            <label style={labelStyle}>Evidence URL (optional)</label>
            <input
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              placeholder="https://…"
              style={inputStyle}
            />
          </div>

          {/* Notes */}
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={labelStyle}>Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Additional context…"
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </div>
        </div>

        <div style={{ marginTop: '1.25rem' }}>
          <button type="submit" style={btnPrimary} disabled={submitting || !selectedCompany}>
            {submitting ? 'Saving…' : 'Confirm Mandate'}
          </button>
        </div>
      </form>
    </div>
  )
}

// ── Section 2: Accuracy Table ─────────────────────────────────────────────────

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
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-editorial)', fontSize: '1.5rem', fontWeight: 500, color: 'var(--color-primary)', margin: 0, letterSpacing: '-0.01em' }}>
            Prediction Accuracy
          </h2>
          <p style={{ color: 'var(--color-on-surface-variant)', fontSize: 13, marginTop: 4, marginBottom: 0, fontFamily: 'var(--font-data)' }}>
            How often ORACLE's predictions were correct before confirmed mandates
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          style={{ ...inputStyle, width: 'auto', marginTop: 0 }}
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
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={th}>Practice Area</th>
              <th style={{ ...th, textAlign: 'center' }}>Horizon</th>
              <th style={{ ...th, textAlign: 'center' }}>Confirmed</th>
              <th style={{ ...th, textAlign: 'center' }}>Precision</th>
              <th style={{ ...th, textAlign: 'center' }}>Avg Lead Days</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-container-low)' }}>
                <td style={td}>
                  <span style={{ fontFamily: 'var(--font-editorial)', fontWeight: 500, fontSize: 14 }}>
                    {PA_LABEL(r.practice_area)}
                  </span>
                </td>
                <td style={{ ...td, textAlign: 'center' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, background: 'var(--color-secondary-container)', color: 'var(--color-on-secondary-container)', borderRadius: 'var(--radius-full)', padding: '2px 8px' }}>
                    {r.horizon}d
                  </span>
                </td>
                <td style={{ ...td, textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                  {r.n_total}
                </td>
                <td style={{ ...td, textAlign: 'center' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color: precisionColor(r.precision) }}>
                    {(r.precision * 100).toFixed(0)}%
                  </span>
                </td>
                <td style={{ ...td, textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-on-surface-variant)' }}>
                  {r.avg_lead_days != null ? `${r.avg_lead_days}d` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── Section 3: Drift Alerts ───────────────────────────────────────────────────

function DriftAlerts() {
  const [alerts, setAlerts] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    feedbackApi.drift()
      .then(setAlerts)
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false))
  }, [])

  const deltaColor = (delta) => delta < -0.15 ? 'var(--error)' : 'var(--warning)'

  return (
    <div style={card}>
      <h2 style={{ fontFamily: 'var(--font-editorial)', fontSize: '1.5rem', fontWeight: 500, color: 'var(--color-primary)', marginTop: 0, marginBottom: 4, letterSpacing: '-0.01em' }}>
        Model Drift Alerts
      </h2>
      <p style={{ color: 'var(--color-on-surface-variant)', fontSize: 13, marginBottom: '1.5rem', marginTop: 0, fontFamily: 'var(--font-data)' }}>
        Practice areas where prediction accuracy has dropped &gt; 10 percentage points (detected by Agent 031 weekly)
      </p>

      {loading ? (
        <SkeletonTable rows={3} />
      ) : !alerts || alerts.length === 0 ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '1.25rem 1.5rem', background: 'var(--color-success-bg)', borderRadius: 'var(--radius-md)', color: 'var(--color-success)', fontSize: 13, fontFamily: 'var(--font-data)' }}>
          <span style={{ fontSize: 18 }}>&#10003;</span>
          No open drift alerts. All practice areas are performing within expected accuracy bounds.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {alerts.map((a) => (
            <div
              key={a.id}
              style={{
                borderLeft: `4px solid ${deltaColor(a.delta)}`,
                background: a.delta < -0.15 ? 'var(--error-bg)' : 'var(--warning-bg)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem 1.25rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontFamily: 'var(--font-editorial)', fontWeight: 500, fontSize: 16, color: 'var(--color-on-surface)', marginBottom: 4, letterSpacing: '-0.01em' }}>
                    {PA_LABEL(a.practice_area)}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)' }}>
                    Detected {a.detected_at ? new Date(a.detected_at).toLocaleDateString() : '—'}
                    {a.ks_pvalue != null && ` · KS p-value: ${a.ks_pvalue.toFixed(3)}`}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: deltaColor(a.delta) }}>
                    {(a.delta * 100).toFixed(1)}pp
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-on-surface-variant)' }}>accuracy change</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '2rem', marginTop: '0.75rem' }}>
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function FeedbackPage() {
  return (
    <AppShell>
      <div style={{ maxWidth: 860, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <h1 style={{
          fontFamily: 'var(--font-editorial)',
          fontWeight: 500,
          fontSize: '1.75rem',
          color: 'var(--color-primary)',
          marginBottom: 6,
          marginTop: 0,
          letterSpacing: '-0.01em',
        }}>
          Mandate Feedback
        </h1>
        <p style={{ color: 'var(--color-on-surface-variant)', fontSize: 14, marginBottom: '2.5rem', marginTop: 0, fontFamily: 'var(--font-data)' }}>
          Close the intelligence loop — record outcomes, measure accuracy, track model drift.
        </p>

        <ConfirmMandateForm />
        <AccuracyTable />
        <DriftAlerts />
      </div>
    </AppShell>
  )
}
