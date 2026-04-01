/**
 * App.jsx — Stitch-first ORACLE shell.
 *
 * - design-system.css: Digital Atelier tokens (PR #19)
 * - Authenticated routes use AppShell (icon rail + main) inside each page
 * - Legacy paths (/dashboard, /modules, /geo, /scraper-dashboard) redirect to Stitch equivalents
 */

import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './styles/design-system.css'

import ErrorBoundary             from './components/ErrorBoundary'
import PrivateRoute              from './components/PrivateRoute'
import LoginPage                 from './pages/LoginPage'
import SearchPage                from './pages/SearchPage'
import CompanyDetailPage         from './pages/CompanyDetailPage'
import ExplainPage               from './pages/ExplainPage'
import SignalsFeedPage           from './pages/SignalsFeedPage'
import ScrapersAdminPage         from './pages/admin/ScrapersAdminPage'
import UsersAdminPage            from './pages/admin/UsersAdminPage'
import OptimizationPage          from './pages/admin/OptimizationPage'
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

      {/* Legacy → Stitch redirects */}
      <Route path="/dashboard" element={
        <PrivateRoute><Navigate to="/constructlex" replace /></PrivateRoute>
      } />
      <Route path="/modules" element={
        <PrivateRoute><Navigate to="/constructlex" replace /></PrivateRoute>
      } />
      <Route path="/geo" element={
        <PrivateRoute><Navigate to="/m-a-dark-signals" replace /></PrivateRoute>
      } />
      <Route path="/scraper-dashboard" element={
        <PrivateRoute adminOnly><Navigate to="/admin/scrapers" replace /></PrivateRoute>
      } />

      {/* Core data (Stitch shell via AppShell in each page) */}
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

      {/* Stitch command center + modules */}
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

      <Route path="/feedback" element={
        <PrivateRoute><FeedbackPage /></PrivateRoute>
      } />

      {/* Admin */}
      <Route path="/admin/scrapers" element={
        <PrivateRoute adminOnly><ScrapersAdminPage /></PrivateRoute>
      } />
      <Route path="/admin/users" element={
        <PrivateRoute adminOnly><UsersAdminPage /></PrivateRoute>
      } />
      <Route path="/admin/optimization" element={
        <PrivateRoute adminOnly><OptimizationPage /></PrivateRoute>
      } />

      <Route path="/" element={
        token ? <Navigate to="/constructlex" replace /> : <LandingPage />
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
