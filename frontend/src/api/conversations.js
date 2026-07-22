import { apiFetch } from './client'

export const getInbox = () =>
   apiFetch('/conversations')
export const getThread = (customerId) =>
   apiFetch(`/conversations/${customerId}`)
export const takeOver = (customerId)   =>
  apiFetch(`/conversations/${customerId}/takeover`, { method: 'PATCH' })
export const resolve = (customerId)   => apiFetch(`/conversations/${customerId}/resolve`, { method: 'PATCH' })
export const sendReply   = (customerId, message) =>
  apiFetch(`/conversations/${customerId}/reply`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })