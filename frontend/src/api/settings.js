import { apiFetch, USER_ID } from './client'

export const getSettings = () =>
  apiFetch(`/settings?user_id=${USER_ID}`)

export const updateSettings = (data) =>
  apiFetch(`/settings?user_id=${USER_ID}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })