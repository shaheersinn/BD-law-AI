/**
 * pages/LiveTriggersPage.jsx — P7/P8 Redesign
 *
 * Real-time legal mandate signals from SEDAR, EDGAR, CanLII, Jobs, OSC.
 * Supports source tab filtering and urgency level filter.
 * LiveTriggersList styles are integrated here.
 * DM Serif Display + DM Sans, no inline styles.
 */

import { useEffect, useState, useCallback } from 'react'
import { Zap, Loader } from 'lucide-react'
import { triggers } from '../api/client'
import AppShell from '../components/layout/AppShell'
import { Skeleton } from '../components/Skeleton'
import {
  PageHeader,
  MetricCard,
  Tag,
  EmptyState,
  ErrorState,
} from '../components/ui/Primitives'

const TRIGGERS_CSS = `
.lt-root {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
}
.lt-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin-bottom: 2.5rem;
}

/* Tabs */
.lt-tabs-row {
  display: flex;
  gap: 6px;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.lt-tab {
  padding: 6px 16px;
  border-radius: var(--radius-full);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  cursor: pointer;
  border: none;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.lt-tab:hover { background: var(--color-surface-container-high); }
.lt-tab.active {
  background: var(--color-secondary-container);
  color: var(--color-on-secondary-container);
}
.lt-tab.inactive {
  background: var(--color-surface-container-low);
  color: var(--color-on-surface-variant);
}

/* Urgency Filter */
.lt-filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 1.5rem;
}
.lt-filter-label {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.lt-filter-btn {
  padding: 5px 12px;
  border-radius: var(--radius-md);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  cursor: pointer;
  border: none;
  transition: background var(--transition-fast);
}
.lt-filter-btn:hover { opacity: 0.9; }
.lt-filter-btn.active {
  background: var(--color-primary);
  color: #fff;
}
.lt-filter-btn.inactive {
  background: var(--color-surface-container-low);
  color: var(--color-on-surface-variant);
}

/* List / Feed */
.lt-feed {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.lt-card {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-ambient);
  padding: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  transition: box-shadow var(--transition-card), transform var(--transition-card);
}
.lt-card:hover {
  box-shadow: 0 4px 24px -6px rgba(25,28,30,0.12);
  transform: translateY(-2px);
}
.lt-content {
  flex: 1;
  min-width: 0;
}
.lt-entity {
  font-family: var(--font-editorial);
  font-size: 1.25rem;
  font-weight: 400;
  color: var(--color-primary);
  margin-bottom: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  letter-spacing: -0.01em;
}
.lt-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.lt-desc {
  font-family: var(--font-data);
  font-size: 0.8125rem;
  color: var(--color-on-surface-variant);
  line-height: 1.6;
  margin: 0 0 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.lt-time {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  color: var(--color-on-primary-container);
  opacity: 0.8;
}

/* Actions Sidebar in Card */
.lt-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  flex-shrink: 0;
}
.lt-urgency {
  font-family: var(--font-editorial);
  font-size: 2.2rem;
  font-weight: 400;
  line-height: 1;
}
.lt-btn-brief {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-family: var(--font-data);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border: none;
  transition: background var(--transition-fast), opacity var(--transition-fast);
  white-space: nowrap;
}
.lt-btn-brief-active {
  background: var(--color-primary);
  color: #fff;
  cursor: pointer;
}
.lt-btn-brief-active:hover { opacity: 0.9; }
.lt-btn-brief-loading {
  background: var(--color-surface-container-high);
  color: var(--color-on-surface-variant);
  cursor: default;
  opacity: 0.7;
}
.lt-brief-ready {
  font-family: var(--font-data);
  font-size: 0.6875rem;
  color: var(--color-secondary);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

@media (max-width: 980px) {
  .lt-metrics { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 640px) {
  .lt-metrics { grid-template-columns: 1fr; }
  .lt-card { flex-direction: column; align-items: stretch; }
  .lt-actions { align-items: flex-start; flex-direction: row; justify-content: space-between; }
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('lt-styles')) {
    const el = document.createElement('style')
    el.id = 'lt-styles'
    el.textContent = TRIGGERS_CSS
    document.head.appendChild(el)
  }
}

const SOURCES = ['ALL', 'SEDAR', 'EDGAR', 'CANLII', 'JOBS', 'OSC']
const URGENCY_OPTIONS = [
  { label: 'All', value: null },
  { label: 'High (>80)', value: 80 },
  { label: 'Medium (>50)', value: 50 },
]

function urgencyTextColor(score) {
  if (score > 80) return 'var(--color-error)'
  if (score > 60) return '#d97706'
  return 'var(--color-secondary)'
}

export default function LiveTriggersPage() {
  injectCSS()
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
      <div className="lt-root">
        <PageHeader
          tag="Signal Intelligence"
          title="Live Triggers"
          subtitle="Real-time legal mandate signals from SEDAR, EDGAR, CanLII, Jobs, OSC"
        />

        {/* Metric cards */}
        <section className="lt-metrics">
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
        <div className="lt-tabs-row">
          {SOURCES.map(src => (
            <button
              key={src}
              onClick={() => setActiveTab(src)}
              className={`lt-tab ${activeTab === src ? 'active' : 'inactive'}`}
            >
              {src}
            </button>
          ))}
        </div>

        {/* Urgency filter */}
        <div className="lt-filter-row">
          <span className="lt-filter-label">Urgency:</span>
          {URGENCY_OPTIONS.map(opt => (
            <button
              key={opt.label}
              onClick={() => setUrgencyFilter(opt.value)}
              className={`lt-filter-btn ${urgencyFilter === opt.value ? 'active' : 'inactive'}`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Trigger cards */}
        <div className="lt-feed">
          {feedLoading ? (
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="lt-card">
                <div className="lt-content">
                  <Skeleton width={180} height={18} style={{ marginBottom: 8 }} />
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                    <Skeleton width={60} height={20} />
                    <Skeleton width={80} height={20} />
                  </div>
                  <Skeleton width="90%" height={14} />
                </div>
                <div className="lt-actions">
                  <Skeleton width={48} height={36} />
                  <Skeleton width={110} height={32} />
                </div>
              </div>
            ))
          ) : feed.length === 0 ? (
            <EmptyState
              icon={<Zap size={32} />}
              title="No triggers found"
              message="No signals match the current source and urgency filters."
            />
          ) : (
            feed.map((trigger, i) => {
              const id = trigger.id || trigger.trigger_id || i
              const urgency = trigger.urgency || trigger.urgency_score || 0
              const isBriefing = briefLoading[id]
              const hasBrief = briefResults[id]
              return (
                <div key={id} className="lt-card">
                  <div className="lt-content">
                    <div className="lt-entity">{trigger.company_name || trigger.entity_name || 'Unknown Entity'}</div>
                    <div className="lt-tags">
                      {trigger.source && <Tag label={trigger.source} color="navy" />}
                      {trigger.practice_area && <Tag label={trigger.practice_area} color="blue" />}
                    </div>
                    <p className="lt-desc">{trigger.description || trigger.headline || trigger.summary || ''}</p>
                    {(trigger.filed_at || trigger.created_at) && (
                      <div className="lt-time">
                        {new Date(trigger.filed_at || trigger.created_at).toLocaleString('en-CA', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                        })}
                      </div>
                    )}
                  </div>

                  <div className="lt-actions">
                    <div className="lt-urgency" style={{ color: urgencyTextColor(urgency) }}>
                      {Math.round(urgency)}
                    </div>
                    {hasBrief && !hasBrief.error ? (
                      <span className="lt-brief-ready">Brief Ready</span>
                    ) : (
                      <button
                        onClick={() => handleBrief(id)}
                        disabled={isBriefing}
                        className={`lt-btn-brief ${isBriefing ? 'lt-btn-brief-loading' : 'lt-btn-brief-active'}`}
                      >
                        {isBriefing && <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} />}
                        {isBriefing ? 'Generating...' : 'Generate Brief'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>

      </div>
    </AppShell>
  )
}
