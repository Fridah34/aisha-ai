import { apiFetch } from './client'

// Returns order groups (one entry per checkout) for the authenticated
// business owner, newest first. Legacy rows with no order_group_id are
// returned as single-item groups by the backend (see crud.py).
export const getOrders = () =>
  apiFetch('/orders')

// Updates ONE line item's status — never a whole checkout group. This
// matches the per-item-status decision: one order_group_id can have a
// shipped item and a cancelled item at the same time.
export const updateOrderStatus = (orderId, status) =>
  apiFetch(`/orders/${orderId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })