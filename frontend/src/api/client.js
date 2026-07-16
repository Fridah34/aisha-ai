/**
 * Base API client.
 * All requests go through /api which Vite proxies to FastAPI.
 *
 * API helpers read the active business UUID from the authenticated user
 * persisted by useAuth after login or registration.
 */

const BASE = '/api'

export function getCurrentBusinessId() {
  const storedUser = localStorage.getItem('user')

  if (!storedUser) {
    throw new Error('Your session has expired. Please sign in again.')
  }

  try {
    const user = JSON.parse(storedUser)
    if (typeof user?.id === 'string' && user.id) return user.id
  } catch {
    // The session error below gives the user an actionable recovery path.
  }

  throw new Error('Your account is missing a valid business ID. Please sign in again.')
}

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