import React, { useState } from 'react'
import Sidebar from './components/layout/Sidebar.jsx'
import Dashboard from './components/pages/Dashboard.jsx'
import ChurnPredictor from './components/pages/ChurnPredictor.jsx'
import RegulatoryRipple from './components/pages/RegulatoryRipple.jsx'
import RelationshipHeatMap from './components/pages/RelationshipHeatMap.jsx'
import PreCrimeAcquisition from './components/pages/PreCrimeAcquisition.jsx'
import MandatePreFormation from './components/pages/MandatePreFormation.jsx'
import MADarkSignals from './components/pages/MADarkSignals.jsx'
import CompetitiveIntel from './components/pages/CompetitiveIntel.jsx'
import WalletShare from './components/pages/WalletShare.jsx'
import AlumniActivator from './components/pages/AlumniActivator.jsx'
import GCProfiler from './components/pages/GCProfiler.jsx'
import AssociateAccelerator from './components/pages/AssociateAccelerator.jsx'
import PitchAutopsy from './components/pages/PitchAutopsy.jsx'

const PAGE_MAP = {
  dashboard: Dashboard,
  churn: ChurnPredictor,
  regulatory: RegulatoryRipple,
  heatmap: RelationshipHeatMap,
  precrime: PreCrimeAcquisition,
  mandates: MandatePreFormation,
  maDark: MADarkSignals,
  supplychain: (props) => <MADarkSignals {...props} />,
  competitive: CompetitiveIntel,
  wallet: WalletShare,
  alumni: AlumniActivator,
  gcprofiler: GCProfiler,
  associate: AssociateAccelerator,
  pitchaudit: PitchAutopsy,
  campaigns: (props) => <PitchAutopsy {...props} />,
}

export default function App() {
  const [activePage, setActivePage] = useState('dashboard')

  const PageComponent = PAGE_MAP[activePage] || Dashboard

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-base)' }}>
      {/* Subtle grid overlay */}
      <div className="grid-bg" style={{ position: 'fixed', inset: 0, opacity: 0.4, pointerEvents: 'none', zIndex: 0 }} />

      {/* Sidebar */}
      <div style={{ position: 'relative', zIndex: 10 }}>
        <Sidebar active={activePage} setActive={setActivePage} />
      </div>

      {/* Main content */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Top border accent */}
        <div style={{ height: 2, background: 'linear-gradient(90deg, var(--accent-gold), transparent 60%)', flexShrink: 0 }} />

        {/* Page content */}
        <div key={activePage} style={{ flex: 1, overflow: 'hidden' }}>
          <PageComponent setPage={setActivePage} />
        </div>
      </div>
    </div>
  )
}
