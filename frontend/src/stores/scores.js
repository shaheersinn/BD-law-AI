/**
 * stores/scores.js — Zustand score store.
 *
 * Caches fetched scores in memory so navigating between company pages
 * doesn't re-fetch unless the data is stale (> 6 hours old).
 */

import { create } from 'zustand'
import { scores as scoresApi } from '../api/client'

const STALE_MS = 6 * 60 * 60 * 1000 // 6 hours

const useScoreStore = create((set, get) => ({
  // Map<companyId: number, { data, fetchedAt: Date }>
  cache: new Map(),
  loading: new Set(),
  errors:  new Map(),

  fetchScore: async (companyId) => {
    const id = Number(companyId)
    const cached = get().cache.get(id)
    if (cached && Date.now() - cached.fetchedAt < STALE_MS) return cached.data

    if (get().loading.has(id)) return null

    set((s) => {
      const loading = new Set(s.loading)
      loading.add(id)
      return { loading }
    })

    try {
      const data = await scoresApi.get(id)
      set((s) => {
        const cache = new Map(s.cache)
        cache.set(id, { data, fetchedAt: Date.now() })
        const loading = new Set(s.loading)
        loading.delete(id)
        const errors = new Map(s.errors)
        errors.delete(id)
        return { cache, loading, errors }
      })
      return data
    } catch (err) {
      set((s) => {
        const loading = new Set(s.loading)
        loading.delete(id)
        const errors = new Map(s.errors)
        errors.set(id, err.message || 'Failed to fetch score')
        return { loading, errors }
      })
      return null
    }
  },

  fetchBatch: async (companyIds) => {
    try {
      const results = await scoresApi.batch(companyIds)
      set((s) => {
        const cache = new Map(s.cache)
        companyIds.forEach((id, i) => {
          if (results[i]) {
            cache.set(Number(id), { data: results[i], fetchedAt: Date.now() })
          }
        })
        return { cache }
      })
      return results
    } catch (err) {
      return null
    }
  },

  getScore: (companyId) => {
    const cached = get().cache.get(Number(companyId))
    return cached?.data ?? null
  },

  isLoading: (companyId) => get().loading.has(Number(companyId)),
  getError:  (companyId) => get().errors.get(Number(companyId)) ?? null,
}))

export default useScoreStore
