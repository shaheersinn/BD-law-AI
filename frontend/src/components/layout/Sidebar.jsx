/**
 * components/layout/Sidebar.jsx — ConstructLex Pro sidebar navigation.
 *
 * Fixed 240px left sidebar. Collapses to 64px icon-only on demand.
 * Firm logo placeholder at bottom.
 */

import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import useAuthStore from '../../stores/auth'

/* ── SVG icon primitives ─────────────────────────────────────────────────── */
const Icon = ({ d, size = 18, stroke = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={stroke} strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
)

const icons = {
  dashboard:  'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  search:     'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  signals:    'M13 10V3L4 14h7v7l9-11h-7z',
  admin:      'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
  users:      'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
  scrapers:   'M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18',
  logout:     'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1',
  chevron:    'M11 19l-7-7 7-7m8 14l-7-7 7-7',
  expand:     'M13 5l7 7-7 7M5 5l7 7-7 7',
}

const navItems = [
  { path: '/dashboard', label: 'Dashboard',  icon: 'dashboard' },
  { path: '/search',    label: 'Search',     icon: 'search' },
  { path: '/signals',   label: 'Signals',    icon: 'signals' },
]

const adminItems = [
  { path: '/admin/scrapers', label: 'Scrapers', icon: 'scrapers' },
  { path: '/admin/users',    label: 'Users',    icon: 'users' },
]

export default function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)

  const isActive = (path) => location.pathname.startsWith(path)
  const w = collapsed ? 64 : 240

  const navItem = (item) => {
    const active = isActive(item.path)
    return (
      <button
        key={item.path}
        onClick={() => navigate(item.path)}
        title={collapsed ? item.label : undefined}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: collapsed ? 0 : 10,
          width: '100%',
          padding: collapsed ? '10px 0' : '9px 14px',
          justifyContent: collapsed ? 'center' : 'flex-start',
          background: active ? 'var(--accent-light)' : 'transparent',
          border: 'none',
          borderRadius: 'var(--radius-md)',
          color: active ? 'var(--accent)' : 'var(--text-secondary)',
          fontWeight: active ? 600 : 400,
          fontSize: 13,
          cursor: 'pointer',
          transition: 'background var(--transition), color var(--transition)',
          marginBottom: 2,
          position: 'relative',
        }}
        onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--surface-hover)'; e.currentTarget.style.color = 'var(--text)' }}
        onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)' } }}
      >
        {/* Active indicator bar */}
        {active && (
          <span style={{
            position: 'absolute', left: 0, top: '20%', bottom: '20%',
            width: 3, background: 'var(--accent)', borderRadius: '0 2px 2px 0',
          }} />
        )}
        <Icon d={icons[item.icon]} size={16} />
        {!collapsed && <span>{item.label}</span>}
      </button>
    )
  }

  return (
    <>
      {/* Sidebar */}
      <aside style={{
        position: 'fixed',
        top: 0, left: 0, bottom: 0,
        width: w,
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
        transition: 'width var(--transition)',
        overflow: 'hidden',
      }}>
        {/* Logo / brand */}
        <div style={{
          padding: collapsed ? '20px 0' : '20px 18px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          flexShrink: 0,
        }}>
          {!collapsed && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {/* Wordmark */}
              <div style={{
                width: 32, height: 32,
                background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                borderRadius: 8,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <span style={{ color: '#fff', fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-display)', letterSpacing: 1 }}>O</span>
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 18, color: 'var(--text)', lineHeight: 1.1, letterSpacing: '0.02em' }}>
                  ORACLE
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-tertiary)', letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 500 }}>
                  BD Intelligence
                </div>
              </div>
            </div>
          )}
          {collapsed && (
            <div style={{
              width: 32, height: 32,
              background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
              borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span style={{ color: '#fff', fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-display)' }}>O</span>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              title="Collapse sidebar"
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', padding: 4, borderRadius: 4 }}
            >
              <Icon d={icons.chevron} size={14} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: collapsed ? '12px 8px' : '12px 10px', overflowY: 'auto' }}>
          {navItems.map(navItem)}

          {/* Admin section */}
          {user?.role === 'admin' && (
            <>
              {!collapsed && (
                <div style={{
                  fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)',
                  textTransform: 'uppercase', letterSpacing: '0.1em',
                  padding: '16px 6px 6px',
                }}>
                  Admin
                </div>
              )}
              {collapsed && <div style={{ height: 16 }} />}
              {adminItems.map(navItem)}
            </>
          )}
        </nav>

        {/* User + sign out */}
        <div style={{
          padding: collapsed ? '12px 8px' : '12px 10px',
          borderTop: '1px solid var(--border)',
          flexShrink: 0,
        }}>
          {!collapsed && user && (
            <div style={{
              fontSize: 11, color: 'var(--text-tertiary)',
              marginBottom: 8, padding: '0 6px',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {user.email}
            </div>
          )}
          <button
            onClick={logout}
            title={collapsed ? 'Sign out' : undefined}
            style={{
              display: 'flex', alignItems: 'center',
              gap: collapsed ? 0 : 8,
              justifyContent: collapsed ? 'center' : 'flex-start',
              width: '100%', padding: collapsed ? '8px 0' : '8px 10px',
              background: 'none', border: 'none', borderRadius: 'var(--radius-md)',
              color: 'var(--text-secondary)', fontSize: 13, cursor: 'pointer',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; e.currentTarget.style.color = 'var(--error)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = 'var(--text-secondary)' }}
          >
            <Icon d={icons.logout} size={15} />
            {!collapsed && <span>Sign out</span>}
          </button>

          {/* Firm logo placeholder */}
          {!collapsed && (
            <div style={{
              marginTop: 16, padding: '8px 10px',
              border: '1px dashed var(--border)',
              borderRadius: 'var(--radius-md)',
              textAlign: 'center',
              fontSize: 10, color: 'var(--text-tertiary)',
              letterSpacing: '0.05em',
            }}>
              HALCYON LEGAL
            </div>
          )}
        </div>

        {/* Expand button when collapsed */}
        {collapsed && (
          <button
            onClick={() => setCollapsed(false)}
            title="Expand sidebar"
            style={{
              position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)',
              background: 'var(--surface-hover)', border: '1px solid var(--border)',
              borderRadius: '50%', width: 28, height: 28,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: 'var(--text-secondary)',
            }}
          >
            <Icon d={icons.expand} size={12} />
          </button>
        )}
      </aside>

      {/* Content offset shim — siblings get margin-left via AppShell */}
      <div id="sidebar-width-shim" data-width={w} style={{ display: 'none' }} />
    </>
  )
}
