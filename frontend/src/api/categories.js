import { apiFetch} from './client'

export const getCategories = () =>
  apiFetch('/categories')

export const createCategory = (data) =>
  apiFetch('/categories', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateCategory = (id, data) =>
  apiFetch(`/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteCategory = (id) =>
  apiFetch(`/categories/${id}`, {
    method: 'DELETE',
  })