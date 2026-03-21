import React, { useState } from 'react'
import { gcProfiles, clients } from '../../data/mockData.js'
import { PageHeader, Tag, Section, Spinner, AIBadge, MetricCard } from '../ui/index.jsx'

const TRUST_DIMS = ['Credibility', 'Reliability', 'Intimacy', 'Self-Orientation']

export default function GCProfiler() {
  const [selectedProfile, setSelectedProfile] = useState(gcProfiles[0])
  const [customInput, setCustomInput] = useState('')
  const [customCompany, setCustomCompany] = useState('')
  const [aiProfile, setAiProfile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('existing')

  async function generateProfile() {
    if (!customInput.trim()) return
    setLoading(true)
    setAiProfile(null)
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1200,
          messages: [{
            role: 'user',
            content: `You are an AI that builds psychographic profiles of General Counsels and Chief Legal Officers for law firm business development. Analyze the following public information about this GC and produce a structured intelligence brief.

GC/CLO Information Provided:
Company: ${customCompany || 'Unknown'}
${customInput}

Respond with a JSON object (no markdown, pure JSON) with these fields:
{
  "name": "inferred name or 'Unknown GC'",
  "title": "title or 'General Counsel'",
  "decision_style": "one-line description",
  "risk_tolerance": "Low / Medium / High",
  "communication_pref": "one-line description",
  "relationship_type": "Transaction-focused / Relationship-driven / Mixed",
  "fee_sensitivity": "Low / Medium / High — with one-line context",
  "career_ambition": "one-line observation",
  "key_concerns": ["concern 1", "concern 2", "concern 3"],
  "pitch_hooks": ["hook 1", "hook 2", "hook 3"],
  "credibility_score": 65,
  "reliability_score": 70,
  "intimacy_score": 45,
  "self_orientation_score": 60,
  "overall_trust_score": 60,
  "meeting_brief": "2-3 sentence pre-meeting brief for a senior partner"
}

All scores are 0-100. Self-orientation is INVERTED (low = they think about the client, high = they focus on billing — so lower is better for trust). Be insightful and specific based on the provided information.`
          }]
        })
      })
      const data = await res.json()
      const text = data.content?.[0]?.text || '{}'
      try {
        setAiProfile(JSON.parse(text.replace(/```json|```/g, '').trim()))
      } catch {
        setAiProfile({ meeting_brief: text, key_concerns: [], pitch_hooks: [], credibility_score: 0, reliability_score: 0, intimacy_score: 0, self_orientation_score: 0, overall_trust_score: 0 })
      }
    } catch { setAiProfile({ meeting_brief: 'API error.', key_concerns: [], pitch_hooks: [] }) }
    setLoading(false)
  }

  const displayProfile = activeTab === 'ai' && aiProfile ? aiProfile : (activeTab === 'existing' ? selectedProfile?.psychographic : null)

  const TrustDial = ({ label, score, invert }) => {
    const effectiveScore = invert ? (100 - score) : score
    const color = effectiveScore >= 70 ? 'var(--accent-green)' : effectiveScore >= 40 ? 'var(--accent-gold)' : 'var(--accent-red)'
    return (
      <div style={{ textAlign: 'center' }}>
        <div style={{ position: 'relative', width: 60, height: 60, margin: '0 auto 6px' }}>
          <svg viewBox="0 0 60 60" style={{ transform: 'rotate(-90deg)' }}>
            <circle cx="30" cy="30" r="24" fill="none" stroke="var(--border)" strokeWidth="4" />
            <circle cx="30" cy="30" r="24" fill="none" stroke={color} strokeWidth="4"
              strokeDasharray={`${effectiveScore * 1.508} 150.8`} strokeLinecap="round" />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 600, color }}>
            {effectiveScore}
          </div>
        </div>
        <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.04em' }}>{label}</div>
        {invert && <div style={{ fontSize: 8, color: 'var(--text-muted)', marginTop: 1 }}>(inverted)</div>}
      </div>
    )
  }

  return (
    <div className="animate-fade-in" style={{ height: '100%', overflowY: 'auto', padding: '20px 24px' }}>
      <PageHeader
        tag="Relationship Intelligence"
        title="GC Psychographic Profiler"
        subtitle="Scrapes every public signal a GC has left — speeches, articles, LinkedIn, earnings calls — and builds a decision-making profile. Generates a pre-meeting intelligence brief in 90 seconds."
      />

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        <button className={`tab-btn ${activeTab === 'existing' ? 'active' : ''}`} onClick={() => setActiveTab('existing')}>
          Saved Profiles ({gcProfiles.length})
        </button>
        <button className={`tab-btn ${activeTab === 'ai' ? 'active' : ''}`} onClick={() => setActiveTab('ai')}>
          ◈ AI Profile Generator
        </button>
      </div>

      {activeTab === 'existing' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 14 }}>
          {/* GC list */}
          <div className="panel" style={{ padding: 0 }}>
            {gcProfiles.map(p => (
              <div
                key={p.id}
                onClick={() => setSelectedProfile(p)}
                style={{
                  padding: '14px 16px',
                  borderBottom: '1px solid var(--border)',
                  cursor: 'pointer',
                  background: selectedProfile?.id === p.id ? 'var(--bg-elevated)' : 'transparent',
                  borderLeft: selectedProfile?.id === p.id ? '2px solid var(--accent-gold)' : '2px solid transparent',
                }}
              >
                <div style={{ fontWeight: 500, fontSize: 13 }}>{p.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{p.title}</div>
                <div style={{ fontSize: 11, color: 'var(--accent-gold)', marginTop: 2 }}>{p.company}</div>
                <div style={{ marginTop: 6, display: 'flex', gap: 6 }}>
                  <Tag color="default">Trust: {p.trust_score}</Tag>
                </div>
              </div>
            ))}
          </div>

          {/* Profile detail */}
          {selectedProfile && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="panel" style={{ padding: '18px 20px' }}>
                <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 20, letterSpacing: '-0.02em' }}>{selectedProfile.name}</div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>{selectedProfile.title} · {selectedProfile.company}</div>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 12 }}>{selectedProfile.linkedin_summary}</p>

                <div style={{ display: 'flex', justifyContent: 'space-around', padding: '14px 0', borderTop: '1px solid var(--border)' }}>
                  <TrustDial label="CREDIBILITY" score={selectedProfile.trust_score - 5} />
                  <TrustDial label="RELIABILITY" score={selectedProfile.trust_score + 10} />
                  <TrustDial label="INTIMACY" score={selectedProfile.trust_score - 15} />
                  <TrustDial label="SELF-ORIENT" score={100 - selectedProfile.trust_score} invert />
                  <TrustDial label="OVERALL TRUST" score={selectedProfile.trust_score} />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div className="panel" style={{ padding: '14px 16px' }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>Psychographic Profile</div>
                  {Object.entries(selectedProfile.psychographic).map(([key, val]) => (
                    <div key={key} style={{ display: 'flex', gap: 10, paddingBottom: 8, marginBottom: 8, borderBottom: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", width: 130, flexShrink: 0, textTransform: 'capitalize', lineHeight: 1.4 }}>
                        {key.replace(/_/g, ' ')}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{val}</div>
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div className="panel" style={{ padding: '14px 16px' }}>
                    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>Key Concerns</div>
                    {selectedProfile.key_concerns.map((c, i) => (
                      <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                        <span style={{ color: 'var(--accent-red)', fontSize: 10, marginTop: 3 }}>▸</span>
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{c}</span>
                      </div>
                    ))}
                  </div>
                  <div className="panel" style={{ padding: '14px 16px' }}>
                    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12 }}>Pitch Hooks</div>
                    {selectedProfile.pitch_hooks.map((h, i) => (
                      <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                        <span style={{ color: 'var(--accent-green)', fontSize: 10, marginTop: 3 }}>◉</span>
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{h}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div className="panel" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Profile a New GC</div>
              <AIBadge />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", display: 'block', marginBottom: 6 }}>Company Name</label>
              <input className="oracle-input" placeholder="e.g. Pinnacle Health Systems" value={customCompany} onChange={e => setCustomCompany(e.target.value)} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", display: 'block', marginBottom: 6 }}>Public Information (LinkedIn bio, speeches, articles, news mentions)</label>
              <textarea
                className="oracle-input"
                rows={10}
                placeholder="Paste any publicly available information about the GC here — LinkedIn About section, quotes from interviews, panel bios, published articles, conference speech topics, or any news mentions..."
                value={customInput}
                onChange={e => setCustomInput(e.target.value)}
              />
            </div>
            <button className="oracle-btn oracle-btn-primary" onClick={generateProfile} disabled={loading || !customInput.trim()} style={{ width: '100%' }}>
              {loading ? 'Analyzing...' : '◈ Generate Psychographic Profile'}
            </button>
          </div>

          <div>
            {loading ? (
              <div className="panel" style={{ padding: '40px 20px', display: 'flex', justifyContent: 'center' }}>
                <Spinner />
              </div>
            ) : aiProfile ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div className="panel" style={{ padding: '18px 20px' }}>
                  <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 20, letterSpacing: '-0.02em' }}>{aiProfile.name}</div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>{aiProfile.title} · {customCompany}</div>

                  <div style={{ background: 'rgba(232,168,58,0.05)', border: '1px solid rgba(232,168,58,0.2)', borderRadius: 3, padding: '12px 14px', marginBottom: 14 }}>
                    <div style={{ fontSize: 10, color: 'var(--accent-gold)', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>PRE-MEETING BRIEF</div>
                    <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)' }}>{aiProfile.meeting_brief}</div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-around', paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                    <TrustDial label="CREDIBILITY" score={aiProfile.credibility_score || 0} />
                    <TrustDial label="RELIABILITY" score={aiProfile.reliability_score || 0} />
                    <TrustDial label="INTIMACY" score={aiProfile.intimacy_score || 0} />
                    <TrustDial label="SELF-ORIENT" score={aiProfile.self_orientation_score || 0} invert />
                    <TrustDial label="TRUST SCORE" score={aiProfile.overall_trust_score || 0} />
                  </div>
                </div>

                {aiProfile.key_concerns?.length > 0 && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                    <div className="panel" style={{ padding: '14px 16px' }}>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>Key Concerns</div>
                      {aiProfile.key_concerns.map((c, i) => (
                        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                          <span style={{ color: 'var(--accent-red)', fontSize: 10, marginTop: 3 }}>▸</span>
                          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{c}</span>
                        </div>
                      ))}
                    </div>
                    <div className="panel" style={{ padding: '14px 16px' }}>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>Pitch Hooks</div>
                      {(aiProfile.pitch_hooks || []).map((h, i) => (
                        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                          <span style={{ color: 'var(--accent-green)', fontSize: 10, marginTop: 3 }}>◉</span>
                          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{h}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="panel" style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: 28, marginBottom: 10 }}>◈</div>
                <div style={{ fontSize: 13 }}>Paste any public information about a GC and ORACLE will build a complete psychographic profile — decision style, risk tolerance, fee sensitivity, communication preferences, and a pre-meeting brief.</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )

  function TrustDial({ label, score, invert }) {
    const effectiveScore = invert ? (100 - score) : score
    const color = effectiveScore >= 70 ? 'var(--accent-green)' : effectiveScore >= 40 ? 'var(--accent-gold)' : 'var(--accent-red)'
    return (
      <div style={{ textAlign: 'center' }}>
        <div style={{ position: 'relative', width: 60, height: 60, margin: '0 auto 6px' }}>
          <svg viewBox="0 0 60 60" style={{ transform: 'rotate(-90deg)' }}>
            <circle cx="30" cy="30" r="24" fill="none" stroke="var(--border)" strokeWidth="4" />
            <circle cx="30" cy="30" r="24" fill="none" stroke={color} strokeWidth="4"
              strokeDasharray={`${effectiveScore * 1.508} 150.8`} strokeLinecap="round" />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 600, color }}>
            {effectiveScore}
          </div>
        </div>
        <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.04em' }}>{label}</div>
      </div>
    )
  }
}
