/**
 * App.jsx — ORACLE Phase 8A functional frontend.
 *
 * Routes:
 *   /login                  — JWT login form (public)
 *   /dashboard              — Score dashboard + trend charts (auth)
 *   /search                 — Fuzzy company search (auth)
 *   /companies/:id          — Company detail + score matrix + signals (auth)
 *   /companies/:id/explain  — SHAP explanations (auth)
 *   /signals                — Global signal feed (auth)
 *   /admin/scrapers         — Scraper health (admin only)
 *   /admin/users            — User management (admin only)
 *
 * Design system (Phase 8B — ConstructLex Pro):
 *   Background:  #F8F7F4 (warm off-white)
 *   Accent:      teal-emerald #0C9182 → #059669 gradient
 *   Display/nums: Cormorant Garamond
 *   Body:         Plus Jakarta Sans
 *   Data/mono:    JetBrains Mono
 */

import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import PrivateRoute from './components/PrivateRoute'
import LoginPage          from './pages/LoginPage'
import DashboardPage      from './pages/DashboardPage'
import SearchPage         from './pages/SearchPage'
import CompanyDetailPage  from './pages/CompanyDetailPage'
import ExplainPage        from './pages/ExplainPage'
import SignalsFeedPage    from './pages/SignalsFeedPage'
import ScrapersAdminPage  from './pages/admin/ScrapersAdminPage'
import UsersAdminPage     from './pages/admin/UsersAdminPage'
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

      {/* Authenticated */}
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

      {/* Admin only */}
      <Route path="/admin/scrapers" element={
        <PrivateRoute adminOnly><ScrapersAdminPage /></PrivateRoute>
      } />
      <Route path="/admin/users" element={
        <PrivateRoute adminOnly><UsersAdminPage /></PrivateRoute>
      } />

      {/* Default redirects */}
      <Route path="/" element={
        token ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
      } />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
