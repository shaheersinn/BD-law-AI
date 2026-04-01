/**
 * App.jsx — ORACLE (Digital Atelier design system).
 *
 * - Imports design-system.css (CSS variables, Newsreader/Manrope, surface hierarchy)
 * - LoginPage has NO AppShell (full-screen split layout)
 * - LandingPage is public at / (no auth)
 * - All authenticated pages wrap with AppShell internally
 */

import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './styles/design-system.css'

import ErrorBoundary             from './components/ErrorBoundary'
import PrivateRoute              from './components/PrivateRoute'
import LoginPage                 from './pages/LoginPage'
import DashboardPage             from './pages/DashboardPage'
import SearchPage                from './pages/SearchPage'
import CompanyDetailPage         from './pages/CompanyDetailPage'
import ExplainPage               from './pages/ExplainPage'
import SignalsFeedPage           from './pages/SignalsFeedPage'
import ScrapersAdminPage         from './pages/admin/ScrapersAdminPage'
import UsersAdminPage            from './pages/admin/UsersAdminPage'
import FeedbackPage              from './pages/FeedbackPage'
import ClassActionRadar          from './pages/ClassActionRadar'
import LandingPage               from './pages/LandingPage'
import ConstructLexDashboardPage from './pages/ConstructLexDashboardPage'
import ChurnPredictorPage        from './pages/ChurnPredictorPage'
import LiveTriggersPage          from './pages/LiveTriggersPage'
import RegulatoryRipplePage      from './pages/RegulatoryRipplePage'
import MADarkSignalsPage         from './pages/MADarkSignalsPage'
import PreCrimeAcquisitionPage   from './pages/PreCrimeAcquisitionPage'
import MandatePreFormationPage   from './pages/MandatePreFormationPage'
import PitchAutopsyPage          from './pages/PitchAutopsyPage'
import GCProfilerPage            from './pages/GCProfilerPage'
import AssociateAcceleratorPage  from './pages/AssociateAcceleratorPage'
import CompetitiveIntelPage      from './pages/CompetitiveIntelPage'
import WalletSharePage           from './pages/WalletSharePage'
import useAuthStore              from './stores/auth'
import NewModulesPage            from './pages/NewModules'
import GeoPagesWrapper           from './pages/GeoPages'
import ScraperDashboard          from './pages/ScraperDashboard'

function AppRoutes() {
  const { token, loadUser } = useAuthStore()

  useEffect(() => {
    if (token) loadUser()
  }, [token])

  return (
    <Routes>
      {/* Public */}
      <Route path="/login"   element={<LoginPage />} />
      <Route path="/landing" element={<LandingPage />} />

      {/* Authenticated — AppShell is applied inside each page */}
      <Route path="/dashboard" element={
        <PrivateRoute><DashboardPage /></PrivateRoute>
      } />
      <Route path="/search" element={
        <PrivateRoute><SearchPage /></PrivateRoute>
      } />
      <Route path="/companies/:id" element={
        <PrivateRoute><CompanyDetailPage /></PrivateRoute>
      } />
      <Route path="/companies/:id/explain" element={
        <PrivateRoute><ExplainPage /></PrivateRoute>
      } />
      <Route path="/signals" element={
        <PrivateRoute><SignalsFeedPage /></PrivateRoute>
      } />
      <Route path="/class-action-radar" element={
        <PrivateRoute><ClassActionRadar /></PrivateRoute>
      } />

      {/* Stitch pages */}
      <Route path="/constructlex" element={
        <PrivateRoute><ConstructLexDashboardPage /></PrivateRoute>
      } />
      <Route path="/churn-predictor" element={
        <PrivateRoute><ChurnPredictorPage /></PrivateRoute>
      } />
      <Route path="/live-triggers" element={
        <PrivateRoute><LiveTriggersPage /></PrivateRoute>
      } />
      <Route path="/regulatory-ripple" element={
        <PrivateRoute><RegulatoryRipplePage /></PrivateRoute>
      } />
      <Route path="/m-a-dark-signals" element={
        <PrivateRoute><MADarkSignalsPage /></PrivateRoute>
      } />
      <Route path="/precrime" element={
        <PrivateRoute><PreCrimeAcquisitionPage /></PrivateRoute>
      } />
      <Route path="/mandate-formation" element={
        <PrivateRoute><MandatePreFormationPage /></PrivateRoute>
      } />
      <Route path="/pitch-autopsy" element={
        <PrivateRoute><PitchAutopsyPage /></PrivateRoute>
      } />
      <Route path="/gc-profiler" element={
        <PrivateRoute><GCProfilerPage /></PrivateRoute>
      } />
      <Route path="/associate-accelerator" element={
        <PrivateRoute><AssociateAcceleratorPage /></PrivateRoute>
      } />
      <Route path="/competitive-intel" element={
        <PrivateRoute><CompetitiveIntelPage /></PrivateRoute>
      } />
      <Route path="/wallet-share" element={
        <PrivateRoute><WalletSharePage /></PrivateRoute>
      } />

      {/* Partner+ */}
      <Route path="/feedback" element={
        <PrivateRoute><FeedbackPage /></PrivateRoute>
      } />

      {/* New module pages */}
      <Route path="/modules" element={
        <PrivateRoute><NewModulesPage /></PrivateRoute>
      } />
      <Route path="/geo" element={
        <PrivateRoute><GeoPagesWrapper /></PrivateRoute>
      } />
      <Route path="/scraper-dashboard" element={
        <PrivateRoute><ScraperDashboard /></PrivateRoute>
      } />

      {/* Admin only */}
      <Route path="/admin/scrapers" element={
        <PrivateRoute adminOnly><ScrapersAdminPage /></PrivateRoute>
      } />
      <Route path="/admin/users" element={
        <PrivateRoute adminOnly><UsersAdminPage /></PrivateRoute>
      } />
      <Route path="/admin/optimization" element={
        <PrivateRoute adminOnly><OptimizationPage /></PrivateRoute>
      } />

      {/* Default redirects */}
      <Route path="/" element={
        token ? <Navigate to="/dashboard" replace /> : <LandingPage />
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ErrorBoundary>
  )
}
