/**
 * pages/LandingPage.jsx — Digital Atelier public landing page.
 *
 * Glass navbar, Newsreader hero, signal type cards,
 * practice area chip grid, social proof stats.
 * Public route at / — no auth required.
 */

import { useNavigate } from 'react-router-dom'

/* ── 34 practice areas from CLAUDE.md ─────────────────────────── */
const PRACTICE_AREAS = [
  'Mergers & Acquisitions', 'Capital Markets', 'Private Equity', 'Venture Capital',
  'Banking & Finance', 'Project Finance', 'Restructuring & Insolvency', 'Tax',
  'Competition / Antitrust', 'Corporate Governance', 'Securities Regulation',
  'Real Estate', 'Infrastructure', 'Energy', 'Mining',
  'Environmental', 'Indigenous Law', 'Technology & Data Privacy',
  'Intellectual Property', 'Labour & Employment', 'Pensions & Benefits',
  'Litigation', 'Arbitration', 'Class Actions', 'White Collar & Investigations',
  'Insurance', 'Healthcare & Life Sciences', 'Government Relations',
  'International Trade', 'Immigration', 'Wealth Management',
  'Cannabis', 'Aerospace & Defence', 'Telecommunications',
]

/* ── Signal type showcases ──────────────────────────────────────── */
const SIGNAL_TYPES = [
  {
    type: 'SEC & SEDAR Filings',
    desc: 'Regulatory filing analysis across North American markets. Material change reports, annual information forms, and prospectus alerts.',
    icon: '📄',
  },
  {
    type: 'Court Records',
    desc: 'Real-time monitoring of federal, provincial, and state court filings. Litigation risk detection before it becomes public knowledge.',
    icon: '⚖️',
  },
  {
    type: 'Job Postings',
    desc: 'Track strategic hiring signals — in-house counsel expansion, regulatory affairs buildout, and C-suite transitions.',
    icon: '💼',
  },
  {
    type: 'ADS-B Flight Data',
    desc: 'Executive jet movement patterns correlated with M&A activity. Private aviation tracking across 14,000+ registered aircraft.',
    icon: '✈️',
  },
  {
    type: 'Satellite Imagery',
    desc: 'Construction activity, facility expansion, and environmental monitoring via orbital image analysis.',
    icon: '🛰️',
  },
  {
    type: 'Press & Market Data',
    desc: 'NLP-processed news feeds, analyst reports, and credit rating changes. Sentiment scoring with 28-day momentum.',
    icon: '📊',
  },
]

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--color-surface)',
      fontFamily: 'var(--font-data)',
    }}>

      {/* ── Glass Navbar ──────────────────────────────────────── */}
      <nav style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        padding: '1rem 3rem',
        background: 'rgba(255, 255, 255, 0.80)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32,
            background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
            borderRadius: 'var(--radius-md)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{
              color: 'var(--color-on-primary)',
              fontSize: 14, fontWeight: 700,
              fontFamily: 'var(--font-editorial)',
            }}>O</span>
          </div>
          <span style={{
            fontFamily: 'var(--font-editorial)',
            fontSize: 20,
            fontWeight: 500,
            color: 'var(--color-primary)',
            letterSpacing: '-0.01em',
          }}>
            ORACLE
          </span>
        </div>
        <button
          onClick={() => navigate('/login')}
          style={{
            padding: '8px 20px',
            background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
            color: 'var(--color-on-primary)',
            borderRadius: 'var(--radius-md)',
            fontWeight: 600,
            fontSize: 13,
            cursor: 'pointer',
            transition: 'opacity 150ms ease-out',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.9'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          Sign In
        </button>
      </nav>


      {/* ── Hero Section ──────────────────────────────────────── */}
      <section style={{
        maxWidth: 960,
        margin: '0 auto',
        padding: '6rem 2rem 5rem',
        textAlign: 'center',
      }}>
        <div style={{
          fontFamily: 'var(--font-data)',
          fontSize: '0.6875rem',
          fontWeight: 700,
          color: 'var(--color-secondary)',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          marginBottom: '1rem',
        }}>
          BigLaw BD Intelligence
        </div>

        <h1 style={{
          fontFamily: 'var(--font-editorial)',
          fontSize: 'clamp(2rem, 5vw, 3.5rem)',
          fontWeight: 400,
          color: 'var(--color-primary)',
          lineHeight: 1.15,
          letterSpacing: '-0.02em',
          marginBottom: '1.5rem',
        }}>
          Predict Who Needs a Lawyer —<br />Before They Call
        </h1>

        <p style={{
          fontFamily: 'var(--font-data)',
          fontSize: '1rem',
          color: 'var(--color-on-surface-variant)',
          maxWidth: 600,
          margin: '0 auto 2.5rem',
          lineHeight: 1.6,
          letterSpacing: '0.01em',
        }}>
          28 signal types. 34 practice areas. 30/60/90 day horizons.
          Machine learning scores mandate probability across the full matrix
          so your partners know who to call — and when.
        </p>

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => navigate('/login')}
            style={{
              padding: '12px 28px',
              background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
              color: 'var(--color-on-primary)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
              transition: 'opacity 150ms ease-out',
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = '0.9'}
            onMouseLeave={e => e.currentTarget.style.opacity = '1'}
          >
            Access Dashboard
          </button>
          <button
            onClick={() => document.getElementById('signals-section')?.scrollIntoView({ behavior: 'smooth' })}
            style={{
              padding: '12px 28px',
              background: 'var(--color-secondary-container)',
              color: 'var(--color-on-secondary-container)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
              transition: 'opacity 150ms ease-out',
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
            onMouseLeave={e => e.currentTarget.style.opacity = '1'}
          >
            Explore Signals
          </button>
        </div>
      </section>


      {/* ── Signal Types Grid ─────────────────────────────────── */}
      <section id="signals-section" style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: '0 2rem 5rem',
      }}>
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div style={{
            fontFamily: 'var(--font-data)',
            fontSize: '0.6875rem',
            fontWeight: 700,
            color: 'var(--color-secondary)',
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            marginBottom: 8,
          }}>
            Intelligence Sources
          </div>
          <h2 style={{
            fontFamily: 'var(--font-editorial)',
            fontSize: '1.5rem',
            fontWeight: 500,
            color: 'var(--color-primary)',
            letterSpacing: '-0.01em',
          }}>
            28 Signal Types. One Score.
          </h2>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '1.25rem',
        }}>
          {SIGNAL_TYPES.map(sig => (
            <div key={sig.type} style={{
              background: 'var(--color-surface-container-lowest)',
              borderRadius: 'var(--radius-xl)',
              padding: '1.5rem',
              boxShadow: 'var(--shadow-ambient)',
              transition: 'transform 200ms ease-out',
            }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <div style={{ fontSize: 28, marginBottom: 12 }}>{sig.icon}</div>
              <h3 style={{
                fontFamily: 'var(--font-data)',
                fontWeight: 600,
                fontSize: '0.875rem',
                color: 'var(--color-on-surface)',
                marginBottom: 8,
              }}>
                {sig.type}
              </h3>
              <p style={{
                fontFamily: 'var(--font-data)',
                fontSize: '0.875rem',
                color: 'var(--color-on-surface-variant)',
                lineHeight: 1.6,
                letterSpacing: '0.01em',
              }}>
                {sig.desc}
              </p>
            </div>
          ))}
        </div>
      </section>


      {/* ── Practice Area Chips ────────────────────────────────── */}
      <section style={{
        background: 'var(--color-surface-container-low)',
        padding: '4rem 2rem',
      }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
            <div style={{
              fontFamily: 'var(--font-data)',
              fontSize: '0.6875rem',
              fontWeight: 700,
              color: 'var(--color-secondary)',
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              marginBottom: 8,
            }}>
              Full Coverage
            </div>
            <h2 style={{
              fontFamily: 'var(--font-editorial)',
              fontSize: '1.5rem',
              fontWeight: 500,
              color: 'var(--color-primary)',
              letterSpacing: '-0.01em',
            }}>
              34 Practice Areas × 3 Horizons
            </h2>
          </div>

          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            justifyContent: 'center',
          }}>
            {PRACTICE_AREAS.map(pa => (
              <span key={pa} style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '6px 14px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--color-surface-container-lowest)',
                fontFamily: 'var(--font-data)',
                fontSize: '0.75rem',
                fontWeight: 600,
                color: 'var(--color-on-surface-variant)',
                letterSpacing: '0.02em',
                boxShadow: 'var(--shadow-ambient)',
              }}>
                {pa}
              </span>
            ))}
          </div>
        </div>
      </section>


      {/* ── Stats / Social Proof ──────────────────────────────── */}
      <section style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: '5rem 2rem',
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr',
          gap: '3rem',
          alignItems: 'center',
        }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-data)',
              fontSize: '0.6875rem',
              fontWeight: 700,
              color: 'var(--color-secondary)',
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              marginBottom: 8,
            }}>
              How It Works
            </div>
            <h2 style={{
              fontFamily: 'var(--font-editorial)',
              fontSize: '1.5rem',
              fontWeight: 500,
              color: 'var(--color-primary)',
              letterSpacing: '-0.01em',
              marginBottom: '1.5rem',
            }}>
              ML Models Score. Partners Act.
            </h2>
            <p style={{
              fontFamily: 'var(--font-data)',
              fontSize: '0.875rem',
              color: 'var(--color-on-surface-variant)',
              lineHeight: 1.8,
              letterSpacing: '0.01em',
              maxWidth: 500,
            }}>
              ORACLE's scoring engine processes signals daily through calibrated ML models.
              Each company receives a probability score for each of 34 practice areas
              across three time horizons (30, 60, and 90 days). SHAP explanations
              surface the features driving each score — so partners see the reasoning,
              not just the number.
            </p>
          </div>

          <div style={{
            background: 'var(--color-surface-container-lowest)',
            borderRadius: 'var(--radius-xl)',
            padding: '2rem',
            boxShadow: 'var(--shadow-ambient)',
          }}>
            {[
              { label: 'Practice Areas', value: '34' },
              { label: 'Signal Types', value: '28' },
              { label: 'Time Horizons', value: '3' },
              { label: 'ML Engines', value: '34' },
            ].map((s, i) => (
              <div key={s.label} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: i % 2 === 1 ? 'var(--color-surface-container-low)' : 'transparent',
                margin: i % 2 === 1 ? '0 -2rem' : 0,
                padding: i % 2 === 1 ? '1rem 2rem' : '1rem 0',
              }}>
                <span style={{
                  fontFamily: 'var(--font-data)',
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  color: 'var(--color-on-surface-variant)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}>{s.label}</span>
                <span style={{
                  fontFamily: 'var(--font-editorial)',
                  fontSize: '1.5rem',
                  fontWeight: 500,
                  color: 'var(--color-primary)',
                  letterSpacing: '-0.01em',
                }}>{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>


      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer style={{
        background: 'var(--color-surface-container-low)',
        padding: '2rem 3rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{
          fontFamily: 'var(--font-editorial)',
          fontSize: 16,
          fontWeight: 500,
          color: 'var(--color-primary)',
          letterSpacing: '-0.01em',
        }}>
          ORACLE
        </span>
        <span style={{
          fontFamily: 'var(--font-data)',
          fontSize: '0.6875rem',
          color: 'var(--color-on-surface-variant)',
          letterSpacing: '0.05em',
        }}>
          BD Intelligence Platform · Halcyon Legal
        </span>
      </footer>
    </div>
  )
}
