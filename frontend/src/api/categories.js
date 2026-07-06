import { apiFetch, USER_ID } from './client'

export const getCategories = () =>
  apiFetch(`/categories?user_id=${USER_ID}`)

export const createCategory = (data) =>
  apiFetch('/categories', {
    method: 'POST',
    body: JSON.stringify({ ...data, user_id: USER_ID }),
  })

export const updateCategory = (id, data) =>
  apiFetch(`/categories/${id}?user_id=${USER_ID}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteCategory = (id) =>
  apiFetch(`/categories/${id}?user_id=${USER_ID}`, {
    method: 'DELETE',
  })