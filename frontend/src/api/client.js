/**
 * api/client.js — Phase 10: adds 5xx retry interceptor.
 *
 * Changes from Phase 8B:
 * - Response interceptor retries 5xx errors up to 3 times with linear
 *   backoff: 500ms → 1000ms → 1500ms.
 * - 4xx errors are never retried (client errors are final).
 * - 401 still clears auth + redirects immediately (no retry).
 */

import axios from 'axios'
import useAuthStore from '../stores/auth'

const MAX_RETRIES = 3
const RETRY_DELAY_MS = 500  // base delay; multiplied by attempt number

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 15_000,
})

// Token helpers used by auth store and interceptors.
export const auth = {
  getToken: () => sessionStorage.getItem('bdforlaw_token'),
  setToken: (token) => sessionStorage.setItem('bdforlaw_token', token),
  clearToken: () => sessionStorage.removeItem('bdforlaw_token'),
}

// Request interceptor — attach JWT
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor — 401 → logout; 5xx → retry with backoff
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const config = err.config

    // 401: clear auth immediately, no retry
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      return Promise.reject(err)
    }

    // 5xx: retry up to MAX_RETRIES times
    const status = err.response?.status
    const isServerError = status >= 500 && status <= 599
    const isNetworkError = !err.response && err.code !== 'ECONNABORTED'

    if ((isServerError || isNetworkError) && config && !config.__retryCount) {
      config.__retryCount = 0
    }

    if (
      (isServerError || isNetworkError) &&
      config &&
      config.__retryCount < MAX_RETRIES
    ) {
      config.__retryCount += 1
      const delay = RETRY_DELAY_MS * config.__retryCount  // 500, 1000, 1500
      await new Promise((resolve) => setTimeout(resolve, delay))
      return api(config)
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

// ── feedback ──────────────────────────────────────────────────────────────────
export const feedback = {
  confirmMandate: (body)    => api.post('/api/v1/feedback/mandate', body).then(r => r.data),
  accuracy:       (days=90) => api.get('/api/v1/feedback/accuracy', { params: { days } }).then(r => r.data),
  drift:          ()        => api.get('/api/v1/feedback/drift').then(r => r.data),
  confirmations:  (params)  => api.get('/api/v1/feedback/confirmations', { params }).then(r => r.data),
}

// ── class actions ─────────────────────────────────────────────────────────────
export const classActions = {
  risks:      (limit = 20)              => api.get('/api/class-actions/risks', { params: { limit } }).then(r => r.data),
  riskDetail: (companyId)               => api.get(`/api/class-actions/risks/${companyId}`).then(r => r.data),
  cases:      (limit = 200)             => api.get('/api/class-actions/cases', { params: { limit } }).then(r => r.data),
  caseDetail: (id)                      => api.get(`/api/class-actions/cases/${id}`).then(r => r.data),
  match:      (companyId, topN = 5)     => api.get(`/api/class-actions/match/${companyId}`, { params: { top_n: topN } }).then(r => r.data),
  customMatch:(payload)                 => api.post('/api/class-actions/match', payload).then(r => r.data),
  dashboard:  ()                        => api.get('/api/class-actions/dashboard').then(r => r.data),
}

// ── auth ───────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) => api.post('/api/auth/login', { email, password }).then(r => r.data),
  logout: () => api.post('/api/auth/logout').then(r => r.data),
  me: () => api.get('/api/auth/me').then(r => r.data),
  refresh: (refreshToken) =>
    api.post('/api/auth/refresh', { refresh_token: refreshToken }).then(r => r.data),
}

// ── scrapers ─────────────────────────────────────────────────────────────────
// NOTE: scrapers router has NO /v1/ prefix — /api/scrapers/*, not /api/v1/scrapers/*
export const scrapers = {
  health:   (limit = 200) => api.get('/api/scrapers/health',  { params: { limit } }).then(r => r.data),
  summary:  ()            => api.get('/api/scrapers/summary').then(r => r.data),
  run:      (sourceId)    => api.post(`/api/scrapers/${sourceId}/run`).then(r => r.data),
  registry: ()            => api.get('/api/scrapers/registry').then(r => r.data),
}

// ── geo signals (filtered via signals endpoint) ───────────────────────────────
export const geoSignals = {
  jets:    (limit = 20) => api.get('/api/v1/signals', { params: { signal_type: 'geo_flight_corporate_jet', limit } }).then(r => r.data),
  permits: (limit = 20) => api.get('/api/v1/signals', { params: { signal_type: 'geo_municipal_permit_issued', limit } }).then(r => r.data),
  all:     (limit = 50) => api.get('/api/v1/signals', { params: { category: 'geo', limit } }).then(r => r.data),
}

// ── clients ───────────────────────────────────────────────────────────────────
// NOTE: clients router has NO /v1/ prefix — /api/clients/*, not /api/v1/clients/*
export const clients = {
  list:        (params = {}) => api.get('/api/clients',              { params }).then(r => r.data),
  churnScores: ()            => api.get('/api/clients/churn-scores').then(r => r.data),
  get:         (id)          => api.get(`/api/clients/${id}`).then(r => r.data),
  walletShare: ()            => api.get('/api/clients/wallet-share').then(r => r.data),
}

// ── bd ────────────────────────────────────────────────────────────────────────
export const bd = {
  partners:          ()          => api.get('/api/v1/bd/partners').then(r => r.data),
  partnerCoaching:   (partnerId) => api.get(`/api/v1/bd/partner-coaching/${partnerId}`).then(r => r.data),
  pitchHistory:      ()          => api.get('/api/v1/bd/pitch-history').then(r => r.data),
  associateActivity: ()          => api.get('/api/v1/bd/associate-activity').then(r => r.data),
  content:           ()          => api.get('/api/v1/bd/content').then(r => r.data),
  submitInquiry:     (body)      => api.post('/api/v1/bd/inquiries', body).then(r => r.data),
}

// ── firms ─────────────────────────────────────────────────────────────────────
export const firms = {
  competitive: () => api.get('/api/v1/firms/competitive').then(r => r.data),
}

export default api
