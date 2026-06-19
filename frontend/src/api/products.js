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