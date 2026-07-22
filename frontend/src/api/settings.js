import { apiFetch, getCurrentBusinessId } from './client'

export const getSettings = () =>
  apiFetch(`/settings?business_id=${encodeURIComponent(getCurrentBusinessId())}`)

export const updateSettings = (data) =>
  apiFetch(`/settings?business_id=${encodeURIComponent(getCurrentBusinessId())}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })