/**
 * Base API client.
 * All requests go through /api which Vite proxies to FastAPI.
 *
 * AUTH NOTE: user_id is hardcoded to 1 here for now.
 * When Eve's JWT auth is ready, replace USER_ID with the
 * decoded user id from the JWT token stored in context.
 */

const BASE = '/api'

// AUTH NOTE: Replace with real user id from JWT when auth is ready
export const USER_ID = 1

export async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${res.status}`)
  }

  // 204 No Content — no body to parse
  if (res.status === 204) return null

  return res.json()
}