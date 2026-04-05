/**
 * pages/PreCrimeAcquisitionPage.jsx — P9 Redesign
 *
 * Companies showing pre-acquisition signals before public announcements.
 * Uses DM Serif Display and DM Sans via external CSS classes. No inline styles.
 */

import { useEffect, useState } from 'react'
import { Eye, Trash2, Plus, Search, TrendingUp } from 'lucide-react'
import { watchlist, scores } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import {
  PageHeader,
  MetricCard,
  Panel,
  EmptyState,
  ErrorState,
} from '../components/ui/Primitives'
import './PreCrimeAcquisitionPage.css' // P10 styles

export default function PreCrimeAcquisitionPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [watchlistData, setWatchlistData] = useState([])
  const [topVelocity, setTopVelocity] = useState([])
  const [addInput, setAddInput] = useState('')
  const [addLoading, setAddLoading] = useState(false)
  const [addError, setAddError] = useState(null)
  const [removingIds, setRemovingIds] = useState({})
  const [watchingIds, setWatchingIds] = useState({})

  const load = () => {
    setLoading(true)
    setError(null)
    Promise.all([
      watchlist.list(),
      scores.topVelocity(20),
    ])
      .then(([wl, tv]) => {
        setWatchlistData(Array.isArray(wl) ? wl : (wl?.results || []))
        setTopVelocity(Array.isArray(tv) ? tv : [])
      })
      .catch(err => setError(err.message || 'Failed to load acquisition data'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleAddToWatchlist = (company_id, company_name) => {
    if (watchingIds[company_id]) return
    setWatchingIds(prev => ({ ...prev, [company_id]: true }))
    watchlist.add({ company_id, company_name })
      .then(newEntry => setWatchlistData(prev => {
        const exists = prev.some(w => (w.company_id || w.id) === company_id)
        if (exists) return prev
        return [...prev, newEntry || { company_id, company_name, added_at: new Date().toISOString() }]
      }))
      .catch(() => {})
      .finally(() => setWatchingIds(prev => ({ ...prev, [company_id]: false })))
  }

  const handleAddFromInput = (e) => {
    e.preventDefault()
    const name = addInput.trim()
    if (!name) return
    setAddLoading(true)
    setAddError(null)
    watchlist.add({ company_name: name })
      .then(newEntry => {
        setWatchlistData(prev => [...prev, newEntry || { company_name: name, added_at: new Date().toISOString() }])
        setAddInput('')
      })
      .catch(err => setAddError(err.message || 'Could not add company'))
      .finally(() => setAddLoading(false))
  }

  const handleRemove = (id) => {
    setRemovingIds(prev => ({ ...prev, [id]: true }))
    watchlist.remove(id)
      .then(() => setWatchlistData(prev => prev.filter(w => (w.id || w.watchlist_id || w.company_id) !== id)))
      .catch(() => {})
      .finally(() => setRemovingIds(prev => ({ ...prev, [id]: false })))
  }

  if (error) return (
    <AppShell>
      <div style={{ padding: '2rem' }}>
        <ErrorState message={error} onRetry={load} />
      </div>
    </AppShell>
  )

  const highVelocity = topVelocity.filter(v => (v.velocity_score || 0) > 0.7)
  const top10 = topVelocity.slice(0, 10)

  return (
    <AppShell>
      <div className="pca-root">
        <PageHeader
          tag="Acquisition Intelligence"
          title="Pre-Crime Acquisition Radar"
          subtitle="Companies showing pre-acquisition signals before public announcements"
        />

        {/* Metric cards */}
        <section className="pca-metrics">
          <MetricCard
            label="Watchlist"
            value={loading ? <Skeleton width={48} height={24} /> : watchlistData.length}
            accent="navy"
          />
          <MetricCard
            label="High Velocity"
            value={loading ? <Skeleton width={48} height={24} /> : highVelocity.length}
            accent="red"
          />
          <MetricCard
            label="New Signals"
            value="—"
            sub="Real-time via live feed"
            accent="gold"
          />
        </section>

        {/* Two-column layout */}
        <section className="pca-grid">
          {/* Left: Acquisition Targets (top velocity) */}
          <Panel title="Acquisition Targets">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Skeleton width="100%" height={32} />
                  </div>
                ))}
              </div>
            ) : top10.length === 0 ? (
              <EmptyState
                icon={<TrendingUp size={32} />}
                title="No acquisition targets"
                message="Velocity scoring will surface candidates once companies are scored."
              />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="pca-table">
                  <thead>
                    <tr>
                      {['#', 'Company', 'Velocity', 'Score', 'Action'].map(h => (
                        <th key={h} className="pca-th">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {top10.map((item, i) => {
                      const id = item.company_id
                      const name = item.company_name || item.name || ('Company ' + id)
                      const velocity = item.velocity_score || 0
                      const isWatching = watchingIds[id]
                      const alreadyWatched = watchlistData.some(
                        w => (w.company_id || w.id) === id
                      )
                      return (
                        <tr key={id || i} className="pca-tr">
                          <td className="pca-td pca-td-rank">{String(i + 1).padStart(2, '0')}</td>
                          <td className="pca-td pca-td-name">{name}</td>
                          <td className="pca-td">
                            <span className={velocity > 0 ? "pca-vel-badge-up" : "pca-vel-badge-down"}>
                              {velocity > 0 ? '↑' : '↓'} {Math.abs(velocity).toFixed(2)}
                            </span>
                          </td>
                          <td className="pca-td pca-td-score">
                            {item.composite_score != null
                              ? ((item.composite_score * 100).toFixed(1) + '%')
                              : '—'}
                          </td>
                          <td className="pca-td">
                            {alreadyWatched ? (
                              <span className="pca-tag-watching">Watching</span>
                            ) : (
                              <button
                                onClick={() => handleAddToWatchlist(id, name)}
                                disabled={isWatching || !id}
                                className="pca-btn-watch"
                              >
                                <Eye size={11} />
                                {isWatching ? 'Adding...' : 'Watch'}
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          {/* Right: Watchlist */}
          <Panel title="Your Watchlist">
            {/* Add company form */}
            <form onSubmit={handleAddFromInput} className="pca-search-form">
              <div className="pca-search-wrap">
                <Search size={14} className="pca-search-icon" />
                <input
                  type="text"
                  placeholder="Company name..."
                  value={addInput}
                  onChange={e => { setAddInput(e.target.value); setAddError(null) }}
                  className="pca-search-input"
                />
              </div>
              <button
                type="submit"
                disabled={addLoading || !addInput.trim()}
                className="pca-btn-add"
              >
                <Plus size={14} />
                {addLoading ? 'Adding...' : 'Add to Watchlist'}
              </button>
            </form>

            {addError && (
              <p style={{
                fontFamily: 'var(--font-data)',
                fontSize: '0.75rem',
                color: 'var(--color-error)',
                marginBottom: '0.75rem',
                marginTop: '-0.75rem',
              }}>{addError}</p>
            )}

            {/* Watchlist entries */}
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} width="100%" height={52} />
                ))}
              </div>
            ) : watchlistData.length === 0 ? (
              <EmptyState
                icon={<Eye size={32} />}
                title="Watchlist is empty"
                message="Add companies from the targets table or search above."
              />
            ) : (
              <div>
                {watchlistData.map((entry, i) => {
                  const id = entry.id || entry.watchlist_id || entry.company_id || i
                  const name = entry.company_name || entry.name || ('Company ' + id)
                  const addedAt = entry.added_at || entry.created_at
                  const isRemoving = removingIds[id]
                  return (
                    <div key={id} className="pca-watch-item">
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="pca-watch-name">{name}</div>
                        {addedAt && (
                          <div className="pca-watch-date">
                            Added {new Date(addedAt).toLocaleDateString('en-CA', {
                              year: 'numeric', month: 'short', day: 'numeric',
                            })}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => handleRemove(id)}
                        disabled={isRemoving}
                        title="Remove from watchlist"
                        className="pca-btn-remove"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </Panel>

        </section>
      </div>
    </AppShell>
  )
}
