import { apiFetch, USER_ID } from './client'

export const getProducts = () =>
  apiFetch(`/products?user_id=${USER_ID}`)

export const createProduct = (data) =>
  apiFetch('/products', {
    method: 'POST',
    body: JSON.stringify({ ...data, user_id: USER_ID }),
  })

export const updateProduct = (id, data) =>
  apiFetch(`/products/${id}?user_id=${USER_ID}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteProduct = (id) =>
  apiFetch(`/products/${id}?user_id=${USER_ID}`, {
    method: 'DELETE',
  })

export const toggleAvailability = (id, isAvailable) =>
  apiFetch(`/products/${id}?user_id=${USER_ID}`, {
    method: 'PUT',
    body: JSON.stringify({ is_available: isAvailable }),
  })

export async function uploadProductImage(productId, file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(
    `/api/products/${productId}/image?user_id=${USER_ID}`,
    { method: 'POST', body: formData }
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}