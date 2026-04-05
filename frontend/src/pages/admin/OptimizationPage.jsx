/**
 * pages/admin/OptimizationPage.jsx — Admin UI Update
 * Post-Launch Optimization dashboard (Admin-only).
 * Refactored colors/fonts to strictly use the DM stack (injected via CSS).
 */

import { useEffect, useState } from 'react'
import AppShell from '../../components/layout/AppShell'
import { SkeletonTable, SkeletonCard } from '../../components/Skeleton'
import { optimization as optimizationApi } from '../../api/client'

const OPT_CSS = `
.opt-root {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.opt-title {
  font-family: var(--font-editorial);
  font-size: 1.75rem;
  font-weight: 500;
  color: var(--color-primary);
  margin-bottom: 6px;
  margin-top: 0;
  letter-spacing: -0.01em;
}
.opt-subtitle {
  font-size: 0.875rem;
  color: var(--color-on-surface-variant);
  font-family: var(--font-data);
  margin-bottom: 2rem;
}

.opt-card {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-ambient);
}
.opt-card-title {
  font-family: var(--font-editorial);
  font-size: 1.5rem;
  font-weight: 500;
  color: var(--color-primary);
  margin-top: 0;
  margin-bottom: 8px;
  letter-spacing: -0.01em;
}

.opt-table {
  width: 100%;
  border-collapse: collapse;
}
.opt-th {
  padding: 10px 14px;
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--color-surface-container-low);
  text-align: left;
  white-space: nowrap;
  font-family: var(--font-data);
}
.opt-td {
  padding: 10px 14px;
  font-size: 0.8125rem;
  color: var(--color-on-surface);
  font-family: var(--font-mono);
}

.opt-input {
  display: block;
  width: 100%;
  margin-top: 4px;
  padding: 8px 12px;
  border: 1px solid rgba(197, 198, 206, 0.15);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  background: var(--color-surface-container-lowest);
  color: var(--color-on-surface);
  outline: none;
  font-family: var(--font-data);
  transition: border-color var(--transition-fast);
}
.opt-input:focus {
  border-color: rgba(197, 198, 206, 0.4);
}

.opt-btn {
  padding: 8px 16px;
  background: linear-gradient(to bottom, var(--color-primary), var(--color-primary-container));
  color: var(--color-on-primary);
  border: none;
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  font-family: var(--font-data);
}
.opt-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.opt-btn-text {
  background: none;
  border: 1px solid rgba(197, 198, 206, 0.2);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 0.6875rem;
  color: var(--color-error);
  cursor: pointer;
  font-family: var(--font-data);
  font-weight: 600;
}
.opt-btn-text:hover {
  background: var(--color-error-bg);
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('opt-styles')) {
    const el = document.createElement('style')
    el.id = 'opt-styles'
    el.textContent = OPT_CSS
    document.head.appendChild(el)
  }
}

/* ── Section: Usage Report ─────────────────────────────────────────────────── */
function UsageReport() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    optimizationApi.usageReport()
      .then(r => setData(r.data ? r.data : r))
      .catch(e => {
        if (e.response?.status === 404) setData(null)
        else setError('Failed to load usage report')
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="opt-card">
      <h2 className="opt-card-title">Usage Report</h2>
      {loading && <SkeletonCard />}
      {error && <p style={{ color: 'var(--color-error)', fontSize: 13, fontFamily: 'var(--font-data)' }}>{error}</p>}
      {!loading && !error && !data && (
        <p style={{ color: 'var(--color-on-surface-variant)', fontSize: 13, fontFamily: 'var(--font-data)' }}>
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

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: 20 }}>
            <div>
              <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-on-surface-variant)', marginBottom: 8, fontFamily: 'var(--font-data)' }}>Top Companies Searched</h3>
              {(data.top_companies || []).length === 0 && <p style={{ fontSize: 12, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)' }}>No data</p>}
              {(data.top_companies || []).slice(0, 10).map((c, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid var(--color-surface-container-high)', fontSize: 12 }}>
                  <span style={{ color: 'var(--color-on-surface)', fontFamily: 'var(--font-data)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</span>
                  <span style={{ color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-mono)' }}>{c.request_count}</span>
                </div>
              ))}
            </div>

            <div>
              <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-on-surface-variant)', marginBottom: 8, fontFamily: 'var(--font-data)' }}>Slowest Endpoints (p95)</h3>
              {(data.endpoint_breakdown || []).length === 0 && <p style={{ fontSize: 12, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)' }}>No data</p>}
              {(data.endpoint_breakdown || []).slice(0, 8).map((e, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid var(--color-surface-container-high)', fontSize: 12 }}>
                  <span style={{ color: 'var(--color-on-surface)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{e.endpoint.replace('/api/v1', '')}</span>
                  <span style={{ color: (e.p95_ms || 0) > 300 ? 'var(--color-warning)' : 'var(--color-on-surface-variant)', fontFamily: 'var(--font-mono)' }}>{(e.p95_ms || 0).toFixed(0)}ms</span>
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
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    optimizationApi.scoreQuality()
      .then(r => setData(r.data ? r.data : r))
      .catch(e => {
        if (e.response?.status === 404) setData(null)
        else setError('Failed to load score quality report')
      })
      .finally(() => setLoading(false))
  }, [])

  const worstSet = new Set(data?.worst_five || [])

  return (
    <div className="opt-card">
      <h2 className="opt-card-title">Score Quality</h2>
      <p style={{ fontSize: 12, color: 'var(--color-on-surface-variant)', marginBottom: 16, fontFamily: 'var(--font-data)' }}>
        Per-practice-area precision from prediction_accuracy_log (last 30 days).
        Worst 5 highlighted in amber.
      </p>
      {loading && <SkeletonTable />}
      {error && <p style={{ color: 'var(--color-error)', fontSize: 13, fontFamily: 'var(--font-data)' }}>{error}</p>}
      {!loading && !error && !data && (
        <p style={{ color: 'var(--color-on-surface-variant)', fontSize: 13, fontFamily: 'var(--font-data)' }}>
          No score quality report yet. Requires Phase 9 feedback loop data.
        </p>
      )}
      {data && (
        <div style={{ overflowX: 'auto' }}>
          <table className="opt-table">
            <thead>
              <tr>
                <th className="opt-th">Practice Area</th>
                <th className="opt-th" style={{ textAlign: 'right' }}>Precision</th>
                <th className="opt-th" style={{ textAlign: 'right' }}>Avg Lead</th>
                <th className="opt-th" style={{ textAlign: 'right' }}>Samples</th>
                <th className="opt-th" style={{ textAlign: 'right' }}>Labels</th>
                <th className="opt-th">Flags</th>
              </tr>
            </thead>
            <tbody>
              {(data.summary || []).map((row, i) => {
                const isWorst = worstSet.has(row.practice_area)
                return (
                  <tr key={i} style={{ background: isWorst ? 'var(--color-warning-bg)' : i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent' }}>
                    <td className="opt-td" style={{ color: isWorst ? 'var(--color-warning)' : 'var(--color-on-surface)', fontFamily: 'var(--font-editorial)', fontWeight: 500 }}>
                      {row.practice_area.replace(/_/g, ' ')}
                    </td>
                    <td className="opt-td" style={{ textAlign: 'right', color: row.precision == null ? 'var(--color-on-surface-variant)' : row.precision < 0.5 ? 'var(--color-error)' : 'var(--color-success)' }}>
                      {row.precision != null ? (row.precision * 100).toFixed(1) + '%' : '—'}
                    </td>
                    <td className="opt-td" style={{ textAlign: 'right' }}>
                      {row.avg_lead_days != null ? row.avg_lead_days + 'd' : '—'}
                    </td>
                    <td className="opt-td" style={{ textAlign: 'right' }}>{row.sample_count}</td>
                    <td className="opt-td" style={{ textAlign: 'right' }}>{row.label_count ?? '—'}</td>
                    <td className="opt-td">
                      {row.low_data_flag && <span style={{ fontSize: 11, background: 'var(--color-warning-bg)', color: 'var(--color-warning)', padding: '2px 6px', borderRadius: 4, fontFamily: 'var(--font-data)' }}>Low data</span>}
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
    optimizationApi.listOverrides()
      .then(r => setOverrides(r.data ? r.data : r))
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
    <div className="opt-card">
      <h2 className="opt-card-title">Signal Weight Overrides</h2>
      <p style={{ fontSize: 12, color: 'var(--color-on-surface-variant)', marginBottom: 16, fontFamily: 'var(--font-data)' }}>
        BD team multipliers applied after ML-calibrated weights. Human override wins.
        Multiplier 1.0 = no change. 2.0 = double weight. 0.1 = nearly ignore.
      </p>
      {error && <p style={{ color: 'var(--color-error)', fontSize: 13, marginBottom: 12, fontFamily: 'var(--font-data)' }}>{error}</p>}

      {/* Add form */}
      <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr) 100px minmax(0,1fr) auto', gap: 10, marginBottom: 20, alignItems: 'end' }}>
        <label style={{ fontSize: 11, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)', fontWeight: 700, textTransform: 'uppercase' }}>
          Signal Type
          <input
            value={form.signal_type}
            onChange={e => setForm(f => ({ ...f, signal_type: e.target.value }))}
            placeholder="e.g. sedar_material_change"
            className="opt-input"
            required
          />
        </label>
        <label style={{ fontSize: 11, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)', fontWeight: 700, textTransform: 'uppercase' }}>
          Practice Area
          <input
            value={form.practice_area}
            onChange={e => setForm(f => ({ ...f, practice_area: e.target.value }))}
            placeholder="e.g. Insolvency_Restructuring"
            className="opt-input"
            required
          />
        </label>
        <label style={{ fontSize: 11, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)', fontWeight: 700, textTransform: 'uppercase' }}>
          Multiplier
          <input
            type="number"
            min="0.01"
            max="5.0"
            step="0.1"
            value={form.multiplier}
            onChange={e => setForm(f => ({ ...f, multiplier: e.target.value }))}
            className="opt-input"
            required
          />
        </label>
        <label style={{ fontSize: 11, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)', fontWeight: 700, textTransform: 'uppercase' }}>
          Reason (opt)
          <input
            value={form.reason}
            onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
            placeholder="Why this override?"
            className="opt-input"
          />
        </label>
        <button type="submit" disabled={saving} className="opt-btn">
          {saving ? '…' : 'Add'}
        </button>
      </form>

      {/* Table */}
      {loading && <SkeletonTable />}
      {!loading && overrides.length === 0 && (
        <p style={{ fontSize: 13, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-data)' }}>No active overrides.</p>
      )}
      {!loading && overrides.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table className="opt-table">
            <thead>
              <tr>
                <th className="opt-th">Signal Type</th>
                <th className="opt-th">Practice Area</th>
                <th className="opt-th" style={{ textAlign: 'right' }}>Multiplier</th>
                <th className="opt-th">Reason</th>
                <th className="opt-th">Set</th>
                <th className="opt-th" />
              </tr>
            </thead>
            <tbody>
              {overrides.map((o, i) => (
                <tr key={o.id} style={{ background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent' }}>
                  <td className="opt-td">{o.signal_type}</td>
                  <td className="opt-td" style={{ fontFamily: 'var(--font-data)' }}>{o.practice_area.replace(/_/g, ' ')}</td>
                  <td className="opt-td" style={{ textAlign: 'right', color: o.multiplier > 1 ? 'var(--color-success)' : o.multiplier < 1 ? 'var(--color-warning)' : 'var(--color-on-surface)' }}>
                    ×{o.multiplier.toFixed(2)}
                  </td>
                  <td className="opt-td" style={{ fontFamily: 'var(--font-data)', color: 'var(--color-on-surface-variant)' }}>{o.reason || '—'}</td>
                  <td className="opt-td" style={{ fontSize: 11, color: 'var(--color-on-surface-variant)' }}>{o.created_at?.slice(0, 10)}</td>
                  <td className="opt-td">
                    <button onClick={() => handleDelete(o.id)} className="opt-btn-text">Remove</button>
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

/* ── Shared helpers ─────────────────────────────────────────────────────────── */
const Stat = ({ label, value, alert }) => (
  <div style={{ minWidth: 120 }}>
    <div style={{ fontSize: '0.6875rem', color: 'var(--color-on-surface-variant)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4, fontFamily: 'var(--font-data)', fontWeight: 700 }}>{label}</div>
    <div style={{ fontSize: '1.25rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: alert ? 'var(--color-warning)' : 'var(--color-on-surface)' }}>{value}</div>
  </div>
)

/* ── Page ───────────────────────────────────────────────────────────────────── */
export default function OptimizationPage() {
  injectCSS()
  return (
    <AppShell>
      <div className="opt-root">
        <h1 className="opt-title">Post-Launch Optimization</h1>
        <p className="opt-subtitle">
          Usage analytics, score quality monitoring, and BD signal weight overrides.
        </p>

        <UsageReport />
        <ScoreQuality />
        <SignalOverrides />
      </div>
    </AppShell>
  )
}
