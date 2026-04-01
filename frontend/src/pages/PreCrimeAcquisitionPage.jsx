/**
 * pages/PreCrimeAcquisitionPage.jsx — route /precrime
 *
 * Companies showing pre-acquisition signals before public announcements.
 * Data: watchlist.list(), scores.topVelocity(), watchlist.add/remove()
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
  Tag,
  EmptyState,
  ErrorState,
} from '../components/ui/Primitives'

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
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>

        <PageHeader
          tag="Acquisition Intelligence"
          title="Pre-Crime Acquisition Radar"
          subtitle="Companies showing pre-acquisition signals before public announcements"
        />

        {/* Metric cards */}
        <section style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '1.25rem',
          marginBottom: '2.5rem',
        }}>
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
        <section style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '2rem',
        }}>

          {/* Left: Acquisition Targets (top velocity) */}
          <Panel title="Acquisition Targets">
            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Skeleton width={24} height={16} />
                    <Skeleton width={140} height={16} style={{ flex: 1 }} />
                    <Skeleton width={60} height={22} />
                    <Skeleton width={50} height={16} />
                    <Skeleton width={80} height={32} />
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
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'var(--color-surface-container-low)' }}>
                      {['#', 'Company', 'Velocity', 'Score', 'Action'].map(h => (
                        <th key={h} style={{
                          padding: '8px 12px',
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.625rem',
                          fontWeight: 700,
                          color: 'var(--color-on-surface-variant)',
                          letterSpacing: '0.05em',
                          textTransform: 'uppercase',
                          textAlign: 'left',
                          whiteSpace: 'nowrap',
                        }}>{h}</th>
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
                        <tr
                          key={id || i}
                          style={{
                            background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent',
                            transition: 'background var(--transition-fast)',
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
                          onMouseLeave={e => e.currentTarget.style.background = i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent'}
                        >
                          <td style={{
                            padding: '12px 12px',
                            fontFamily: 'var(--font-editorial)',
                            fontSize: '1rem',
                            color: 'var(--color-on-surface-variant)',
                            whiteSpace: 'nowrap',
                          }}>
                            {String(i + 1).padStart(2, '0')}
                          </td>
                          <td style={{
                            padding: '12px 12px',
                            fontFamily: 'var(--font-data)',
                            fontSize: '0.875rem',
                            fontWeight: 600,
                            color: 'var(--color-primary)',
                            maxWidth: 160,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}>
                            {name}
                          </td>
                          <td style={{ padding: '12px 12px', whiteSpace: 'nowrap' }}>
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 3,
                              padding: '3px 8px',
                              borderRadius: 'var(--radius-full)',
                              background: velocity > 0 ? 'var(--color-secondary-container)' : 'var(--color-error-bg)',
                              color: velocity > 0 ? 'var(--color-on-secondary-container)' : 'var(--color-error)',
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.625rem',
                              fontWeight: 700,
                            }}>
                              {velocity > 0 ? '\u2191' : '\u2193'} {Math.abs(velocity).toFixed(2)}
                            </span>
                          </td>
                          <td style={{
                            padding: '12px 12px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.8125rem',
                            color: 'var(--color-on-surface)',
                            whiteSpace: 'nowrap',
                          }}>
                            {item.composite_score != null
                              ? ((item.composite_score * 100).toFixed(1) + '%')
                              : '—'}
                          </td>
                          <td style={{ padding: '12px 12px', whiteSpace: 'nowrap' }}>
                            {alreadyWatched ? (
                              <span style={{
                                fontFamily: 'var(--font-data)',
                                fontSize: '0.6875rem',
                                color: 'var(--color-secondary)',
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                letterSpacing: '0.04em',
                              }}>Watching</span>
                            ) : (
                              <button
                                onClick={() => handleAddToWatchlist(id, name)}
                                disabled={isWatching || !id}
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 5,
                                  padding: '5px 12px',
                                  borderRadius: 'var(--radius-md)',
                                  fontFamily: 'var(--font-data)',
                                  fontSize: '0.625rem',
                                  fontWeight: 700,
                                  letterSpacing: '0.04em',
                                  textTransform: 'uppercase',
                                  cursor: (isWatching || !id) ? 'default' : 'pointer',
                                  background: 'var(--color-primary)',
                                  color: '#fff',
                                  border: 'none',
                                  opacity: (isWatching || !id) ? 0.6 : 1,
                                  transition: 'opacity var(--transition-fast)',
                                }}
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
            <form onSubmit={handleAddFromInput} style={{
              display: 'flex',
              gap: '0.5rem',
              marginBottom: '1.25rem',
            }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Search
                  size={14}
                  style={{
                    position: 'absolute',
                    left: 10,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--color-on-surface-variant)',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  type="text"
                  placeholder="Company name..."
                  value={addInput}
                  onChange={e => { setAddInput(e.target.value); setAddError(null) }}
                  style={{
                    width: '100%',
                    padding: '8px 10px 8px 30px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-surface-container-high)',
                    fontFamily: 'var(--font-data)',
                    fontSize: '0.8125rem',
                    color: 'var(--color-on-surface)',
                    background: 'var(--color-surface-container-low)',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                  onFocus={e => e.target.style.borderColor = 'var(--color-secondary)'}
                  onBlur={e => e.target.style.borderColor = 'var(--color-surface-container-high)'}
                />
              </div>
              <button
                type="submit"
                disabled={addLoading || !addInput.trim()}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-md)',
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                  cursor: (addLoading || !addInput.trim()) ? 'default' : 'pointer',
                  background: 'var(--color-secondary)',
                  color: '#fff',
                  border: 'none',
                  opacity: (addLoading || !addInput.trim()) ? 0.6 : 1,
                  transition: 'opacity var(--transition-fast)',
                  whiteSpace: 'nowrap',
                }}
              >
                <Plus size={12} />
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
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Skeleton width={140} height={14} style={{ marginBottom: 4 }} />
                      <Skeleton width={80} height={11} />
                    </div>
                    <Skeleton width={32} height={32} />
                  </div>
                ))}
              </div>
            ) : watchlistData.length === 0 ? (
              <EmptyState
                icon={<Eye size={32} />}
                title="Watchlist is empty"
                message="Add companies from the targets table or search above."
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {watchlistData.map((entry, i) => {
                  const id = entry.id || entry.watchlist_id || entry.company_id || i
                  const name = entry.company_name || entry.name || ('Company ' + id)
                  const addedAt = entry.added_at || entry.created_at
                  const isRemoving = removingIds[id]
                  return (
                    <div
                      key={id}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '0.75rem 1rem',
                        background: 'var(--color-surface-container-low)',
                        borderRadius: 'var(--radius-md)',
                        transition: 'background var(--transition-fast)',
                        gap: '0.75rem',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-high)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'var(--color-surface-container-low)'}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.875rem',
                          fontWeight: 600,
                          color: 'var(--color-primary)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          marginBottom: 2,
                        }}>
                          {name}
                        </div>
                        {addedAt && (
                          <div style={{
                            fontFamily: 'var(--font-data)',
                            fontSize: '0.6875rem',
                            color: 'var(--color-on-primary-container)',
                          }}>
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
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: 32,
                          height: 32,
                          borderRadius: 'var(--radius-md)',
                          background: isRemoving ? 'var(--color-surface-container-high)' : 'var(--color-error-bg)',
                          color: 'var(--color-error)',
                          border: 'none',
                          cursor: isRemoving ? 'default' : 'pointer',
                          flexShrink: 0,
                          transition: 'background var(--transition-fast)',
                          opacity: isRemoving ? 0.5 : 1,
                        }}
                        onMouseEnter={e => { if (!isRemoving) e.currentTarget.style.background = '#fecaca' }}
                        onMouseLeave={e => { e.currentTarget.style.background = isRemoving ? 'var(--color-surface-container-high)' : 'var(--color-error-bg)' }}
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
