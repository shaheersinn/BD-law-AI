/**
 * components/Sidebar.jsx — Digital Atelier sidebar navigation.
 *
 * Fixed 240px left panel. Active state via useLocation().
 * Shows admin section only for admin/partner roles.
 */

import { useLocation, useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/auth'

// ── Nav icons (inline SVG — no external dependency) ──────────────────────────

function IconDashboard() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
    </svg>
  )
}

function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function IconSignals() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  )
}

function IconScraper() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
    </svg>
  )
}

function IconUsers() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function IconLogout() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  )
}

// ── Nav item ──────────────────────────────────────────────────────────────────

function NavItem({ to, icon, label, onClick }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const isActive = to && pathname.startsWith(to)

  const handleClick = () => {
    if (onClick) { onClick(); return }
    if (to) navigate(to)
  }

  return (
    <button
      className={`cl-nav-link${isActive ? ' active' : ''}`}
      onClick={handleClick}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  const isPartner = user?.role === 'partner' || isAdmin

  return (
    <aside className="cl-sidebar">
      {/* Logo */}
      <div style={{
        padding: '1.5rem 1.25rem 1rem',
        marginBottom: '0.5rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34,
            height: 34,
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
            display: 'grid',
            placeItems: 'center',
            flexShrink: 0,
          }}>
            <span style={{ color: 'var(--color-on-primary)', fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-editorial)' }}>O</span>
          </div>
          <div>
            <div style={{
              fontFamily: 'var(--font-editorial)',
              fontSize: '1.05rem',
              fontWeight: 500,
              color: 'var(--color-primary)',
              lineHeight: 1.1,
              letterSpacing: '-0.01em',
            }}>
              ORACLE
            </div>
            <div style={{
              fontSize: '0.6875rem',
              color: 'var(--color-on-surface-variant)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              fontWeight: 700,
              fontFamily: 'var(--font-data)',
            }}>
              BD Intelligence
            </div>
          </div>
        </div>
      </div>

      {/* Primary nav */}
      <div className="cl-nav-section">
        <NavItem to="/dashboard" icon={<IconDashboard />} label="Dashboard" />
        <NavItem to="/search"    icon={<IconSearch />}    label="Search Companies" />
        <NavItem to="/signals"   icon={<IconSignals />}   label="Signal Feed" />
      </div>

      {/* Admin section */}
      {isPartner && (
        <>
          <div style={{ margin: '0.75rem 0 0.25rem' }}>
            <div className="cl-nav-section">
              <div className="cl-nav-section-label">Admin</div>
              {isAdmin && (
                <>
                  <NavItem to="/admin/scrapers" icon={<IconScraper />} label="Scraper Health" />
                  <NavItem to="/admin/users"    icon={<IconUsers />}   label="Users" />
                </>
              )}
            </div>
          </div>
        </>
      )}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* User / logout */}
      <div style={{
        padding: '1rem 1.25rem',
      }}>
        {user && (
          <div style={{
            fontSize: '0.78rem',
            color: 'var(--color-on-surface-variant)',
            marginBottom: 8,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontFamily: 'var(--font-data)',
          }}>
            <span style={{
              display: 'inline-block',
              padding: '1px 6px',
              background: 'var(--color-surface-container-high)',
              borderRadius: 'var(--radius-full)',
              fontSize: '0.6875rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--color-secondary)',
              marginRight: 6,
            }}>
              {user.role}
            </span>
            {user.email}
          </div>
        )}
        <NavItem icon={<IconLogout />} label="Sign out" onClick={logout} />
      </div>
    </aside>
  )
}
