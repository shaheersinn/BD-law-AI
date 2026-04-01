/**
 * pages/admin/OptimizationPage.jsx — Phase 12: Post-Launch Optimization dashboard.
 *
 * Admin-only. Three sections:
 *   1. Usage Report    — weekly snapshot (top companies, cache hit rate, p95)
 *   2. Score Quality   — 34 practice areas precision/recall, worst 5 highlighted
 *   3. Signal Overrides — list + inline form to add/remove human BD multipliers
 */

import { useEffect, useState } from 'react'
import AppShell from '../../components/layout/AppShell'
import { SkeletonTable, SkeletonCard } from '../../components/Skeleton'
import { optimization as optimizationApi } from '../../api/client'

/* ── Design tokens ─────────────────────────────────────────────────────────── */
const AMBER  = '#F59E0B'
const RED    = '#EF4444'
const GREEN  = 'var(--accent)'
const CARD   = { background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: '20px 24px', border: '1px solid var(--border)', marginBottom: 24 }
const TH     = { padding: '10px 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.08em', borderBottom: '1px solid var(--border)', textAlign: 'left', whiteSpace: 'nowrap' }
const TD     = { padding: '10px 14px', fontSize: 13, color: 'var(--text)', borderBottom: '1px solid var(--border)', fontFamily: 'var(--font-mono)' }

