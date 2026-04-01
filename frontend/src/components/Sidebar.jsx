/**
 * components/Sidebar.jsx — Stitch icon-rail navigation (PR #19).
 *
 * Single source of truth for authenticated nav. Lucide icons only.
 */

import { useLocation, useNavigate } from 'react-router-dom'
import {
  BarChart3,
  Activity,
  Radar,
  Target,
  FileSearch,
  Zap,
  Users,
  PieChart,
  UserCircle,
  Trophy,
  GraduationCap,
  Swords,
  Search,
  Scale,
  MessageSquare,
  Database,
  UserCog,
  Gauge,
  Rss,
  LogOut,
} from 'lucide-react'
import useAuthStore from '../stores/auth'

function NavItem({ to, icon: Icon, label, onClick }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const isActive = to && pathname.startsWith(to)

  const handleClick = () => {
    if (onClick) {
      onClick()
      return
    }
    if (to) navigate(to)
  }

  return (
    <button
      type="button"
      title={label}
      onClick={handleClick}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 4,
        width: '100%',
        padding: '10px 0',
        borderRadius: 'var(--radius-xl)',
        cursor: 'pointer',
        background: isActive ? 'var(--color-surface-container-lowest)' : 'transparent',
        color: isActive
          ? 'var(--color-on-secondary-container)'
          : 'var(--color-on-surface-variant)',
        boxShadow: isActive ? 'var(--shadow-ambient)' : 'none',
        transition: 'color var(--transition-fast), background var(--transition-fast)',
        border: 'none',
      }}
      onMouseEnter={(e) => {
        if (!isActive) e.currentTarget.style.color = 'var(--color-primary)'
      }}
      onMouseLeave={(e) => {
        if (!isActive) e.currentTarget.style.color = 'var(--color-on-surface-variant)'
      }}
    >
      <Icon size={20} strokeWidth={1.5} />
      <span
        style={{
          fontFamily: 'var(--font-data)',
          fontSize: '0.5625rem',
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          lineHeight: 1,
        }}
      >
        {label}
      </span>
    </button>
  )
}

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  const isPartner = user?.role === 'partner' || isAdmin

  return (
    <aside
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        bottom: 0,
        width: 80,
        background: 'var(--color-surface-container-low)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '0.75rem 0.5rem',
        zIndex: 100,
        overflowY: 'auto',
        overflowX: 'hidden',
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 'var(--radius-md)',
          background:
            'linear-gradient(to bottom, var(--color-primary), var(--color-primary-container))',
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
          marginBottom: '1rem',
        }}
      >
        <span
          style={{
            color: 'var(--color-on-primary)',
            fontSize: 14,
            fontWeight: 700,
            fontFamily: 'var(--font-editorial)',
          }}
        >
          O
        </span>
      </div>

      <nav
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          width: '100%',
        }}
      >
        <NavItem to="/constructlex" icon={BarChart3} label="MRKT" />
        <NavItem to="/live-triggers" icon={Activity} label="FEED" />
        <NavItem to="/signals" icon={Rss} label="SIGS" />
        <NavItem to="/m-a-dark-signals" icon={Radar} label="M&A" />
        <NavItem to="/precrime" icon={Target} label="ACQN" />
        <NavItem to="/mandate-formation" icon={FileSearch} label="MAND" />
        <NavItem to="/regulatory-ripple" icon={Zap} label="REG" />
        <NavItem to="/churn-predictor" icon={Users} label="CHURN" />
        <NavItem to="/wallet-share" icon={PieChart} label="WLLT" />
        <NavItem to="/gc-profiler" icon={UserCircle} label="GC" />
        <NavItem to="/pitch-autopsy" icon={Trophy} label="PITCH" />
        <NavItem to="/associate-accelerator" icon={GraduationCap} label="ASSOC" />
        <NavItem to="/competitive-intel" icon={Swords} label="COMP" />
        <NavItem to="/search" icon={Search} label="SRCH" />
        <NavItem to="/class-action-radar" icon={Scale} label="LAW" />
        {isPartner && <NavItem to="/feedback" icon={MessageSquare} label="FDBK" />}
        {isAdmin && (
          <>
            <NavItem to="/admin/scrapers" icon={Database} label="SCRP" />
            <NavItem to="/admin/users" icon={UserCog} label="USR" />
            <NavItem to="/admin/optimization" icon={Gauge} label="OPT" />
          </>
        )}
      </nav>

      <div style={{ flex: 1 }} />

      <NavItem icon={LogOut} label="OUT" onClick={logout} />
    </aside>
  )
}
