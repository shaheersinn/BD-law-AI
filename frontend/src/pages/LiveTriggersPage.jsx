/**
 * pages/LiveTriggersPage.jsx — route /live-triggers
 *
 * Real-time legal mandate signals from SEDAR, EDGAR, CanLII, Jobs, OSC.
 * Supports source tab filtering and urgency level filter.
 */

import { useEffect, useState, useCallback } from 'react'
import { Zap, Loader } from 'lucide-react'
import { triggers } from '../api/client'
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

const SOURCES = ['ALL', 'SEDAR', 'EDGAR', 'CANLII', 'JOBS', 'OSC']
const URGENCY_OPTIONS = [
  { label: 'All', value: null },
  { label: 'High (>80)', value: 80 },
  { label: 'Medium (>50)', value: 50 },
]

function urgencyColor(score) {
  if (score > 80) return 'red'
  if (score > 60) return 'gold'
  return 'green'
}

function urgencyTextColor(score) {
  if (score > 80) return 'var(--color-error)'
  if (score > 60) return '#d97706'
  return 'var(--color-secondary)'
}

export default function LiveTriggersPage() {
  const [statsLoading, setStatsLoading] = useState(true)
  const [feedLoading, setFeedLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const [feed, setFeed] = useState([])
  const [activeTab, setActiveTab] = useState('ALL')
  const [urgencyFilter, setUrgencyFilter] = useState(null)
  const [briefLoading, setBriefLoading] = useState({})
  const [briefResults, setBriefResults] = useState({})

  // Load stats once
  useEffect(() => {
    triggers.stats()
      .then(data => setStats(data))
      .catch(err => setError(err.message || 'Failed to load trigger stats'))
      .finally(() => setStatsLoading(false))
  }, [])

  // Reload feed when tab or urgency changes
  const loadFeed = useCallback(() => {
    setFeedLoading(true)
    const params = {}
    if (activeTab !== 'ALL') params.source = activeTab
    if (urgencyFilter != null) params.min_urgency = urgencyFilter
    triggers.live(params)
      .then(data => setFeed(Array.isArray(data) ? data : (data?.results || [])))
      .catch(err => setError(err.message || 'Failed to load live triggers'))
      .finally(() => setFeedLoading(false))
  }, [activeTab, urgencyFilter])

  useEffect(() => { loadFeed() }, [loadFeed])

  const handleBrief = (id) => {
    setBriefLoading(prev => ({ ...prev, [id]: true }))
    triggers.brief(id)
      .then(result => setBriefResults(prev => ({ ...prev, [id]: result })))
      .catch(() => setBriefResults(prev => ({ ...prev, [id]: { error: true } })))
      .finally(() => setBriefLoading(prev => ({ ...prev, [id]: false })))
  }

  if (error) return (
    <AppShell>
      <div style={{ padding: '2rem' }}>
        <ErrorState message={error} onRetry={() => { setError(null); loadFeed() }} />
      </div>
    </AppShell>
  )

  return (
    <AppShell>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 2rem 3rem' }}>

        <PageHeader
          tag="Signal Intelligence"
          title="Live Triggers"
          subtitle="Real-time legal mandate signals from SEDAR, EDGAR, CanLII, Jobs, OSC"
        />

        {/* Metric cards */}
        <section style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1.25rem',
          marginBottom: '2.5rem',
        }}>
          <MetricCard
            label="Total Today"
            value={statsLoading ? <Skeleton width={48} height={24} /> : (stats?.total_today ?? '--')}
            accent="navy"
          />
          <MetricCard
            label="High Urgency"
            value={statsLoading ? <Skeleton width={48} height={24} /> : (stats?.high_urgency ?? '--')}
            accent="red"
          />
          <MetricCard
            label="Avg Confidence"
            value={statsLoading ? <Skeleton width={48} height={24} /> : (stats?.avg_confidence != null ? `${stats.avg_confidence}%` : '--')}
            accent="blue"
          />
          <MetricCard
            label="Briefed"
            value={statsLoading ? <Skeleton width={48} height={24} /> : (stats?.briefed ?? '--')}
            accent="teal"
          />
        </section>

        {/* Source tab bar */}
        <div style={{
          display: 'flex',
          gap: '0.375rem',
          marginBottom: '1rem',
          flexWrap: 'wrap',
        }}>
          {SOURCES.map(src => {
            const active = activeTab === src
            return (
              <button
                key={src}
                onClick={() => setActiveTab(src)}
                style={{
                  padding: '6px 16px',
                  borderRadius: 'var(--radius-full)',
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                  cursor: 'pointer',
                  border: 'none',
                  transition: 'background var(--transition-fast), color var(--transition-fast)',
                  background: active ? 'var(--color-secondary-container)' : 'var(--color-surface-container-low)',
                  color: active ? 'var(--color-on-secondary-container)' : 'var(--color-on-surface-variant)',
                }}
              >
                {src}
              </button>
            )
          })}
        </div>

        {/* Urgency filter */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '1.5rem',
        }}>
          <span style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.6875rem',
            fontWeight: 700,
            color: 'var(--color-on-surface-variant)',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}>Urgency:</span>
          {URGENCY_OPTIONS.map(opt => {
            const active = urgencyFilter === opt.value
            return (
              <button
                key={opt.label}
                onClick={() => setUrgencyFilter(opt.value)}
                style={{
                  padding: '5px 12px',
                  borderRadius: 'var(--radius-md)',
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  border: 'none',
                  transition: 'background var(--transition-fast)',
                  background: active ? 'var(--color-primary)' : 'var(--color-surface-container-low)',
                  color: active ? '#fff' : 'var(--color-on-surface-variant)',
                }}
              >
                {opt.label}
              </button>
            )
          })}
        </div>

        {/* Trigger cards */}
        {feedLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={{
                background: 'var(--color-surface-container-lowest)',
                borderRadius: 'var(--radius-xl)',
                padding: '1.25rem',
                boxShadow: 'var(--shadow-ambient)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '1rem',
              }}>
                <div style={{ flex: 1 }}>
                  <Skeleton width={180} height={18} style={{ marginBottom: 8 }} />
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                    <Skeleton width={60} height={20} />
                    <Skeleton width={80} height={20} />
                  </div>
                  <Skeleton width="90%" height={14} />
                </div>
                <div style={{ textAlign: 'right' }}>
                  <Skeleton width={48} height={36} style={{ marginBottom: 8 }} />
                  <Skeleton width={110} height={32} />
                </div>
              </div>
            ))}
          </div>
        ) : feed.length === 0 ? (
          <EmptyState
            icon={<Zap size={32} />}
            title="No triggers found"
            message="No signals match the current source and urgency filters."
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {feed.map((trigger, i) => {
              const id = trigger.id || trigger.trigger_id || i
              const urgency = trigger.urgency || trigger.urgency_score || 0
              const isBriefing = briefLoading[id]
              const hasBrief = briefResults[id]
              return (
                <div
                  key={id}
                  style={{
                    background: 'var(--color-surface-container-lowest)',
                    borderRadius: 'var(--radius-xl)',
                    boxShadow: 'var(--shadow-ambient)',
                    padding: '1.25rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: '1.5rem',
                    transition: 'box-shadow var(--transition-card)',
                  }}
                  onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 24px -6px rgba(25,28,30,0.12)'}
                  onMouseLeave={e => e.currentTarget.style.boxShadow = 'var(--shadow-ambient)'}
                >
                  {/* Left side */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontFamily: 'var(--font-editorial)',
                      fontSize: '1.125rem',
                      fontWeight: 500,
                      color: 'var(--color-primary)',
                      marginBottom: '0.5rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {trigger.company_name || trigger.entity_name || 'Unknown Entity'}
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.625rem' }}>
                      {trigger.source && <Tag label={trigger.source} color="navy" />}
                      {trigger.practice_area && <Tag label={trigger.practice_area} color="blue" />}
                    </div>
                    <p style={{
                      fontFamily: 'var(--font-data)',
                      fontSize: '0.8125rem',
                      color: 'var(--color-on-surface-variant)',
                      lineHeight: 1.55,
                      margin: 0,
                      marginBottom: '0.5rem',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>
                      {trigger.description || trigger.headline || trigger.summary || ''}
                    </p>
                    {(trigger.filed_at || trigger.created_at) && (
                      <div style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.6875rem',
                        color: 'var(--color-on-primary-container)',
                      }}>
                        {new Date(trigger.filed_at || trigger.created_at).toLocaleString('en-CA', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                        })}
                      </div>
                    )}
                  </div>

                  {/* Right side */}
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-end',
                    gap: '0.75rem',
                    flexShrink: 0,
                  }}>
                    <div style={{
                      fontFamily: 'var(--font-editorial)',
                      fontSize: '2rem',
                      fontWeight: 500,
                      color: urgencyTextColor(urgency),
                      lineHeight: 1,
                    }}>
                      {Math.round(urgency)}
                    </div>
                    {hasBrief && !hasBrief.error ? (
                      <span style={{
                        fontFamily: 'var(--font-data)',
                        fontSize: '0.6875rem',
                        color: 'var(--color-secondary)',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                      }}>Brief Ready</span>
                    ) : (
                      <button
                        onClick={() => handleBrief(id)}
                        disabled={isBriefing}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '7px 16px',
                          borderRadius: 'var(--radius-md)',
                          fontFamily: 'var(--font-data)',
                          fontSize: '0.6875rem',
                          fontWeight: 700,
                          letterSpacing: '0.04em',
                          textTransform: 'uppercase',
                          cursor: isBriefing ? 'default' : 'pointer',
                          background: isBriefing ? 'var(--color-surface-container-high)' : 'var(--color-primary)',
                          color: isBriefing ? 'var(--color-on-surface-variant)' : '#fff',
                          border: 'none',
                          transition: 'background var(--transition-fast)',
                          whiteSpace: 'nowrap',
                          opacity: isBriefing ? 0.7 : 1,
                        }}
                      >
                        {isBriefing && <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} />}
                        {isBriefing ? 'Generating...' : 'Generate Brief'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

      </div>
    </AppShell>
  )
}
