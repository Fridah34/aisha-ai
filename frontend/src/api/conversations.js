import { apiFetch, USER_ID } from './client'

export const getInbox = () =>
   apiFetch(`/conversations?user_id=${USER_ID}`)
export const getThread = (customerId) =>
   apiFetch(`/conversations/${customerId}?user_id=${USER_ID}`)
export const takeOver = (customerId)   =>
  apiFetch(`/conversations/${customerId}/takeover?user_id=${USER_ID}`, { method: 'PATCH' })
export const resolve = (customerId)   => apiFetch(`/conversations/${customerId}/resolve?user_id=${USER_ID}`, { method: 'PATCH' })
export const sendReply   = (customerId, message) =>
  apiFetch(`/conversations/${customerId}/reply?user_id=${USER_ID}`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })