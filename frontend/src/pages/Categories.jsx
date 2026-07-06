import { useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, Layers, AlertCircle, Package } from 'lucide-react'
import {
  getCategories, createCategory, updateCategory, deleteCategory,
} from '../api/categories'

// ── Constants ──────────────────────────────────────────────────────────────────

const EMPTY_FORM = { name: '', description: '',  is_active: true }

// ── Reusable Toggle component ─────────────────────────────────────────────────
// Duplicated from Products.jsx rather than imported — it's a small, self-
// contained component with no external state. Extracting it into a shared
// components/ file is the more scalable move once a third page needs it;
// with only two consumers so far, duplication is the simpler tradeoff.

function Toggle({ on, onToggle, disabled = false }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      role="switch"
      aria-checked={on}
      className={`relative inline-flex w-11 h-6 rounded-full shrink-0
                  transition-colors duration-200 ease-in-out
                  focus:outline-none focus:ring-2 focus:ring-amber-400
                  focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
                  ${on ? 'bg-emerald-500' : 'bg-slate-300'}`}
    >
      <span
        className={`absolute top-[3px] left-[3px] w-[18px] h-[18px]
                    bg-white rounded-full shadow-sm
                    transition-transform duration-200 ease-in-out
                    ${on ? 'translate-x-[20px]' : 'translate-x-0'}`}
      />
    </button>
  )
}

// ── Add/Edit modal ─────────────────────────────────────────────────────────────
// Modal, not a full-page form like ProductForm — categories have four simple
// fields (name, description, order, active) vs Products' nine-plus-image-
// upload, so a modal keeps the interaction fast without leaving the list.