/* ── Section: Usage Report ─────────────────────────────────────────────────── */
function UsageReport() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    api.optimization.usageReport()
      .then(r => setData(r.data))
      .catch(e => {
        if (e.response?.status === 404) setData(null)
        else setError('Failed to load usage report')
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={CARD}>
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 600, color: 'var(--text)', marginBottom: 16 }}>
        Usage Report
      </h2>
      {loading && <SkeletonCard />}
      {error && <p style={{ color: RED, fontSize: 13 }}>{error}</p>}
      {!loading && !error && !data && (
        <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
          No usage report yet. Agent 033 runs every Monday 08:00 UTC.
        </p>
      )}
      {data && (
        <>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 20 }}>
            <Stat label="Week of" value={data.week_start} />
            <Stat label="Overall p95" value={data.p95_ms != null ? `${data.p95_ms.toFixed(0)}ms` : 'N/A'} alert={data.p95_ms > 300} />
            <Stat label="Overall p50" value={data.p50_ms != null ? `${data.p50_ms.toFixed(0)}ms` : 'N/A'} />
            <Stat label="Cache Hit Rate" value={data.cache_hit_rate != null ? `${(data.cache_hit_rate * 100).toFixed(1)}%` : 'N/A'} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {/* Top companies */}
            <div>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Top Companies Searched</h3>
              {(data.top_companies || []).length === 0 && <p style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>No data</p>}
              {(data.top_companies || []).slice(0, 10).map((c, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid var(--border)', fontSize: 12 }}>
                  <span style={{ color: 'var(--text)' }}>{c.name}</span>
                  <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{c.request_count}</span>
                </div>
              ))}
            </div>

            {/* Endpoint breakdown */}
            <div>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Slowest Endpoints (p95)</h3>
              {(data.endpoint_breakdown || []).length === 0 && <p style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>No data</p>}
              {(data.endpoint_breakdown || []).slice(0, 8).map((e, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid var(--border)', fontSize: 12 }}>
                  <span style={{ color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{e.endpoint.replace('/api/v1', '')}</span>
                  <span style={{ color: (e.p95_ms || 0) > 300 ? AMBER : 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{(e.p95_ms || 0).toFixed(0)}ms</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

/* ── Section: Score Quality ─────────────────────────────────────────────────── */
function ScoreQuality() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    optimizationApi.scoreQuality()
      .then(setData)
      .catch(e => {
        if (e.response?.status === 404) setData(null)
        else setError('Failed to load score quality report')
      })
      .finally(() => setLoading(false))
  }, [])

  const worstSet = new Set(data?.worst_five || [])

  return (
    <div style={CARD}>
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>
        Score Quality
      </h2>
      <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 16 }}>
        Per-practice-area precision from prediction_accuracy_log (last 30 days).
        Worst 5 highlighted in amber.
      </p>
      {loading && <SkeletonTable />}
      {error && <p style={{ color: RED, fontSize: 13 }}>{error}</p>}
      {!loading && !error && !data && (
        <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
          No score quality report yet. Requires Phase 9 feedback loop data.
        </p>
      )}
      {data && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={TH}>Practice Area</th>
                <th style={{ ...TH, textAlign: 'right' }}>Precision</th>
                <th style={{ ...TH, textAlign: 'right' }}>Avg Lead</th>
                <th style={{ ...TH, textAlign: 'right' }}>Samples</th>
                <th style={{ ...TH, textAlign: 'right' }}>Labels</th>
                <th style={TH}>Flags</th>
              </tr>
            </thead>
            <tbody>
              {(data.summary || []).map((row, i) => {
                const isWorst = worstSet.has(row.practice_area)
                return (
                  <tr key={i} style={{ background: isWorst ? 'rgba(245,158,11,0.05)' : undefined }}>
                    <td style={{ ...TD, color: isWorst ? AMBER : 'var(--text)', fontFamily: 'inherit', fontWeight: isWorst ? 600 : 400 }}>
                      {row.practice_area.replace(/_/g, ' ')}
                    </td>
                    <td style={{ ...TD, textAlign: 'right', color: row.precision == null ? 'var(--text-tertiary)' : row.precision < 0.5 ? RED : GREEN }}>
                      {row.precision != null ? (row.precision * 100).toFixed(1) + '%' : '—'}
                    </td>
                    <td style={{ ...TD, textAlign: 'right' }}>
                      {row.avg_lead_days != null ? row.avg_lead_days + 'd' : '—'}
                    </td>
                    <td style={{ ...TD, textAlign: 'right' }}>{row.sample_count}</td>
                    <td style={{ ...TD, textAlign: 'right' }}>{row.label_count ?? '—'}</td>
                    <td style={TD}>
                      {row.low_data_flag && <span style={{ fontSize: 11, background: 'rgba(245,158,11,0.15)', color: AMBER, padding: '2px 6px', borderRadius: 4 }}>Low data</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/* ── Section: Signal Overrides ──────────────────────────────────────────────── */
function SignalOverrides() {
  const [overrides, setOverrides] = useState([])
  const [loading, setLoading]     = useState(true)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState(null)
  const [form, setForm] = useState({ signal_type: '', practice_area: '', multiplier: 1.0, reason: '' })

  const load = () => {
    setLoading(true)
    api.optimization.listOverrides()
      .then(r => setOverrides(r.data))
      .catch(() => setError('Failed to load overrides'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.signal_type || !form.practice_area) return
    setSaving(true)
    setError(null)
    try {
      await optimizationApi.createOverride({
        signal_type: form.signal_type,
        practice_area: form.practice_area,
        multiplier: parseFloat(form.multiplier),
        reason: form.reason || null,
      })
      setForm({ signal_type: '', practice_area: '', multiplier: 1.0, reason: '' })
      load()
    } catch {
      setError('Failed to save override')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await optimizationApi.deleteOverride(id)
      load()
    } catch {
      setError('Failed to deactivate override')
    }
  }

  return (
    <div style={CARD}>
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>
        Signal Weight Overrides
      </h2>
      <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 16 }}>
        BD team multipliers applied after ML-calibrated weights. Human override wins.
        Multiplier 1.0 = no change. 2.0 = double weight. 0.1 = nearly ignore.
      </p>
      {error && <p style={{ color: RED, fontSize: 13, marginBottom: 12 }}>{error}</p>}

      {/* Add form */}
      <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 120px 1fr auto', gap: 10, marginBottom: 20, alignItems: 'end' }}>
        <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Signal Type
          <input
            value={form.signal_type}
            onChange={e => setForm(f => ({ ...f, signal_type: e.target.value }))}
            placeholder="e.g. sedar_material_change"
            style={inputStyle}
            required
          />
        </label>
        <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Practice Area
          <input
            value={form.practice_area}
            onChange={e => setForm(f => ({ ...f, practice_area: e.target.value }))}
            placeholder="e.g. Insolvency_Restructuring"
            style={inputStyle}
            required
          />
        </label>
        <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Multiplier
          <input
            type="number"
            min="0.01"
            max="5.0"
            step="0.1"
            value={form.multiplier}
            onChange={e => setForm(f => ({ ...f, multiplier: e.target.value }))}
            style={inputStyle}
            required
          />
        </label>
        <label style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Reason (optional)
          <input
            value={form.reason}
            onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
            placeholder="Why this override?"
            style={inputStyle}
          />
        </label>
        <button type="submit" disabled={saving} style={btnStyle}>
          {saving ? 'Saving…' : 'Add'}
        </button>
      </form>

      {/* Table */}
      {loading && <SkeletonTable />}
      {!loading && overrides.length === 0 && (
        <p style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>No active overrides.</p>
      )}
      {!loading && overrides.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={TH}>Signal Type</th>
              <th style={TH}>Practice Area</th>
              <th style={{ ...TH, textAlign: 'right' }}>Multiplier</th>
              <th style={TH}>Reason</th>
              <th style={TH}>Set</th>
              <th style={TH} />
            </tr>
          </thead>
          <tbody>
            {overrides.map(o => (
              <tr key={o.id}>
                <td style={{ ...TD, fontFamily: 'var(--font-mono)', fontSize: 12 }}>{o.signal_type}</td>
                <td style={{ ...TD, fontSize: 12 }}>{o.practice_area.replace(/_/g, ' ')}</td>
                <td style={{ ...TD, textAlign: 'right', color: o.multiplier > 1 ? GREEN : o.multiplier < 1 ? AMBER : 'var(--text)' }}>
                  ×{o.multiplier.toFixed(2)}
                </td>
                <td style={{ ...TD, fontSize: 12, color: 'var(--text-secondary)' }}>{o.reason || '—'}</td>
                <td style={{ ...TD, fontSize: 11, color: 'var(--text-tertiary)' }}>{o.created_at?.slice(0, 10)}</td>
                <td style={TD}>
                  <button
                    onClick={() => handleDelete(o.id)}
                    style={{ background: 'none', border: '1px solid var(--border)', borderRadius: 4, padding: '3px 8px', fontSize: 11, color: RED, cursor: 'pointer' }}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/* ── Shared helpers ─────────────────────────────────────────────────────────── */
const Stat = ({ label, value, alert }) => (
  <div style={{ minWidth: 120 }}>
    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 20, fontFamily: 'var(--font-mono)', fontWeight: 700, color: alert ? AMBER : 'var(--text)' }}>{value}</div>
  </div>
)

const inputStyle = {
  display: 'block',
  width: '100%',
  marginTop: 4,
  padding: '7px 10px',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-md)',
  fontSize: 13,
  background: 'var(--bg)',
  color: 'var(--text)',
  outline: 'none',
  fontFamily: 'var(--font-mono)',
}

const btnStyle = {
  padding: '8px 16px',
  background: 'var(--accent)',
  color: '#fff',
  border: 'none',
  borderRadius: 'var(--radius-md)',
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
  whiteSpace: 'nowrap',
}

/* ── Page ───────────────────────────────────────────────────────────────────── */
export default function OptimizationPage() {
  return (
    <AppShell>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 24px' }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 700, color: 'var(--text)', marginBottom: 6 }}>
            Post-Launch Optimization
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
            Usage analytics, score quality monitoring, and BD signal weight overrides.
          </p>
        </div>

        <UsageReport />
        <ScoreQuality />
        <SignalOverrides />
      </div>
    </AppShell>
  )
}
