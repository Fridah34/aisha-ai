import { apiFetch, USER_ID } from './client'

export const getInbox = () =>
  apiFetch(`/conversations?user_id=${USER_ID}`)

export const getThread = (customerId) =>
  apiFetch(`/conversations/${customerId}?user_id=${USER_ID}`)