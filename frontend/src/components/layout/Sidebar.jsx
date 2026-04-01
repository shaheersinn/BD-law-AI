/**
 * components/layout/Sidebar.jsx — Digital Atelier sidebar navigation.
 *
 * Fixed 240px left sidebar. Collapses to 64px icon-only on demand.
 * Uses surface-container-low background, ambient shadow (no border).
 * Active state via surface-container-high shift (no colored indicator).
 * Section headers: Manrope 11px label-sm, all-caps.
 */

import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import useAuthStore from '../../stores/auth'

/* ── SVG icon primitives (1.5px stroke per DESIGN.md) ──────────────────── */
const Icon = ({ d, size = 18, stroke = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={stroke} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
)

const icons = {
  dashboard:  'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  search:     'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  signals:    'M13 10V3L4 14h7v7l9-11h-7z',
  feedback:   'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  admin:      'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
  users:      'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
  scrapers:   'M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18',
  logout:     'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1',
  chevron:    'M11 19l-7-7 7-7m8 14l-7-7 7-7',
  expand:     'M13 5l7 7-7 7M5 5l7 7-7 7',
  modules:    'M4 6h16M4 12h8m-8 6h16',
  geo:        'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z',
  law:        'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z',
}

const navItems = [
  { path: '/dashboard', label: 'Dashboard',    icon: 'dashboard' },
  { path: '/signals',   label: 'Signals',      icon: 'signals' },
  { path: '/search',    label: 'Search',       icon: 'search' },
  { path: '/modules',   label: 'Modules',      icon: 'modules' },
  { path: '/geo',       label: 'Geo Intel',    icon: 'geo' },
  { path: '/class-action-radar', label: 'Class Actions', icon: 'law' },
  { path: '/feedback',  label: 'Feedback',     icon: 'feedback', roles: ['partner', 'admin'] },
]

const adminItems = [
  { path: '/admin/scrapers',    label: 'Scrapers',   icon: 'scrapers' },
  { path: '/scraper-dashboard', label: 'Scraper DB', icon: 'scrapers' },
  { path: '/admin/users',       label: 'Users',      icon: 'users' },
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
          background: active
            ? 'var(--color-surface-container-highest)'
            : 'transparent',
          borderRadius: 'var(--radius-md)',
          color: active
            ? 'var(--color-on-surface)'
            : 'var(--color-on-surface-variant)',
          fontWeight: active ? 600 : 400,
          fontFamily: 'var(--font-data)',
          fontSize: 14,
          cursor: 'pointer',
          transition: 'background 150ms ease-out, color 150ms ease-out',
          marginBottom: 2,
          letterSpacing: '0.01em',
        }}
        onMouseEnter={e => {
          if (!active) {
            e.currentTarget.style.background = 'var(--color-surface-container-high)'
            e.currentTarget.style.color = 'var(--color-on-surface)'
          }
        }}
        onMouseLeave={e => {
          if (!active) {
            e.currentTarget.style.background = 'transparent'
            e.currentTarget.style.color = 'var(--color-on-surface-variant)'
          }
        }}
      >
        <Icon d={icons[item.icon]} size={16} />
        {!collapsed && <span>{item.label}</span>}
      </button>
    )
  }

  return (
    <>
      {/* Sidebar — surface-container-low bg, ambient shadow, no border */}
      <aside style={{
        position: 'fixed',
        top: 0, left: 0, bottom: 0,
        width: w,
        background: 'var(--color-surface-container-low)',
        boxShadow: 'var(--shadow-ambient)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
        transition: 'width 150ms ease-out',
        overflow: 'hidden',
      }}>
        {/* Logo / brand */}
        <div style={{
          padding: collapsed ? '20px 0' : '20px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          flexShrink: 0,
          marginBottom: 10,
        }}>
          {!collapsed && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 32, height: 32,
                background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
                borderRadius: 'var(--radius-md)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <span style={{
                  color: 'var(--color-on-primary)',
                  fontSize: 14,
                  fontWeight: 700,
                  fontFamily: 'var(--font-editorial)',
                  letterSpacing: 1,
                }}>O</span>
              </div>
              <div>
                <div style={{
                  fontFamily: 'var(--font-editorial)',
                  fontWeight: 500,
                  fontSize: 18,
                  color: 'var(--color-primary)',
                  lineHeight: 1.1,
                  letterSpacing: '-0.01em',
                }}>
                  ORACLE
                </div>
                <div style={{
                  fontFamily: 'var(--font-data)',
                  fontSize: 11,
                  fontWeight: 700,
                  color: 'var(--color-on-primary-container)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}>
                  BD Intelligence
                </div>
              </div>
            </div>
          )}
          {collapsed && (
            <div style={{
              width: 32, height: 32,
              background: 'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
              borderRadius: 'var(--radius-md)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span style={{
                color: 'var(--color-on-primary)',
                fontSize: 14,
                fontWeight: 700,
                fontFamily: 'var(--font-editorial)',
              }}>O</span>
            </div>
          )}
          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              title="Collapse sidebar"
              style={{
                background: 'none',
                cursor: 'pointer',
                color: 'var(--color-on-surface-variant)',
                padding: 4,
                borderRadius: 4,
              }}
            >
              <Icon d={icons.chevron} size={14} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: collapsed ? '12px 8px' : '12px 10px', overflowY: 'auto' }}>
          {navItems
            .filter(item => !item.roles || item.roles.includes(user?.role))
            .map(navItem)}

          {/* Admin section */}
          {user?.role === 'admin' && (
            <>
              {!collapsed && (
                <div style={{
                  fontFamily: 'var(--font-data)',
                  fontSize: 11,
                  fontWeight: 700,
                  color: 'var(--color-on-surface-variant)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
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
          flexShrink: 0,
        }}>
          {!collapsed && user && (
            <div style={{
              fontFamily: 'var(--font-data)',
              fontSize: 11,
              color: 'var(--color-on-surface-variant)',
              marginBottom: 8,
              padding: '0 6px',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {user.email}
            </div>
          )}
          <button
            onClick={logout}
            title={collapsed ? 'Sign out' : undefined}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: collapsed ? 0 : 8,
              justifyContent: collapsed ? 'center' : 'flex-start',
              width: '100%',
              padding: collapsed ? '8px 0' : '8px 10px',
              background: 'none',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-on-surface-variant)',
              fontFamily: 'var(--font-data)',
              fontSize: 13,
              cursor: 'pointer',
              transition: 'background 150ms ease-out, color 150ms ease-out',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'var(--color-surface-container-high)'
              e.currentTarget.style.color = 'var(--color-error)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'none'
              e.currentTarget.style.color = 'var(--color-on-surface-variant)'
            }}
          >
            <Icon d={icons.logout} size={15} />
            {!collapsed && <span>Sign out</span>}
          </button>

          {/* Firm logo placeholder */}
          {!collapsed && (
            <div style={{
              marginTop: 16,
              padding: '8px 10px',
              background: 'var(--color-surface-container-high)',
              borderRadius: 'var(--radius-md)',
              textAlign: 'center',
              fontFamily: 'var(--font-data)',
              fontSize: 10,
              fontWeight: 700,
              color: 'var(--color-on-surface-variant)',
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
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
              position: 'absolute',
              bottom: 12,
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'var(--color-surface-container-high)',
              borderRadius: '50%',
              width: 28,
              height: 28,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: 'var(--color-on-surface-variant)',
            }}
          >
            <Icon d={icons.expand} size={12} />
          </button>
        )}
      </aside>

      {/* Content offset shim */}
      <div id="sidebar-width-shim" data-width={w} style={{ display: 'none' }} />
    </>
  )
}
