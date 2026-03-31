/**
 * stores/auth.js — Zustand auth store.
 *
 * State:
 *   token  — JWT access token (persisted to sessionStorage)
 *   user   — { id, email, role, name }
 *
 * Actions:
 *   login(email, password)  — call API, store token + user
 *   logout()                — clear token, redirect to /login
 *   loadFromStorage()       — hydrate from sessionStorage on app mount
 */

import { create } from 'zustand'
import { authApi, auth as tokenStorage } from '../api/client'

const useAuthStore = create((set, get) => ({
  token: tokenStorage.getToken() || null,
  user:  null,
  error: null,

  login: async (email, password) => {
    set({ error: null })
    try {
      const data = await authApi.login(email, password)
      tokenStorage.setToken(data.access_token)
      set({ token: data.access_token, user: data.user || null, error: null })
      return true
    } catch (err) {
      set({ error: err.message || 'Login failed' })
      return false
    }
  },

  logout: async () => {
    try {
      await authApi.logout().catch(() => {})
    } finally {
      tokenStorage.clearToken()
      sessionStorage.removeItem('bdforlaw_refresh')
      set({ token: null, user: null, error: null })
      window.location.href = '/login'
    }
  },

  loadUser: async () => {
    if (!get().token) return
    try {
      const user = await authApi.me()
      set({ user })
    } catch (_) {
      tokenStorage.clearToken()
      set({ token: null, user: null })
    }
  },

  clearError: () => set({ error: null }),
}))

export default useAuthStore
