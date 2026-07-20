import { apiFetch, getCurrentBusinessId } from './client'

function businessQuery() {
  return `business_id=${encodeURIComponent(getCurrentBusinessId())}`
}

export const getProducts = () =>
  apiFetch(`/products?${businessQuery()}`)

export const createProduct = (data) =>
  apiFetch('/products', {
    method: 'POST',
    body: JSON.stringify({ ...data, business_id: getCurrentBusinessId() }),
  })

export const updateProduct = (id, data) =>
  apiFetch(`/products/${id}?${businessQuery()}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteProduct = (id) =>
  apiFetch(`/products/${id}?${businessQuery()}`, {
    method: 'DELETE',
  })

export const toggleAvailability = (id, isAvailable) =>
  apiFetch(`/products/${id}?${businessQuery()}`, {
    method: 'PUT',
    body: JSON.stringify({ is_available: isAvailable }),
  })

export async function uploadProductImage(productId, file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(
    `/api/products/${productId}/image?${businessQuery()}`,
    { method: 'POST', body: formData }
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}