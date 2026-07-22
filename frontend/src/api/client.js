/**
 * Base API client.
 * All requests go through /api which Vite proxies to FastAPI.
 *
 * API helpers read the active business UUID from the authenticated user
 * persisted by useAuth after login or registration.
 */

const BASE = '/api'

// UUID v4 regex pattern
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function getCurrentBusinessId() {
  const businessId = localStorage.getItem('business_id')
  const storedUser = localStorage.getItem('user')

  if (!businessId && storedUser) {
    const parsedUser = JSON.parse(storedUser)
    if (parsedUser?.id && UUID_REGEX.test(parsedUser.id)) {
      localStorage.setItem('business_id', parsedUser.id)
      return parsedUser.id
    }
  }

  // Validate UUID format
  if (businessId && UUID_REGEX.test(businessId)) {
    return businessId
  }

  // Clear stale keys on invalid/missing business_id
  localStorage.removeItem('user_id')
  localStorage.removeItem('business_id')
  localStorage.removeItem('user')

  // Redirect to login if not already there
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }

  throw new Error('Your session has expired. Please sign in again.')
}

export function formatApiError(error) {
  const detail = error?.detail
  if (Array.isArray(detail)) {
    return detail
      .map(e => {
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : null
        return field ? `${field}: ${e.msg}` : e.msg
      })
      .join('; ')
  }
  if (typeof detail === 'string') return detail
  return 'Something went wrong. Please try again.'
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

export function getWebSocketUrl() {
  const apiBase =
    import.meta.env.VITE_API_URL || "http://localhost:8000";

  return apiBase.replace(/^http/, "ws") + "/ws";
}