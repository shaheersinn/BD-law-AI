/**
 * components/Sidebar.jsx — Full-width 220px sidebar navigation.
 *
 * Grouped nav sections with readable labels. Lucide icons only.
 * P1 redesign: DM Serif Display logo, DM Sans nav labels, section grouping.
 */

import { useLocation, useNavigate } from 'react-router-dom'
import {
  BarChart3,
  Activity,
  Rss,
  FileSearch,
  Target,
  TrendingUp,
  Radar,
  AlertTriangle,
  UserCircle,
  PieChart,
  Swords,
  Zap,
  Trophy,
  GraduationCap,
  MessageSquare,
  Search,
  Scale,
  Database,
  UserCog,
  Gauge,
  LogOut,
  ChevronRight,
} from 'lucide-react'
import useAuthStore from '../stores/auth'

// ── CSS injected once ─────────────────────────────────────────────────────────
const SIDEBAR_CSS = `
.sb-root {
  position: fixed;
  top: 0; left: 0; bottom: 0;
  width: 220px;
  background: var(--color-surface-container-lowest);
  display: flex;
  flex-direction: column;
  z-index: 100;
  overflow-y: auto;
  overflow-x: hidden;
  box-shadow: 1px 0 0 0 var(--color-surface-container-high);
}
.sb-logo-section {
  padding: 1.25rem 1rem 1rem;
  flex-shrink: 0;
}
.sb-logo-mark {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 0.25rem;
}
.sb-logo-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  background: linear-gradient(165deg, var(--color-primary), var(--color-primary-container));
  display: grid; place-items: center;
  flex-shrink: 0;
}
.sb-logo-o {
  color: #fff;
  font-family: var(--font-editorial);
  font-size: 16px;
  font-weight: 400;
}
.sb-logo-name {
  font-family: var(--font-editorial);
  font-size: 1.35rem;
  font-weight: 400;
  color: var(--color-primary);
  line-height: 1;
}
.sb-logo-sub {
  font-family: var(--font-data);
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-secondary);
  padding-left: 42px;
}
.sb-nav {
  flex: 1;
  padding: 0.5rem 0.625rem;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.sb-section { margin-bottom: 1rem; }
.sb-section-label {
  font-family: var(--font-data);
  font-size: 0.55rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-outline-variant);
  padding: 6px 8px 4px;
  display: block;
}
.sb-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background var(--transition-fast), color var(--transition-fast);
  font-family: var(--font-data);
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--color-on-surface-variant);
  margin-bottom: 1px;
}
.sb-item:hover {
  background: var(--color-surface-container-low);
  color: var(--color-on-surface);
}
.sb-item.active {
  background: var(--color-surface-container-low);
  color: var(--color-primary);
  font-weight: 600;
}
.sb-icon-wrap {
  width: 20px; height: 20px;
  border-radius: 6px;
  display: grid; place-items: center;
  flex-shrink: 0;
  background: transparent;
  transition: background var(--transition-fast);
}
.sb-item.active .sb-icon-wrap {
  background: var(--color-primary);
  color: #fff;
}
.sb-item.active .sb-icon-wrap svg {
  color: #fff;
}
.sb-spacer { flex: 1; }
.sb-footer {
  padding: 0.75rem 0.625rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sb-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
}
.sb-avatar {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: grid; place-items: center;
  font-family: var(--font-data);
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
}
.sb-user-info { flex: 1; min-width: 0; }
.sb-user-name {
  font-family: var(--font-data);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-on-surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sb-user-role {
  font-family: var(--font-data);
  font-size: 0.65rem;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.sb-logout {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 12px;
  border-radius: 10px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: var(--font-data);
  font-size: 0.82rem;
  color: var(--color-on-surface-variant);
  transition: background var(--transition-fast), color var(--transition-fast);
}
.sb-logout:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
}
`

function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('sb-styles')) {
    const el = document.createElement('style')
    el.id = 'sb-styles'
    el.textContent = SIDEBAR_CSS
    document.head.appendChild(el)
  }
}

function NavItem({ to, icon: Icon, label }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const isActive = to && (pathname === to || pathname.startsWith(to + '/'))

  return (
    <button
      type="button"
      onClick={() => to && navigate(to)}
      className={`sb-item${isActive ? ' active' : ''}`}
    >
      <span className="sb-icon-wrap">
        <Icon size={13} strokeWidth={2} />
      </span>
      {label}
    </button>
  )
}

function NavSection({ label, children }) {
  return (
    <div className="sb-section">
      <span className="sb-section-label">{label}</span>
      {children}
    </div>
  )
}

export default function Sidebar() {
  injectCSS()
  const { user, logout } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
    : (user?.email?.[0] || 'U').toUpperCase()

  return (
    <aside className="sb-root">
      {/* Logo */}
      <div className="sb-logo-section">
        <div className="sb-logo-mark">
          <div className="sb-logo-icon">
            <span className="sb-logo-o">O</span>
          </div>
          <span className="sb-logo-name">Oracle Intelligence</span>
        </div>
        <div className="sb-logo-sub">Executive Command</div>
      </div>

      {/* Navigation */}
      <nav className="sb-nav">
        <NavSection label="Intelligence">
          <NavItem to="/constructlex"       icon={BarChart3}      label="Command Center" />
          <NavItem to="/live-triggers"      icon={Activity}       label="Live Triggers" />
          <NavItem to="/signals"            icon={Rss}            label="Signal Feed" />
          <NavItem to="/mandate-formation"  icon={FileSearch}     label="Mandate Formation" />
        </NavSection>

        <NavSection label="Predictive">
          <NavItem to="/precrime"           icon={Target}         label="Pre-Crime Engine" />
          <NavItem to="/churn-predictor"    icon={TrendingUp}     label="Churn Predictor" />
          <NavItem to="/m-a-dark-signals"   icon={Radar}          label="M&A Dark Signals" />
          <NavItem to="/class-action-radar" icon={Scale}          label="Class Action Radar" />
        </NavSection>

        <NavSection label="Relationships">
          <NavItem to="/gc-profiler"        icon={UserCircle}     label="GC Profiler" />
          <NavItem to="/wallet-share"       icon={PieChart}       label="Wallet Share" />
          <NavItem to="/competitive-intel"  icon={Swords}         label="Competitive Intel" />
          <NavItem to="/regulatory-ripple"  icon={Zap}            label="Regulatory Ripple" />
        </NavSection>

        <NavSection label="Enablement">
          <NavItem to="/pitch-autopsy"         icon={Trophy}         label="Pitch Autopsy" />
          <NavItem to="/associate-accelerator" icon={GraduationCap}  label="Associate Program" />
          <NavItem to="/feedback"              icon={MessageSquare}  label="BD Coaching" />
          <NavItem to="/search"                icon={Search}         label="Search" />
        </NavSection>

        {isAdmin && (
          <NavSection label="Admin">
            <NavItem to="/admin/scrapers"      icon={Database}    label="Scrapers" />
            <NavItem to="/admin/users"         icon={UserCog}     label="Users" />
            <NavItem to="/admin/optimization"  icon={Gauge}       label="Optimization" />
          </NavSection>
        )}
      </nav>

      <div className="sb-spacer" />

      {/* Footer */}
      <div className="sb-footer">
        <div className="sb-user">
          <div className="sb-avatar">{initials}</div>
          <div className="sb-user-info">
            <div className="sb-user-name">{user?.name || user?.email || 'User'}</div>
            <div className="sb-user-role">{user?.role || 'partner'}</div>
          </div>
        </div>
        <button type="button" className="sb-logout" onClick={logout}>
          <LogOut size={14} strokeWidth={2} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