function CategoryModal({ editingCategory, form, setForm, onSave, onCancel, saving, formError }) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-1">
          {editingCategory ? 'Edit category' : 'Add category'}
        </h3>
        <p className="text-xs text-slate-400 mb-5">
          Customers see these as options when they ask to browse on WhatsApp.
        </p>

        {formError && (
          <div className="flex items-start gap-2 px-4 py-3 rounded-xl
                          bg-red-50 border border-red-100 mb-4">
            <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
            <p className="text-sm text-red-600">{formError}</p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              Category name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Drinks"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                         text-sm text-slate-700 placeholder-slate-400
                         focus:outline-none focus:ring-2 focus:ring-amber-400
                         focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              Description
              <span className="text-slate-400 font-normal ml-1">(optional)</span>
            </label>
            <textarea
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              placeholder="Internal note — customers only see the category name"
              rows={2}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                         text-sm text-slate-700 placeholder-slate-400 resize-none
                         focus:outline-none focus:ring-2 focus:ring-amber-400
                         focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              Display order
            </label>
            <input
              type="number"
              value={form.display_order}
              onChange={e => setForm({ ...form, display_order: e.target.value })}
              min="0"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                         text-sm text-slate-700
                         focus:outline-none focus:ring-2 focus:ring-amber-400
                         focus:border-transparent"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Lower numbers appear first in the WhatsApp category list.
            </p>
          </div>

          <div className="flex items-center justify-between pt-1">
            <div>
              <p className="text-sm font-medium text-slate-700">Active</p>
              <p className="text-xs text-slate-400">
                Inactive categories are hidden from WhatsApp customers.
              </p>
            </div>
            <Toggle
              on={form.is_active}
              onToggle={() => setForm({ ...form, is_active: !form.is_active })}
            />
          </div>
        </div>

        <div className="flex items-center gap-3 mt-6">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200
                       text-sm font-medium text-slate-600
                       hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving}
            className="flex-1 px-4 py-2.5 rounded-xl bg-amber-500 text-white
                       text-sm font-medium hover:bg-amber-600 transition-colors
                       disabled:opacity-50"
          >
            {saving ? 'Saving…' : editingCategory ? 'Save changes' : 'Add category'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Category card ──────────────────────────────────────────────────────────────

function CategoryCard({ category, onEdit, onDelete }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4
                    flex flex-col hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-800 truncate">
            {category.name}
          </h3>
          {category.description && (
            <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
              {category.description}
            </p>
          )}
        </div>
        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full
                          uppercase tracking-wide shrink-0
                          ${category.is_active
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-slate-100 text-slate-400'}`}>
          {category.is_active ? 'Active' : 'Hidden'}
        </span>
      </div>

      <div className="flex items-center gap-1.5 mt-3 text-xs text-slate-400">
        <Package size={12} />
        {category.product_count ?? 0} product{category.product_count === 1 ? '' : 's'}
      </div>

      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <button
          onClick={() => onEdit(category)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                     text-xs font-medium text-slate-500 border border-slate-200
                     hover:bg-amber-50 hover:text-amber-700
                     hover:border-amber-200 transition-colors"
        >
          <Pencil size={11} /> Edit
        </button>
        <button
          onClick={() => onDelete(category)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                     text-xs font-medium text-slate-400 border border-slate-200
                     hover:bg-red-50 hover:text-red-500
                     hover:border-red-200 transition-colors"
        >
          <Trash2 size={11} /> Delete
        </button>
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function Categories() {
  const [categories,     setCategories]     = useState(null)
  const [showModal,      setShowModal]      = useState(false)
  const [editingCategory,setEditingCategory]= useState(null)
  const [form,           setForm]           = useState(EMPTY_FORM)
  const [formError,      setFormError]      = useState(null)
  const [saving,         setSaving]         = useState(false)
  const [deleteTarget,   setDeleteTarget]   = useState(null)
  const [deleting,       setDeleting]       = useState(false)

  function loadCategories() {
    getCategories()
      .then(data => setCategories(Array.isArray(data) ? data : []))
      .catch(() => setCategories([]))
  }

  useEffect(() => { loadCategories() }, [])

  function openCreate() {
    setEditingCategory(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setShowModal(true)
  }

  function openEdit(category) {
    setEditingCategory(category)
    setForm({
      name: category.name,
      description: category.description ?? '',
      display_order: category.display_order,
      is_active: category.is_active,
    })
    setFormError(null)
    setShowModal(true)
  }

  function closeModal() {
    setShowModal(false)
    setEditingCategory(null)
    setForm(EMPTY_FORM)
    setFormError(null)
  }

  async function handleSave() {
    if (!form.name.trim()) {
      setFormError('Category name is required.')
      return
    }

    setSaving(true)
    setFormError(null)

    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      is_active: form.is_active,
      ...(editingCategory ? { display_order: Number(form.display_order) || 0 } : {}),
    }

    try {
      if (editingCategory) {
        await updateCategory(editingCategory.id, payload)
      } else {
        await createCategory(payload)
      }
      loadCategories()
      closeModal()
    } catch (e) {
      setFormError(e.message || 'Failed to save category.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteCategory(deleteTarget.id)
      setDeleteTarget(null)
      loadCategories()
    } catch (e) {
      console.error('Delete failed', e)
    } finally {
      setDeleting(false)
    }
  }

  const totalCount = (categories ?? []).length

  return (
    <div className="p-6 max-w-6xl">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center
                      sm:justify-between gap-4 mb-5">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Categories</h2>
          <p className="text-sm text-slate-400 mt-1">
            {categories === null ? 'Loading…' : `${totalCount} categories`}
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center justify-center gap-2 px-4 py-2.5
                     rounded-xl bg-amber-500 text-white text-sm font-medium
                     hover:bg-amber-600 transition-colors shrink-0"
        >
          <Plus size={16} />
          Add category
        </button>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 mb-5 px-4 py-3 rounded-xl
                      bg-amber-50 border border-amber-200">
        <Layers size={15} className="text-amber-600 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-800 leading-relaxed">
          When a customer asks to browse on WhatsApp, AISHA shows these
          categories as a numbered list. Only <strong>Active</strong> categories
          appear, in the display order you set below.
        </p>
      </div>

      {/* Cards grid */}
      {categories === null ? (
        <div className="flex items-center justify-center h-40">
          <p className="text-sm text-slate-400">Loading categories…</p>
        </div>
      ) : categories.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Layers size={36} className="text-slate-300" />
          <p className="text-sm text-slate-400">
            No categories yet — add your first one
          </p>
          <button
            onClick={openCreate}
            className="text-sm text-amber-600 font-medium hover:underline"
          >
            Add a category
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {categories.map(c => (
            <CategoryCard
              key={c.id}
              category={c}
              onEdit={openEdit}
              onDelete={setDeleteTarget}
            />
          ))}
        </div>
      )}

      {/* Add/Edit modal */}
      {showModal && (
        <CategoryModal
          editingCategory={editingCategory}
          form={form}
          setForm={setForm}
          onSave={handleSave}
          onCancel={closeModal}
          saving={saving}
          formError={formError}
        />
      )}

      {/* Delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center
                        justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-sm shadow-xl p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-red-50 flex items-center
                              justify-center shrink-0">
                <Trash2 size={18} className="text-red-500" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-800">
                  Delete category?
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  This cannot be undone.
                </p>
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-5">
              <strong>{deleteTarget.name}</strong> will be removed. Products in
              this category are not deleted — they simply become uncategorized.
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200
                           text-sm font-medium text-slate-600
                           hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 px-4 py-2.5 rounded-xl bg-red-500 text-white
                           text-sm font-medium hover:bg-red-600 transition-colors
                           disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}