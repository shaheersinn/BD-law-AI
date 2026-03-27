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

import ErrorBoundary      from './components/ErrorBoundary'
import PrivateRoute       from './components/PrivateRoute'
import LoginPage          from './pages/LoginPage'
import DashboardPage      from './pages/DashboardPage'
import SearchPage         from './pages/SearchPage'
import CompanyDetailPage  from './pages/CompanyDetailPage'
import ExplainPage        from './pages/ExplainPage'
import SignalsFeedPage    from './pages/SignalsFeedPage'
import ScrapersAdminPage  from './pages/admin/ScrapersAdminPage'
import UsersAdminPage     from './pages/admin/UsersAdminPage'
import FeedbackPage       from './pages/FeedbackPage'
import LandingPage        from './pages/LandingPage'
import useAuthStore       from './stores/auth'

function AppRoutes() {
  const { token, loadUser } = useAuthStore()

  useEffect(() => {
    if (token) loadUser()
  }, [token])

  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
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

      {/* Partner+ */}
      <Route path="/feedback" element={
        <PrivateRoute><FeedbackPage /></PrivateRoute>
      } />

      {/* Admin only */}
      <Route path="/admin/scrapers" element={
        <PrivateRoute adminOnly><ScrapersAdminPage /></PrivateRoute>
      } />
      <Route path="/admin/users" element={
        <PrivateRoute adminOnly><UsersAdminPage /></PrivateRoute>
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
