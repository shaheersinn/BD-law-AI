/**
 * pages/LandingPage.jsx - Public marketing landing
 *
 * Updated to match the attached "The BigLaw Ledger" design (hero + mockup,
 * Core Intelligence Engine, The Ledger OS, competitive banner, and apply form).
 */

import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './LandingPage.css'

function scrollToId(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export default function LandingPage() {
  const navigate = useNavigate()

  const coreCards = useMemo(() => ([
    {
      title: 'Signal Engine',
      body: 'Ingests regulatory filings, court events, market data, and executive movement-then normalizes into one signal layer.',
    },
    {
      title: 'Mandate Scoring',
      body: 'Calibrated models produce probability across 34 practice areas and 30/60/90-day horizons.',
    },
    {
      title: 'Executive Context',
      body: 'Profiles entity risk with network effects so your partners understand the "why" behind each score.',
    },
    {
      title: 'Actionable Evidence',
      body: 'SHAP-driven explanations and counterfactual features turn prediction into defensible outreach.',
    },
    {
      title: 'Velocity Monitor',
      body: 'Detects accelerating signal velocity so teams act before the market consensus catches up.',
    },
    {
      title: 'Priority Routing',
      body: 'Auto-routes mandates to the right queues-so BD time goes to the highest-leverage opportunities.',
    },
    {
      title: 'Ledger Feedback Loop',
      body: 'Captures confirmed mandates and improves lead-time accuracy through ongoing validation.',
    },
    {
      title: 'Drift Detection',
      body: 'Flags practice areas where accuracy degrades-prompting model re-evaluation and calibration.',
    },
  ]), [])

  const ledgerItems = useMemo(() => ([
    { title: '01. Strategic Dashboards', sub: 'A clean view of what is changing, where, and why-built for partner review.' },
    { title: '02. Cross Product Signals', sub: 'Unifies scrapers, features, and evidence into one decision surface.' },
    { title: '03. Client Predictive Landscape', sub: 'Maps near-term mandate likelihood across time horizons for outreach timing.' },
    { title: '04. Litigation Routing', sub: 'Prioritizes disputes and enforcement actions with early leading indicators.' },
    { title: '05. OS Layer Memory', sub: 'The ledger stores confirmations and adapts to outcomes over time.' },
    { title: '06. Lighting Intelligence', sub: 'Explains drivers and counterfactuals so BD asks better questions.' },
  ]), [])

  const [form, setForm] = useState({
    fullName: '',
    workEmail: '',
    firm: '',
    practice: '',
  })

  const submit = (e) => {
    e.preventDefault()
    // No backend endpoint exists yet for access requests; send users to sign-in.
    navigate('/login')
  }

  return (
    <div className="lp-root">
      {/* ---- Nav --------------------------------------------- */}
      <div className="lp-nav">
        <div className="lp-container lp-nav-inner">
          <div className="lp-nav-left">
            <div className="lp-logo-mark" aria-hidden="true">
              <span className="lp-logo-letter">O</span>
            </div>
            <div className="lp-nav-brand">
              <span className="lp-nav-brand-top">The BigLaw Ledger</span>
              <span className="lp-nav-brand-name">ORACLE</span>
            </div>
          </div>

          <div className="lp-nav-links">
            <div className="lp-nav-link" onClick={() => scrollToId('core-engine')}>How the platform works</div>
            <div className="lp-nav-link" onClick={() => scrollToId('ledger-os')}>The Ledger OS</div>
          </div>

          <button
            className="cl-btn-primary"
            type="button"
            onClick={() => navigate('/login')}
            style={{ padding: '9px 18px', fontSize: '0.875rem' }}
          >
            Start free trial
          </button>
        </div>
      </div>

      {/* ---- Hero -------------------------------------------- */}
      <section className="lp-hero">
        <div className="lp-container">
          <div className="lp-hero-grid">
            <div>
              <div className="lp-hero-kicker">
                <span className="lp-hero-dot" />
                <span className="lp-hero-kicker-text">The BigLaw Ledger</span>
              </div>

              <h1 className="lp-hero-title">The Future of BigLaw Business Development</h1>

              <p className="lp-hero-sub">
                Predict mandates before firms act. ORACLE unifies signals, scores probability
                across practice areas, and delivers evidence so partners can move with confidence.
              </p>

              <div className="lp-hero-actions">
                <button
                  type="button"
                  className="cl-btn-primary"
                  onClick={() => navigate('/login')}
                >
                  Start the demo
                </button>
                <button
                  type="button"
                  className="cl-btn-secondary"
                  onClick={() => scrollToId('apply-access')}
                >
                  See how it works
                </button>
              </div>
            </div>

            <div className="lp-hero-mock-wrap">
              <div className="lp-hero-mock" aria-hidden="true">
                <div className="lp-mock-topbar">
                  <span className="lp-mock-pill">Priority Lead</span>
                  <span className="lp-mock-pill" style={{ background: 'var(--color-secondary-container)' }}>Live</span>
                </div>

                <div className="lp-mock-cards">
                  <div className="lp-mock-surface">
                    <div className="lp-mock-row">
                      <div className="lp-mock-chart">
                        <svg viewBox="0 0 220 120" preserveAspectRatio="none">
                          <defs>
                            <linearGradient id="lpArea" x1="0" x2="0" y1="0" y2="1">
                              <stop offset="0%" stopColor="var(--color-secondary)" stopOpacity="0.55" />
                              <stop offset="100%" stopColor="var(--color-secondary)" stopOpacity="0.02" />
                            </linearGradient>
                          </defs>
                          <path
                            d="M0,95 C20,92 35,75 55,70 C75,65 90,50 110,45 C130,40 150,52 165,52 C180,52 195,40 220,30 L220,120 L0,120 Z"
                            fill="url(#lpArea)"
                          />
                          <path
                            d="M0,95 C20,92 35,75 55,70 C75,65 90,50 110,45 C130,40 150,52 165,52 C180,52 195,40 220,30"
                            stroke="var(--color-secondary)"
                            strokeWidth="3"
                            fill="none"
                            strokeLinecap="round"
                          />
                        </svg>
                      </div>

                      <div className="lp-mock-table">
                        <div className="lp-mock-line" style={{ width: '72%' }} />
                        <div className="lp-mock-line dim" style={{ width: '88%' }} />
                        <div className="lp-mock-line" style={{ width: '64%' }} />
                        <div className="lp-mock-line dim" style={{ width: '80%' }} />
                      </div>
                    </div>

                    <div className="lp-mock-callout">
                      <div className="lp-mock-callout-title">Bayesian Lead Timeline</div>
                      <div className="lp-mock-callout-sub">
                        When velocity increases, ORACLE routes the mandate to the correct queue with evidence-ready explanations.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---- Core Intelligence Engine ------------------------- */}
      <section id="core-engine" className="lp-section">
        <div className="lp-container">
          <div className="lp-section-head">
            <div className="lp-section-kicker">Core Intelligence Engine</div>
            <div className="lp-section-title">One Score. Partner-Ready Evidence.</div>
          </div>

          <div className="lp-core-grid">
            {coreCards.map((c) => (
              <div key={c.title} className="lp-core-card">
                <div className="lp-core-card-title">{c.title}</div>
                <div className="lp-core-card-body">{c.body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---- Ledger OS ----------------------------------------- */}
      <section id="ledger-os" className="lp-section" style={{ paddingTop: '1rem' }}>
        <div className="lp-container">
          <div className="lp-section-head" style={{ marginBottom: '1.75rem' }}>
            <div className="lp-section-kicker">The Ledger OS</div>
            <div className="lp-section-title">A system of dashboards, evidence, and feedback.</div>
          </div>

          <div className="lp-ledger-grid">
            <div className="lp-ledger-left">
              <h3>The Ledger OS</h3>
              <p>
                Every signal becomes a ledger entry. Every entry feeds the models. Every prediction learns from confirmation,
                so your BD team builds momentum with each cycle--not with guesswork.
              </p>
            </div>

            <div className="lp-ledger-right">
              {ledgerItems.map((it) => (
                <div key={it.title} className="lp-ledger-item">
                  <div className="lp-ledger-item-title">{it.title}</div>
                  <div className="lp-ledger-item-sub">{it.sub}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ---- Competitive banner ------------------------------ */}
      <section className="lp-section" style={{ paddingTop: 0 }}>
        <div className="lp-container">
          <div className="lp-banner">
            <div className="lp-banner-grid">
              <div>
                <div className="lp-banner-label">Mandates Captured (30/60/90)</div>
                <div className="lp-banner-number">1,402</div>
                <div className="lp-banner-text">
                  Signal-to-score coverage designed for partner-led outreach at BigLaw speed.
                </div>
              </div>
              <div>
                <div className="lp-banner-label">The Competitive Advantages</div>
                <div className="lp-banner-text" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
                  <div>
                    <div style={{ fontFamily: 'var(--font-editorial)', fontSize: '1.9rem', color: 'var(--color-on-primary)' }}>
                      4.2x
                    </div>
                    <div style={{ color: 'rgba(255, 255, 255, 0.78)' }}>Lead-time acceleration</div>
                  </div>
                  <div>
                    <div style={{ fontFamily: 'var(--font-editorial)', fontSize: '1.9rem', color: 'var(--color-on-primary)' }}>
                      18/25
                    </div>
                    <div style={{ color: 'rgba(255, 255, 255, 0.78)' }}>Partner-ready evidence rate</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---- Apply for Access ------------------------------- */}
      <section id="apply-access" className="lp-apply">
        <div className="lp-container">
          <div className="lp-apply-head">
            <div className="lp-section-kicker" style={{ marginBottom: 12 }}>Apply for Access</div>
            <div className="lp-apply-title">Request your firm's onboarding slot</div>
            <div className="lp-apply-sub">
              Submit your details and we'll route you to the right workflow.
            </div>
          </div>

          <div className="lp-apply-card">
            <form onSubmit={submit}>
              <div className="lp-form-grid">
                <div>
                  <label className="lp-form-label">Full name</label>
                  <input
                    className="cl-input"
                    value={form.fullName}
                    onChange={(e) => setForm((s) => ({ ...s, fullName: e.target.value }))}
                    placeholder="Jane Smith"
                    required
                  />
                </div>
                <div>
                  <label className="lp-form-label">Work email</label>
                  <input
                    className="cl-input"
                    value={form.workEmail}
                    onChange={(e) => setForm((s) => ({ ...s, workEmail: e.target.value }))}
                    placeholder="jane@firm.com"
                    type="email"
                    required
                  />
                </div>
                <div className="lp-span-2">
                  <label className="lp-form-label">Firm</label>
                  <input
                    className="cl-input"
                    value={form.firm}
                    onChange={(e) => setForm((s) => ({ ...s, firm: e.target.value }))}
                    placeholder="Halcyon Legal"
                    required
                  />
                </div>
                <div className="lp-span-2">
                  <label className="lp-form-label">Area of practice</label>
                  <input
                    className="cl-input"
                    value={form.practice}
                    onChange={(e) => setForm((s) => ({ ...s, practice: e.target.value }))}
                    placeholder="M&A / Litigation / Regulatory..."
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'center', marginTop: 18 }}>
                <button className="cl-btn-primary" type="submit" style={{ padding: '11px 26px' }}>
                  REQUEST ACCESS
                </button>
              </div>

              <div className="lp-footer" style={{ paddingBottom: 0 }}>
                By requesting access, you agree to receive onboarding communications from Halcyon Legal.
              </div>
            </form>
          </div>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="lp-container" style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
          <div>(c) 2026 The BigLaw Ledger - ORACLE</div>
          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <span style={{ cursor: 'pointer' }} onClick={() => scrollToId('core-engine')}>How it works</span>
            <span style={{ cursor: 'pointer' }} onClick={() => scrollToId('ledger-os')}>Ledger OS</span>
            <span style={{ cursor: 'pointer' }} onClick={() => scrollToId('apply-access')}>Apply</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
