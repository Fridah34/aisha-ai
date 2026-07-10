/**
 * Base API client.
 * All requests go through /api which Vite proxies to FastAPI.
 *
 * AUTH NOTE: user_id is hardcoded to 1 here for now.
 * When Eve's JWT auth is ready, replace USER_ID with the
 * decoded user id from the JWT token stored in context.
 */

const BASE = '/api'
const WS_BASE = 'ws://localhost:5173' 

// AUTH NOTE: Replace with real user id from JWT when auth is ready


export async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials : 'include',
    ...options,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }))
    let message = `HTTP ${ res.status}`
    if (typeof error.detail === 'string') {
      message = error.detail
    } else if (Array.isArray(error.detail)) {
      // FastAPI validation errors: [{ loc, msg, type }, ...]
      message = error.detail.map(e => e.msg).join('; ')
    }
    throw new Error(message)
  }

  // 204 No Content — no body to parse
  if (res.status === 204) return null

  return res.json()
}

 //WebSocket helper
export function getWebSocketUrl() {
  return `${WS_BASE}/ws/conversations`
}