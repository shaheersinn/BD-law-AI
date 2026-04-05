/**
 * pages/LandingPage.jsx — P2 Redesign
 *
 * Public marketing page. Sticky glass nav, hero split, How It Works,
 * 22 Intelligence Modules grid, competitive banner, access form, footer.
 * No API calls. DM Serif Display + DM Sans. Responsive below 980px.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './LandingPage.css'

function scrollToId(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const MODULES = [
  { n: '01', title: 'Command Center',        desc: 'Live mandate signals, velocity rankings, and KPIs in one executive view.' },
  { n: '02', title: 'Live Triggers',          desc: 'Real-time regulatory, litigation, and enforcement events as they happen.' },
  { n: '03', title: 'Mandate Pre-Formation',  desc: 'Bayesian convergence engine scoring 34 practice areas on 3 horizons.' },
  { n: '04', title: 'Pre-Crime Engine',       desc: 'Legal Urgency Index — prospects ranked by how urgently they need counsel.' },
  { n: '05', title: 'Churn Predictor',        desc: 'XGBoost + SHAP flags silent client attrition before it becomes visible.' },
  { n: '06', title: 'M&A Dark Signals',       desc: 'Triple convergence: options anomaly + jet tracks + SEDAR confidentiality.' },
  { n: '07', title: 'Class Action Radar',     desc: 'Multi-jurisdiction class action tracking with watchlist company matching.' },
  { n: '08', title: 'Regulatory Ripple',      desc: 'Enforcement actions mapped to same-sector clients for proactive outreach.' },
  { n: '09', title: 'GC Profiler',            desc: 'Psychographic profiles of General Counsels with relationship intelligence.' },
  { n: '10', title: 'Wallet Share',           desc: 'Client legal spend capture rate against Total Addressable Market.' },
  { n: '11', title: 'Competitive Intel',      desc: 'Lateral hires, practice expansions, and conflict arbitrage monitoring.' },
  { n: '12', title: 'Pitch Autopsy',          desc: 'Win/loss analysis with AI debrief and follow-up campaign tracking.' },
]

const HOW_IT_WORKS = [
  {
    n: '01',
    title: 'Signal Ingestion',
    body: 'ORACLE monitors 28 signal types across regulatory filings, court records, executive movements, satellite data, and market feeds — normalized into one intelligence layer.',
  },
  {
    n: '02',
    title: 'Bayesian Convergence',
    body: 'When signals from multiple categories align, a convergence multiplier amplifies the mandate probability score — separating noise from genuine pre-formation activity.',
  },
  {
    n: '03',
    title: 'Partner-Ready Evidence',
    body: 'SHAP-driven explanations and counterfactual features turn each prediction into a defensible brief — so partners have something to say before they call.',
  },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ fullName: '', workEmail: '', firm: '', practice: '' })

  const handleSubmit = (e) => {
    e.preventDefault()
    navigate('/login')
  }

  return (
    <div className="lp-root">

      {/* ── Nav ── */}
      <nav className="lp-nav">
        <div className="lp-container lp-nav-inner">
          <div className="lp-nav-left">
            <div className="lp-logo-mark"><span className="lp-logo-letter">O</span></div>
            <span className="lp-nav-wordmark">Oracle Intelligence</span>
          </div>
          <div className="lp-nav-links">
            <button type="button" className="lp-nav-link" onClick={() => scrollToId('how-it-works')}>Platform</button>
            <button type="button" className="lp-nav-link" onClick={() => scrollToId('how-it-works')}>Intelligence</button>
            <button type="button" className="lp-nav-link" onClick={() => scrollToId('modules')}>Modules</button>
          </div>
          <button type="button" className="lp-nav-cta" onClick={() => navigate('/login')}>
            Request access
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="lp-hero">
        <div className="lp-container">
          <div className="lp-hero-grid">

            {/* Left 55% */}
            <div className="lp-hero-copy">
              <div className="lp-hero-kicker">
                <span className="lp-hero-dot" />
                <span>BD Intelligence Platform</span>
              </div>
              <h1 className="lp-hero-title">
                Predict who needs a lawyer{' '}
                <em>before they call</em>
              </h1>
              <p className="lp-hero-sub">
                ORACLE monitors 28 signal types across regulatory filings, court records,
                executive movements, and market data — then scores mandate probability
                across 34 practice areas at 30, 60, and 90-day horizons.
              </p>
              <div className="lp-hero-actions">
                <button type="button" className="lp-btn-primary" onClick={() => navigate('/login')}>
                  Start the demo
                </button>
                <button type="button" className="lp-btn-secondary" onClick={() => scrollToId('how-it-works')}>
                  How it works
                </button>
              </div>
              <div className="lp-hero-stats">
                {[
                  { val: '28', label: 'Signal Types'    },
                  { val: '34', label: 'Practice Areas'  },
                  { val: '100+', label: 'Data Sources'  },
                  { val: '3',   label: 'Time Horizons'  },
                ].map(s => (
                  <div key={s.label} className="lp-hero-stat">
                    <div className="lp-hero-stat-val">{s.val}</div>
                    <div className="lp-hero-stat-label">{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right 45% — Mock dashboard card */}
            <div className="lp-hero-mock-wrap" aria-hidden="true">
              <div className="lp-hero-mock">
                <div className="lp-mock-header">
                  <span className="lp-mock-tag">Mandate Score — Laurier Software Group</span>
                  <span className="lp-mock-live">● LIVE</span>
                </div>

                {/* 30/60/90 horizon bars */}
                <div className="lp-mock-horizons">
                  {[
                    { label: '30 DAY', pct: 87, color: 'var(--color-secondary)' },
                    { label: '60 DAY', pct: 72, color: '#3b6eb5' },
                    { label: '90 DAY', pct: 54, color: 'var(--color-on-surface-variant)' },
                  ].map(h => (
                    <div key={h.label} className="lp-mock-horizon-row">
                      <span className="lp-mock-horizon-label">{h.label}</span>
                      <div className="lp-mock-horizon-track">
                        <div className="lp-mock-horizon-fill" style={{ width: `${h.pct}%`, background: h.color }} />
                      </div>
                      <span className="lp-mock-horizon-val" style={{ color: h.color }}>{h.pct}%</span>
                    </div>
                  ))}
                </div>

                {/* Mini area chart */}
                <div className="lp-mock-chart">
                  <svg viewBox="0 0 280 80" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="lpGrad" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="#2a7d5f" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#2a7d5f" stopOpacity="0.02" />
                      </linearGradient>
                    </defs>
                    <path d="M0,65 C40,60 70,48 100,42 C130,36 160,44 190,40 C220,36 250,22 280,14 L280,80 L0,80 Z" fill="url(#lpGrad)" />
                    <path d="M0,65 C40,60 70,48 100,42 C130,36 160,44 190,40 C220,36 250,22 280,14" stroke="#2a7d5f" strokeWidth="2.5" fill="none" strokeLinecap="round" />
                  </svg>
                </div>

                <div className="lp-mock-callout">
                  <span className="lp-mock-callout-dot">◆</span>
                  Bayesian convergence: 4 signal categories active
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how-it-works" className="lp-section">
        <div className="lp-container">
          <div className="lp-section-head">
            <div className="lp-section-kicker">How it works</div>
            <div className="lp-section-title">From raw signal to partner brief in minutes</div>
          </div>
          <div className="lp-how-grid">
            {HOW_IT_WORKS.map(s => (
              <div key={s.n} className="lp-how-card">
                <div className="lp-how-num">{s.n}</div>
                <div className="lp-how-title">{s.title}</div>
                <p className="lp-how-body">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 22 Intelligence Modules ── */}
      <section id="modules" className="lp-section lp-section-alt">
        <div className="lp-container">
          <div className="lp-section-head">
            <div className="lp-section-kicker">Intelligence Modules</div>
            <div className="lp-section-title">22 intelligence modules. One platform.</div>
          </div>
          <div className="lp-modules-grid">
            {MODULES.map((m, i) => (
              <div key={m.n} className={`lp-module-card${i === 0 ? ' lp-module-featured' : ''}`}>
                <div className="lp-module-num">{m.n}</div>
                <div className="lp-module-title">{m.title}</div>
                <p className="lp-module-desc">{m.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Competitive banner ── */}
      <section className="lp-banner-section">
        <div className="lp-container">
          <div className="lp-banner">
            <div className="lp-banner-headline">4.2× lead-time acceleration</div>
            <div className="lp-banner-stats">
              {[
                { val: '1,402', label: 'Mandates Scored' },
                { val: '18/25', label: 'Evidence Rate'   },
                { val: '22',    label: 'Intel Modules'   },
              ].map(s => (
                <div key={s.label} className="lp-banner-stat">
                  <div className="lp-banner-stat-val">{s.val}</div>
                  <div className="lp-banner-stat-label">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Apply for access ── */}
      <section id="apply-access" className="lp-section">
        <div className="lp-container">
          <div className="lp-apply-head">
            <div className="lp-section-kicker">Apply for access</div>
            <div className="lp-section-title">Request your firm's onboarding slot</div>
          </div>
          <div className="lp-apply-card">
            <form onSubmit={handleSubmit}>
              <div className="lp-form-grid">
                <div>
                  <label className="lp-form-label" htmlFor="ap-name">Full Name</label>
                  <input id="ap-name" className="lp-form-input" value={form.fullName}
                    onChange={e => setForm(s => ({ ...s, fullName: e.target.value }))}
                    placeholder="Jane Smith" required />
                </div>
                <div>
                  <label className="lp-form-label" htmlFor="ap-email">Work Email</label>
                  <input id="ap-email" className="lp-form-input" type="email" value={form.workEmail}
                    onChange={e => setForm(s => ({ ...s, workEmail: e.target.value }))}
                    placeholder="jane@firm.com" required />
                </div>
                <div className="lp-span-2">
                  <label className="lp-form-label" htmlFor="ap-firm">Firm</label>
                  <input id="ap-firm" className="lp-form-input" value={form.firm}
                    onChange={e => setForm(s => ({ ...s, firm: e.target.value }))}
                    placeholder="Halcyon Legal" required />
                </div>
                <div className="lp-span-2">
                  <label className="lp-form-label" htmlFor="ap-practice">Practice Area</label>
                  <input id="ap-practice" className="lp-form-input" value={form.practice}
                    onChange={e => setForm(s => ({ ...s, practice: e.target.value }))}
                    placeholder="M&A / Litigation / Regulatory..." required />
                </div>
              </div>
              <div className="lp-apply-submit-row">
                <button type="submit" className="lp-btn-primary">REQUEST ACCESS</button>
              </div>
            </form>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <div className="lp-container lp-footer-inner">
          <span>© 2026 Oracle Intelligence — ORACLE BD Platform</span>
          <div className="lp-footer-links">
            <button type="button" className="lp-footer-link" onClick={() => scrollToId('how-it-works')}>Platform</button>
            <button type="button" className="lp-footer-link" onClick={() => scrollToId('modules')}>Modules</button>
            <button type="button" className="lp-footer-link" onClick={() => scrollToId('apply-access')}>Apply</button>
            <button type="button" className="lp-footer-link" onClick={() => navigate('/login')}>Sign in</button>
          </div>
        </div>
      </footer>
    </div>
  )
}
