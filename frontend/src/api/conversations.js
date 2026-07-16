import { apiFetch, getCurrentBusinessId } from './client'

function businessQuery() {
  return `business_id=${encodeURIComponent(getCurrentBusinessId())}`
}

export const getInbox = () =>
   apiFetch(`/conversations?${businessQuery()}`)
export const getThread = (customerId) =>
   apiFetch(`/conversations/${customerId}?${businessQuery()}`)
export const takeOver = (customerId)   =>
  apiFetch(`/conversations/${customerId}/takeover?${businessQuery()}`, { method: 'PATCH' })
export const resolve = (customerId)   => apiFetch(`/conversations/${customerId}/resolve?${businessQuery()}`, { method: 'PATCH' })
export const sendReply   = (customerId, message) =>
  apiFetch(`/conversations/${customerId}/reply?${businessQuery()}`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })