/**
 * frontend/src/api/client.js
 *
 * Centralised API client. All fetch calls go through here.
 * In dev the Vite proxy forwards /api/* to http://localhost:8000.
 * In production the nginx proxy does the same.
 *
 * Authentication: JWT stored in sessionStorage.
 * Every request auto-attaches Authorization header if a token exists.
 */

const BASE = "/api";

// ── Auth token management ──────────────────────────────────────────────────────

const tokenKey = "bdforlaw_token";

export const auth = {
  getToken:   ()    => sessionStorage.getItem(tokenKey),
  setToken:   (t)   => sessionStorage.setItem(tokenKey, t),
  clearToken: ()    => sessionStorage.removeItem(tokenKey),
  isLoggedIn: ()    => !!sessionStorage.getItem(tokenKey),
};

// ── Error class ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(status, message, requestId) {
    super(message);
    this.status    = status;
    this.requestId = requestId;
    this.name      = "ApiError";
  }
}

// ── Core fetch ─────────────────────────────────────────────────────────────────

async function request(method, path, body = null, options = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = auth.getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const opts = { method, headers };
  if (body !== null) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE}${path}`, opts);

  // Handle 401 — clear stale token
  if (res.status === 401) {
    auth.clearToken();
    if (!options.noRedirect) {
      window.location.href = "/?session_expired=1";
    }
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    let requestId = res.headers.get("x-request-id") || "";
    try {
      const err = await res.json();
      detail = err.error || err.detail || err.message || detail;
    } catch (_) {}
    throw new ApiError(res.status, detail, requestId);
  }

  // No-content responses
  if (res.status === 204) return null;
  return res.json();
}

const get    = (path)         => request("GET",    path);
const post   = (path, body)   => request("POST",   path, body);
const patch  = (path, body)   => request("PATCH",  path, body);
const del    = (path)         => request("DELETE", path);

// ── SSE streaming helper ──────────────────────────────────────────────────────

export function streamBrief(path, onToken, onDone, onError) {
  const token = auth.getToken();
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  // Use EventSource-compatible fetch streaming
  const controller = new AbortController();

  fetch(`${BASE}${path}`, { headers, signal: controller.signal })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        onError?.(err.error || `HTTP ${res.status}`);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") {
            onDone?.(fullText);
            return;
          }
          try {
            const msg = JSON.parse(data);
            if (msg.delta) {
              fullText += msg.delta;
              onToken?.(msg.delta, fullText);
            }
            if (msg.error) {
              onError?.(msg.error);
              return;
            }
            if (msg.done) {
              onDone?.(msg.full_text || fullText);
              return;
            }
          } catch (_) {}
        }
      }
    })
    .catch((e) => {
      if (e.name !== "AbortError") onError?.(e.message);
    });

  return () => controller.abort(); // returns cancel function
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login:          (email, password) => request("POST", "/auth/login",
                    { email, password }, { noRedirect: true }),
  refresh:        (refreshToken)    => post("/auth/refresh", { refresh_token: refreshToken }),
  logout:         (refreshToken)    => post("/auth/logout",  { refresh_token: refreshToken }),
  me:             ()                => get("/auth/me"),
  changePassword: (body)            => request("PUT", "/auth/me/password", body),
  // admin only:
  createUser:     (body)            => post("/auth/users", body),
  listUsers:      ()                => get("/auth/users"),
};

// ── Clients ────────────────────────────────────────────────────────────────────

export const clients = {
  list:        (params = {}) => get(`/clients/?${new URLSearchParams(params)}`),
  get:         (id)          => get(`/clients/${id}`),
  update:      (id, body)    => patch(`/clients/${id}`, body),
  churnScores: ()            => get("/clients/churn-scores"),
  churnBrief:  (id)          => post(`/clients/${id}/churn-brief`, {}),
  churnStream: (id, onToken, onDone, onError) =>
    streamBrief(`/clients/${id}/churn-brief/stream`, onToken, onDone, onError),
  invalidateBriefCache: (id) => del(`/clients/${id}/churn-brief/cache`),
  addSignal:   (id, body)    => post(`/clients/${id}/signals`, body),
};

// ── Triggers ──────────────────────────────────────────────────────────────────

export const triggers = {
  live:   (params = {}) => get(`/triggers/live?${new URLSearchParams(params)}`),
  stats:  ()            => get("/triggers/stats"),
  get:    (id)          => get(`/triggers/${id}`),
  label:  (id, outcome, notes) => post(`/triggers/${id}/label`, { outcome, notes }),
  brief:  (id)          => post(`/triggers/${id}/brief`, {}),
  stream: (id, onToken, onDone, onError) =>
    streamBrief(`/triggers/${id}/brief/stream`, onToken, onDone, onError),
};

// ── Geospatial ────────────────────────────────────────────────────────────────

export const geo = {
  intensity:      ()   => get("/geo/intensity"),
  geoBrief:       (id) => post(`/geo/intensity/${id}/brief`, {}),
  jets:           (p)  => get(`/geo/jets?${new URLSearchParams(p || {})}`),
  jetBrief:       (id) => post(`/geo/jets/${id}/brief`, {}),
  jetStream:      (id, ...cbs) => streamBrief(`/geo/jets/${id}/brief/stream`, ...cbs),
  footTraffic:    (p)  => get(`/geo/foot-traffic?${new URLSearchParams(p || {})}`),
  footStrategy:   (id) => post(`/geo/foot-traffic/${id}/strategy`, {}),
  footStream:     (id, ...cbs) => streamBrief(`/geo/foot-traffic/${id}/strategy/stream`, ...cbs),
  satellite:      ()   => get("/geo/satellite"),
  satelliteBrief: (id) => post(`/geo/satellite/${id}/brief`, {}),
  satStream:      (id, ...cbs) => streamBrief(`/geo/satellite/${id}/brief/stream`, ...cbs),
  permits:        (p)  => get(`/geo/permits?${new URLSearchParams(p || {})}`),
  permitBrief:    (id) => post(`/geo/permits/${id}/brief`, {}),
  permitStream:   (id, ...cbs) => streamBrief(`/geo/permits/${id}/brief/stream`, ...cbs),
};

// ── Watchlist ─────────────────────────────────────────────────────────────────

export const watchlist = {
  list:      ()     => get("/watchlist"),
  add:       (body) => post("/watchlist", body),
  remove:    (id)   => del(`/watchlist/${id}`),
  search:    (q, limit = 10) => get(`/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  scrape:    (body) => post("/scrape/trigger", body),
};

// ── AI generation ─────────────────────────────────────────────────────────────

export const ai = {
  regulatoryAlert:  (body)    => post("/ai/regulatory-alert", body),
  prospectOutreach: (body)    => post("/ai/prospect-outreach", body),
  prospectStream:   (params, ...cbs) =>
    streamBrief(`/ai/prospect-outreach/stream?${new URLSearchParams(params)}`, ...cbs),
  alumniMessage:    (id)      => post(`/ai/alumni/${id}/message`, {}),
  gcProfile:        (body)    => post("/ai/gc-profile", body),
  mandateBrief:     (body)    => post("/ai/mandate-brief", body),
  mandateStream:    (params, ...cbs) =>
    streamBrief(`/ai/mandate-brief/stream?${new URLSearchParams(params)}`, ...cbs),
  maStrategy:       (body)    => post("/ai/ma-strategy", body),
  pitchDebrief:     (body)    => post("/ai/pitch-debrief", body),
  bdCampaign:       (body)    => post("/ai/bd-campaign", body),
  coachingBrief:    (id)      => post(`/ai/coaching/${id}/brief`, {}),
  ghostDraft:       (body)    => post("/ai/ghost/draft", body),
  ghostStream:      (params, ...cbs) =>
    streamBrief(`/ai/ghost/draft/stream?${new URLSearchParams(params)}`, ...cbs),
  // Generic proxy for direct Claude calls from geo/module pages
  anthropic:        (body)    => post("/ai/anthropic", body),
};

// ── Analytics ─────────────────────────────────────────────────────────────────

export const analytics = {
  modelPerformance: (days = 90)  => get(`/analytics/model-performance?days_back=${days}`),
  signalQuality:    (days = 30)  => get(`/analytics/signal-quality?days_back=${days}`),
  bdPerformance:    (partnerId)  => get(`/analytics/bd-performance${partnerId ? `?partner_id=${partnerId}` : ""}`),
  health:           ()           => get("/analytics/health"),
};

// ── System ────────────────────────────────────────────────────────────────────

export const system = {
  health: () => get("/health"),
  ready:  () => get("/ready"),
};

// ── Phase 7 — ORACLE Scoring API ──────────────────────────────────────────────

export const scores = {
  get:     (companyId)                    => get(`/v1/scores/${companyId}`),
  explain: (companyId)                    => get(`/v1/scores/${companyId}/explain`),
  batch:   (companyIds, practiceAreas)    => post("/v1/scores/batch", {
    company_ids: companyIds,
    ...(practiceAreas ? { practice_areas: practiceAreas } : {}),
  }),
};

export const companies = {
  search: (q, limit = 10) => get(`/v1/companies/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  get:    (companyId)     => get(`/v1/companies/${companyId}`),
};

export const signals = {
  list: (companyId, params = {}) =>
    get(`/v1/signals/${companyId}?${new URLSearchParams(params)}`),
};

export const trends = {
  practiceAreas: () => get("/v1/trends/practice_areas"),
};
