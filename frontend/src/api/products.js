import { apiFetch, formatApiError } from './client'

export const getProducts = () =>
  apiFetch('/products')

export const createProduct = (data) =>
  apiFetch('/products', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateProduct = (id, data) =>
  apiFetch(`/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteProduct = (id) =>
  apiFetch(`/products/${id}`, {
    method: 'DELETE',
  })

export const toggleAvailability = (id, isAvailable) =>
  apiFetch(`/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ is_available: isAvailable }),
  })

export async function uploadProductImage(productId, file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(
    `/api/products/${productId}/image`,
    { method: 'POST', body: formData }
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(formatApiError(err))
  }
  return res.json()
}