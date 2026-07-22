import { apiFetch } from './client'

export const getSettings = () =>
  apiFetch('/settings')

export const updateSettings = (data) =>
  apiFetch('/settings', {
    method: 'PATCH',
    body: JSON.stringify(data),
  })