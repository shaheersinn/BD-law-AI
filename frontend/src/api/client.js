/**
 * api/client.js — Phase 8B: adds scores.topVelocity() call.
 *
 * All other methods unchanged from Phase 8A.
 * topVelocity calls GET /api/v1/scores/top-velocity?limit=N
 * which is the new Phase 8B backend endpoint.
 */

import axios from 'axios'
import useAuthStore from '../stores/auth'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 15_000,
})

// Request interceptor — attach JWT
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor — 401 → clear auth + redirect
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(err)
  },
)

// ── scores ────────────────────────────────────────────────────────────────────
export const scores = {
  get:     (id)             => api.get(`/api/v1/scores/${id}`).then(r => r.data),
  explain: (id)             => api.get(`/api/v1/scores/${id}/explain`).then(r => r.data),
  batch:   (ids, areas)     => api.post('/api/v1/scores/batch', { company_ids: ids, practice_areas: areas }).then(r => r.data),
  topVelocity: (limit = 20) => api.get(`/api/v1/scores/top-velocity?limit=${limit}`).then(r => r.data),
}

// ── companies ─────────────────────────────────────────────────────────────────
export const companies = {
  search: (q, limit = 15) => api.get('/api/v1/companies/search', { params: { q, limit } }).then(r => r.data),
  get:    (id)             => api.get(`/api/v1/companies/${id}`).then(r => r.data),
}

// ── signals ───────────────────────────────────────────────────────────────────
export const signals = {
  list: (companyId, params = {}) => {
    const url = companyId ? `/api/v1/signals/${companyId}` : '/api/v1/signals'
    return api.get(url, { params }).then(r => r.data)
  },
}

// ── trends ────────────────────────────────────────────────────────────────────
export const trends = {
  practiceAreas: () => api.get('/api/v1/trends/practice_areas').then(r => r.data),
}

// ── optimization (Phase 12) ───────────────────────────────────────────────────
export const optimization = {
  usageReport:    ()       => api.get('/api/v1/optimization/usage-report'),
  scoreQuality:   ()       => api.get('/api/v1/optimization/score-quality'),
  perfReport:     (days=7) => api.get(`/api/v1/optimization/perf-report?days=${days}`),
  listOverrides:  ()       => api.get('/api/v1/optimization/signal-overrides'),
  createOverride: (body)   => api.post('/api/v1/optimization/signal-override', body),
  deleteOverride: (id)     => api.delete(`/api/v1/optimization/signal-override/${id}`),
}

// Attach all endpoint groups to the default export for convenience
api.scores       = scores
api.companies    = companies
api.signals      = signals
api.trends       = trends
api.optimization = optimization

export default api
