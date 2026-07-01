import { useEffect, useState, useRef } from 'react'
import {
  Plus, Pencil, Trash2, Search, CheckCircle,
  XCircle, Sparkles, AlertCircle, ImagePlus,
  Package, Tag, Layers, ArrowLeft, ChevronRight
} from 'lucide-react'
import {
  getProducts, createProduct, updateProduct,
  deleteProduct, toggleAvailability, uploadProductImage,
} from '../api/products'
import { getSettings } from '../api/settings'

// ── Constants ──────────────────────────────────────────────────────────────────

const EMPTY_FORM = {
  name: '', description: '', price: '', is_available: true,
  category: '', variant_label: '', variant_options: '',
  unit: '', upsell_text: '',
}

const VARIANT_CONFIG = {
  retail: {
    variantLabel:        'Size / Color',
    variantPlaceholder:  'e.g. S, M, L, XL  or  Red, Blue, Green',
    unitPlaceholder:     'e.g. per piece, per pair',
    categoryPlaceholder: 'e.g. Shoes, Dresses, Accessories',
    upsellPlaceholder:   'e.g. Pair this with our Matching Headwrap (KES 500) for a complete look.',
    descPlaceholder:     'e.g. Hand-stitched ankara fabric, available in sizes S–XL',
    variantLabelHint:    'e.g. Size  or  Color',
    questionHint:        'what sizes / colors do you have',
  },
  services: {
    variantLabel:        'Duration / Options',
    variantPlaceholder:  'e.g. 30min, 60min, 90min',
    unitPlaceholder:     'e.g. per session, per visit',
    categoryPlaceholder: 'e.g. Hair, Nails, Massage',
    upsellPlaceholder:   'e.g. Also suggest our Deep Conditioning Treatment (KES 800) for best results.',
    descPlaceholder:     'e.g. Deep conditioning treatment, includes scalp massage',
    variantLabelHint:    'e.g. Duration',
    questionHint:        'how long does it take',
  },
  general: {
    variantLabel:        'Variant',
    variantPlaceholder:  'e.g. Small, Medium, Large',
    unitPlaceholder:     'e.g. per unit, per kg',
    categoryPlaceholder: 'e.g. Electronics, Hardware',
    upsellPlaceholder:   'e.g. Customers also buy our Protective Case (KES 300) with this.',
    descPlaceholder:     'e.g. Heavy-duty roofing nails, galvanised and rust-resistant',
    variantLabelHint:    'e.g. Variant',
    questionHint:        'what options do you have',
  },
}

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_SIZE_MB   = 2

// ── Reusable Toggle component ─────────────────────────────────────────────────
// Why a separate component: the toggle appears in three places (card, form
// stock section). Extracting it ensures the math is correct in one place only.
//
// Toggle math explained:
//   track  = w-11 = 44px wide, h-6 = 24px tall
//   ball   = 18px wide, 18px tall
//   padding = 3px each side
//   off position: ball at left=3px
//   on  position: ball at left=3px + (44 - 18 - 3 - 3) = 23px → translate-x-[20px]
//   Result: ball stays 3px from each edge, never escapes the track

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

// ── Image upload zone ─────────────────────────────────────────────────────────
// Approach: HTML5 native drag-and-drop events + hidden file input.
// Why not react-dropzone: avoids a dependency, teaches the native API,
// and is sufficient for a single-file image upload use case.
// Alternative: react-dropzone gives multi-file, progress events, and
// better accessibility out of the box — worth adding for production.

function ImageUploadZone({ currentUrl, onFile, disabled }) {
  const [dragging, setDragging] = useState(false)
  const [preview,  setPreview]  = useState(currentUrl || null)
  const [error,    setError]    = useState(null)
  const inputRef = useRef(null)

  // Sync preview when switching between edit targets
  useEffect(() => { setPreview(currentUrl || null) }, [currentUrl])

  function validate(file) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Only JPEG, PNG, or WebP images are allowed.')
      return false
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`Image must be under ${MAX_SIZE_MB}MB.`)
      return false
    }
    return true
  }

  function handleFile(file) {
    setError(null)
    if (!validate(file)) return
    // Show blob preview instantly — no upload yet
    // The actual upload happens in handleSave() after the product is created
    setPreview(URL.createObjectURL(file))
    onFile(file)
  }

  return (
    <div>
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          const file = e.dataTransfer.files[0]
          if (file) handleFile(file)
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`relative w-full h-52 rounded-2xl border-2 border-dashed
                    flex flex-col items-center justify-center
                    transition-colors overflow-hidden
                    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                    ${dragging
                      ? 'border-amber-400 bg-amber-50'
                      : 'border-slate-200 hover:border-amber-300 hover:bg-slate-50'}`}
      >
        {preview ? (
          <>
            <img
              src={preview.startsWith('blob:')
                ? preview
                : `http://127.0.0.1:8000${preview}`}
              alt="Product preview"
              className="w-full h-full object-cover"
            />
            {!disabled && (
              <div className="absolute inset-0 bg-black/40 opacity-0
                              hover:opacity-100 transition-opacity
                              flex items-center justify-center">
                <p className="text-white text-sm font-medium">
                  Click to change image
                </p>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center gap-3 px-6 text-center
                          pointer-events-none">
            <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center
                            justify-center">
              <ImagePlus size={22} className="text-slate-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-600">
                {dragging ? 'Drop image here' : 'Drag & drop your product image'}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                or{' '}
                <span className="text-amber-600 font-medium">browse files</span>
              </p>
              <p className="text-xs text-slate-300 mt-2">
                JPEG · PNG · WebP · max {MAX_SIZE_MB}MB
              </p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-500 mt-1.5 flex items-center gap-1">
          <AlertCircle size={11} /> {error}
        </p>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_TYPES.join(',')}
        onChange={e => { const f = e.target.files[0]; if (f) handleFile(f) }}
        className="hidden"
        disabled={disabled}
      />
    </div>
  )
}

// ── Product card ──────────────────────────────────────────────────────────────

function ProductCard({ product, onEdit, onDelete, onToggle, toggling }) {
  const isToggling = toggling === product.id

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden
                    flex flex-col hover:shadow-md transition-shadow">

      {/* Image area */}
      <div className="relative h-52 bg-slate-50 shrink-0">
        {product.image_url ? (
          <img
            src={`http://127.0.0.1:8000${product.image_url}`}
            alt={product.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center
                          justify-center gap-2">
            <Package size={28} className="text-slate-200" />
            <p className="text-xs text-slate-300">No image</p>
          </div>
        )}

        {/* Stock badge */}
        <span className={`absolute top-3 right-3 text-[10px] font-bold
                          px-2.5 py-1 rounded-full uppercase tracking-wide
                          ${product.is_available
                            ? 'bg-emerald-500 text-white'
                            : 'bg-red-500 text-white'}`}>
          {product.is_available ? 'In stock' : 'Out of stock'}
        </span>

        {/* Category badge */}
        {product.category && (
          <span className="absolute top-3 left-3 bg-black/60 backdrop-blur-sm
                           text-white text-[10px] font-medium px-2.5 py-1
                           rounded-full uppercase tracking-wide">
            {product.category}
          </span>
        )}
      </div>

      {/* Card body */}
      <div className="p-4 flex flex-col flex-1">
        <h3 className="text-sm font-semibold text-slate-800 leading-snug">
          {product.name}
        </h3>

        {product.description && (
          <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
            {product.description}
          </p>
        )}

        {/* Variant chips */}
        {product.variant_label && product.variant_options && (
          <div className="mt-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
              {product.variant_label}
            </p>
            <div className="flex flex-wrap gap-1">
              {product.variant_options.split(',').slice(0, 5).map(v => (
                <span key={v.trim()}
                  className="text-[10px] bg-purple-50 text-purple-700
                             px-2 py-0.5 rounded-full font-medium">
                  {v.trim()}
                </span>
              ))}
              {product.variant_options.split(',').length > 5 && (
                <span className="text-[10px] text-slate-400">
                  +{product.variant_options.split(',').length - 5} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Upsell indicator */}
        {product.upsell_text && (
          <div className="flex items-start gap-1.5 mt-2.5 px-2.5 py-2
                          bg-amber-50 rounded-xl border border-amber-100">
            <Sparkles size={10} className="text-amber-500 shrink-0 mt-0.5" />
            <p className="text-[10px] text-amber-700 line-clamp-2 leading-relaxed">
              {product.upsell_text}
            </p>
          </div>
        )}

        {/* Price */}
        <div className="mt-auto pt-3">
          <p className="text-lg font-bold text-slate-800">
            KES {Number(product.price).toLocaleString()}
            {product.unit && (
              <span className="text-xs font-normal text-slate-400 ml-1">
                / {product.unit}
              </span>
            )}
          </p>
        </div>

        {/* Footer: toggle + actions */}
        <div className="flex items-center justify-between mt-3 pt-3
                        border-t border-slate-100">
          <div className="flex items-center gap-2">
            <Toggle
              on={product.is_available}
              onToggle={() => onToggle(product)}
              disabled={isToggling}
            />
            <span className={`text-xs font-medium
                              ${product.is_available
                                ? 'text-emerald-600'
                                : 'text-slate-400'}`}>
              {isToggling ? '…' : product.is_available ? 'Active' : 'Inactive'}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => onEdit(product)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                         text-xs font-medium text-slate-500 border border-slate-200
                         hover:bg-amber-50 hover:text-amber-700
                         hover:border-amber-200 transition-colors"
            >
              <Pencil size={11} /> Edit
            </button>
            <button
              onClick={() => onDelete(product)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                         text-xs font-medium text-slate-400 border border-slate-200
                         hover:bg-red-50 hover:text-red-500
                         hover:border-red-200 transition-colors"
            >
              <Trash2 size={11} /> Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Product form (full-page view) ─────────────────────────────────────────────
// Why extracted as a separate function component and not inlined in Products():
// - Keeps Products() readable — it only handles state and data logic
// - ProductForm has its own clean prop interface
// - Prevents entire Products() state from re-rendering on every keystroke
//   (React only re-renders the subtree that received the prop change)
//
// Why two-column layout:
// Image + stock + upsell on the left (visual/AI config),
// basic info + variants on the right (text data).
// This mirrors how a business owner thinks: "what does it look like
// and how do I price it" vs "what are the details AISHA needs".

function ProductForm({
  editingProduct, form, setForm, onSave, onCancel,
  saving, uploadingImage, formError, businessType,
  onFile, pendingImage,
}) {
  const config = VARIANT_CONFIG[businessType] ?? VARIANT_CONFIG.retail

  return (
    <div className="max-w-6xl px-6 py-6 min-h-full">

      {/* Breadcrumb navigation */}
      <div className="flex items-center gap-2 text-sm text-slate-400 mb-5">
        <button
          onClick={onCancel}
          className="flex items-center gap-1.5 hover:text-amber-600
                     transition-colors font-medium"
        >
          <ArrowLeft size={14} />
          Products
        </button>
        <ChevronRight size={14} className="text-slate-300" />
        <span className="text-slate-600 font-medium">
          {editingProduct ? `Edit — ${editingProduct.name}` : 'Add new product'}
        </span>
      </div>

      {/* Page heading */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-slate-800">
          {editingProduct ? 'Edit product' : 'Add new product'}
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          {editingProduct
            ? 'Changes reflect in AISHA immediately after saving.'
            : 'Only product name and price are required. All other fields improve AISHA\'s answers.'}
        </p>
      </div>

      {/* Error banner */}
      {formError && (
        <div className="flex items-start gap-2 px-4 py-3 rounded-xl
                        bg-red-50 border border-red-100 mb-6">
          <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-600">{formError}</p>
        </div>
      )}

      {/* Two-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-4">

        {/* ── LEFT: Visual + AI config ── */}
        <div className="space-y-4">

          {/* Image upload */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase
                           tracking-wider mb-3 flex items-center gap-1.5">
              <ImagePlus size={11} /> Product image
            </p>
            <ImageUploadZone
              currentUrl={editingProduct?.image_url ?? null}
              onFile={onFile}
              disabled={saving || uploadingImage}
            />
            {pendingImage && !uploadingImage && (
              <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
                <CheckCircle size={11} />
                Image ready — uploads when you save
              </p>
            )}
            {uploadingImage && (
              <p className="text-xs text-slate-400 mt-2 animate-pulse">
                Uploading image…
              </p>
            )}
          </div>

          {/* Stock status */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase
                           tracking-wider mb-4">
              Stock status
            </p>

            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-700">
                  {form.is_available ? 'In stock' : 'Out of stock'}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {form.is_available
                    ? 'AISHA is actively offering this to customers'
                    : 'AISHA will not mention this product until restocked'}
                </p>
              </div>
              <Toggle
                on={form.is_available}
                onToggle={() => setForm({ ...form, is_available: !form.is_available })}
              />
            </div>

            {/* Live status indicator — updates as you toggle */}
            <div className={`mt-4 flex items-center gap-2 px-3 py-2.5 rounded-xl
                             transition-colors
                             ${form.is_available
                               ? 'bg-emerald-50 border border-emerald-100'
                               : 'bg-red-50 border border-red-100'}`}>
              {form.is_available
                ? <CheckCircle size={13} className="text-emerald-500 shrink-0" />
                : <XCircle    size={13} className="text-red-400 shrink-0" />}
              <p className={`text-xs font-medium
                             ${form.is_available
                               ? 'text-emerald-700'
                               : 'text-red-600'}`}>
                {form.is_available
                  ? 'AISHA will recommend this product'
                  : 'AISHA will not mention this product'}
              </p>
            </div>
          </div>

          {/* AI upsell */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase
                           tracking-wider mb-1 flex items-center gap-1.5">
              <Sparkles size={11} className="text-amber-500" />
              AI upsell suggestion
            </p>
            <p className="text-xs text-slate-400 mb-3 leading-relaxed">
              When a customer asks about this product, AISHA will naturally
              suggest this alongside it — increasing average order value.
            </p>
            <textarea
              value={form.upsell_text}
              onChange={e => setForm({ ...form, upsell_text: e.target.value })}
              placeholder={config.upsellPlaceholder}
              rows={3}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                         text-sm text-slate-700 placeholder-slate-400 resize-none
                         focus:outline-none focus:ring-2 focus:ring-amber-400
                         focus:border-transparent"
            />
          </div>
        </div>

        {/* ── RIGHT: Product details ── */}
        <div className="space-y-4">

          {/* Basic info */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase
                           tracking-wider mb-4 flex items-center gap-1.5">
              <Tag size={11} /> Basic info
            </p>

            <div className="space-y-4">

              {/* Name */}
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5">
                  Product name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Ankara Dress"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                             text-sm text-slate-700 placeholder-slate-400
                             focus:outline-none focus:ring-2 focus:ring-amber-400
                             focus:border-transparent"
                />
              </div>

              {/* Category */}
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5">
                  Category
                </label>
                <input
                  type="text"
                  value={form.category}
                  onChange={e => setForm({ ...form, category: e.target.value })}
                  placeholder={config.categoryPlaceholder}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                             text-sm text-slate-700 placeholder-slate-400
                             focus:outline-none focus:ring-2 focus:ring-amber-400
                             focus:border-transparent"
                />
              </div>

              {/* Price + Unit */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">
                    Price (KES) <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="number"
                    value={form.price}
                    onChange={e => setForm({ ...form, price: e.target.value })}
                    placeholder="e.g. 3200"
                    min="0"
                    step="0.01"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                               text-sm text-slate-700 placeholder-slate-400
                               focus:outline-none focus:ring-2 focus:ring-amber-400
                               focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1.5">
                    Unit
                  </label>
                  <input
                    type="text"
                    value={form.unit}
                    onChange={e => setForm({ ...form, unit: e.target.value })}
                    placeholder={config.unitPlaceholder}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                               text-sm text-slate-700 placeholder-slate-400
                               focus:outline-none focus:ring-2 focus:ring-amber-400
                               focus:border-transparent"
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5">
                  Description
                </label>
                <textarea
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  placeholder={config.descPlaceholder}
                  rows={3}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                             text-sm text-slate-700 placeholder-slate-400 resize-none
                             focus:outline-none focus:ring-2 focus:ring-amber-400
                             focus:border-transparent"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  AISHA uses this when describing the product to customers.
                </p>
              </div>
            </div>
          </div>

          {/* Variants */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase
                           tracking-wider mb-1 flex items-center gap-1.5">
              <Layers size={11} /> {config.variantLabel}
            </p>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Separate options with commas. AISHA uses this to accurately answer
              "{config.questionHint}?" — instead of guessing from free text.
            </p>

          {/* Worked example so owner knows exactly what to put */}
          <div className="flex items-start gap-2 mb-4 px-3 py-2.5 rounded-xl
                           bg-blue-50 border border-blue-100">
            <span className="text-blue-500 text-xs shrink-0 mt-0.5">e.g.</span>
            <div className="text-xs text-blue-700 leading-relaxed">
              {businessType === 'services'
                ? <><strong>Type label:</strong> Duration &nbsp;→&nbsp; <strong>Options:</strong> 30min, 60min, 90min</>
                : <><strong>Type label:</strong> Size &nbsp;→&nbsp; <strong>Options:</strong> S, M, L, XL<br />
                    <strong>Type label:</strong> Color &nbsp;→&nbsp; <strong>Options:</strong> Red, Blue, Black</>
              }
            </div>
          </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5">
                  Type Label
                  <span className="text-slate-400 font-normal ml-1">(e.g. Size , Color) </span>
                </label>
                <input
                  type="text"
                  value={form.variant_label}
                  onChange={e => setForm({ ...form, variant_label: e.target.value })}
                  placeholder={config.variantLabelHint}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                             text-sm text-slate-700 placeholder-slate-400
                             focus:outline-none focus:ring-2 focus:ring-amber-400
                             focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5">
                  Options
                  <span className="text-slate-400 font-normal ml-1">(comma-separated)</span>
                </label>
                <input
                  type="text"
                  value={form.variant_options}
                  onChange={e => setForm({ ...form, variant_options: e.target.value })}
                  placeholder={config.variantPlaceholder}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200
                             text-sm text-slate-700 placeholder-slate-400
                             focus:outline-none focus:ring-2 focus:ring-amber-400
                             focus:border-transparent"
                />
              </div>
            </div>

            {/* Live chip preview — only shown when options exist */}
            {form.variant_options.trim() && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-2">
                  Preview — how chips appear on the card
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {form.variant_options
                    .split(',')
                    .filter(v => v.trim())
                    .map(v => (
                      <span key={v.trim()}
                        className="text-xs bg-purple-50 text-purple-700
                                   px-2.5 py-1 rounded-full font-medium">
                        {v.trim()}
                      </span>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Form actions */}
      <div className="flex items-center gap-3 mt-6 pt-5 border-t border-slate-200">
        <button
          onClick={onCancel}
          className="px-6 py-2.5 rounded-xl border border-slate-200
                     text-sm font-medium text-slate-600
                     hover:bg-slate-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={onSave}
          disabled={saving || uploadingImage}
          className="px-8 py-2.5 rounded-xl bg-amber-500 text-white
                     text-sm font-medium hover:bg-amber-600 transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploadingImage
            ? 'Uploading image…'
            : saving
              ? 'Saving…'
              : editingProduct ? 'Save changes' : 'Add product'}
        </button>
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function Products() {
  const [products,       setProducts]       = useState(null)
  const [businessType,   setBusinessType]   = useState('retail')
  const [search,         setSearch]         = useState('')
  const [filterStatus,   setFilterStatus]   = useState('all')
  const [filterCategory, setFilterCategory] = useState('all')
  const [view,           setView]           = useState('list') // 'list' | 'form'
  const [editingProduct, setEditingProduct] = useState(null)
  const [form,           setForm]           = useState(EMPTY_FORM)
  const [formError,      setFormError]      = useState(null)
  const [saving,         setSaving]         = useState(false)
  const [pendingImage,   setPendingImage]   = useState(null)
  const [uploadingImage, setUploadingImage] = useState(false)
  const [deleteTarget,   setDeleteTarget]   = useState(null)
  const [deleting,       setDeleting]       = useState(false)
  const [toggling,       setToggling]       = useState(null)

  function loadProducts() {
    getProducts()
      .then(data => setProducts(Array.isArray(data) ? data : []))
      .catch(() => setProducts([]))
  }

  useEffect(() => {
    loadProducts()
    getSettings()
      .then(s => setBusinessType(s?.business_type ?? 'retail'))
      .catch(() => {})
  }, [])

  const config     = VARIANT_CONFIG[businessType] ?? VARIANT_CONFIG.retail
  const categories = ['all', ...new Set((products ?? []).map(p => p.category).filter(Boolean))]
  const availCount = (products ?? []).filter(p => p.is_available).length
  const totalCount = (products ?? []).length

  // ── Navigation ───────────────────────────────────────────────────────────────

  function goToCreate() {
    setEditingProduct(null)
    setForm({ ...EMPTY_FORM })   // all fields blank — no pre-fill
    setFormError(null)
    setPendingImage(null)
    setView('form')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function goToEdit(product) {
    setEditingProduct(product)
    setForm({
      name:            product.name,
      description:     product.description     ?? '',
      price:           String(product.price),
      is_available:    product.is_available,
      category:        product.category        ?? '',
      variant_label:   product.variant_label   ?? '',
      variant_options: product.variant_options ?? '',
      unit:            product.unit            ?? '',
      upsell_text:     product.upsell_text     ?? '',
    })
    setFormError(null)
    setPendingImage(null)
    setView('form')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function goToList() {
    setView('list')
    setEditingProduct(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setPendingImage(null)
  }

  // ── Save ─────────────────────────────────────────────────────────────────────

  async function handleSave() {
    if (!form.name.trim()) {
      setFormError('Product name is required.')
      return
    }
    const priceNum = parseFloat(form.price)
    if (isNaN(priceNum) || priceNum <= 0) {
      setFormError('Enter a valid price greater than 0.')
      return
    }

    setSaving(true)
    setFormError(null)

    try {
      const payload = {
        name:            form.name.trim(),
        description:     form.description.trim()     || null,
        price:           priceNum,
        is_available:    form.is_available,
        category:        form.category.trim()        || null,
        variant_label:   form.variant_label.trim()   || null,
        variant_options: form.variant_options.trim() || null,
        unit:            form.unit.trim()            || null,
        upsell_text:     form.upsell_text.trim()     || null,
      }

      let savedProduct
      if (editingProduct) {
        savedProduct = await updateProduct(editingProduct.id, payload)
      } else {
        savedProduct = await createProduct(payload)
      }

      // Image upload happens after product exists so we have a product ID.
      // On create, savedProduct.id is the new ID.
      // On edit, editingProduct.id is the fallback.
      if (pendingImage) {
        const productId = savedProduct?.id ?? editingProduct?.id
        if (productId) {
          setUploadingImage(true)
          try {
            await uploadProductImage(productId, pendingImage)
          } catch {
            setFormError(
              'Product saved but image upload failed. ' +
              'Edit the product to re-upload the image.'
            )
            loadProducts()
            return
          } finally {
            setUploadingImage(false)
          }
        }
      }

      loadProducts()
      goToList()
    } catch (e) {
      setFormError(e.message || 'Failed to save product.')
    } finally {
      setSaving(false)
    }
  }

  // ── Toggle availability ───────────────────────────────────────────────────────
  // Approach: optimistic update — flip state in UI immediately, call API,
  // revert if API fails. Why: feels instant for the user vs waiting for API.
  // Alternative: pessimistic — wait for API response, then update UI.
  // Pessimistic is safer but feels sluggish for a toggle.

  async function handleToggle(product) {
    setToggling(product.id)
    setProducts(prev => prev.map(p =>
      p.id === product.id ? { ...p, is_available: !p.is_available } : p
    ))
    try {
      await toggleAvailability(product.id, !product.is_available)
    } catch {
      // Revert on failure
      setProducts(prev => prev.map(p =>
        p.id === product.id ? { ...p, is_available: product.is_available } : p
      ))
    } finally {
      setToggling(null)
    }
  }

  // ── Delete ───────────────────────────────────────────────────────────────────

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteProduct(deleteTarget.id)
      setDeleteTarget(null)
      loadProducts()
    } catch (e) {
      console.error('Delete failed', e)
    } finally {
      setDeleting(false)
    }
  }

  // ── Filter ───────────────────────────────────────────────────────────────────

  const filtered = (products ?? []).filter(p => {
    const q = search.toLowerCase()
    const matchSearch =
      p.name.toLowerCase().includes(q) ||
      (p.description  ?? '').toLowerCase().includes(q) ||
      (p.category     ?? '').toLowerCase().includes(q)
    const matchStatus =
      filterStatus === 'all'       ? true :
      filterStatus === 'available' ? p.is_available :
      !p.is_available
    const matchCat = filterCategory === 'all' || p.category === filterCategory
    return matchSearch && matchStatus && matchCat
  })

  // ── Render: form view ────────────────────────────────────────────────────────

  if (view === 'form') {
    return (
      <div className="min-h-full bg-slate-50">
        <ProductForm
          editingProduct={editingProduct}
          form={form}
          setForm={setForm}
          onSave={handleSave}
          onCancel={goToList}
          saving={saving}
          uploadingImage={uploadingImage}
          formError={formError}
          businessType={businessType}
          onFile={setPendingImage}
          pendingImage={pendingImage}
        />
      </div>
    )
  }

  // ── Render: list view ────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-6xl">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center
                      sm:justify-between gap-4 mb-5">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">
            Product catalogue
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            {products === null
              ? 'Loading…'
              : `${totalCount} products · ${availCount} available to AISHA`}
          </p>
        </div>
        <button
          onClick={goToCreate}
          className="flex items-center justify-center gap-2 px-4 py-2.5
                     rounded-xl bg-amber-500 text-white text-sm font-medium
                     hover:bg-amber-600 transition-colors shrink-0"
        >
          <Plus size={16} />
          Add product
        </button>
      </div>

      {/* AI banner */}
      <div className="flex items-start gap-3 mb-5 px-4 py-3 rounded-xl
                      bg-amber-50 border border-amber-200">
        <Sparkles size={15} className="text-amber-600 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-800 leading-relaxed">
          AISHA only recommends <strong>Active</strong> products.
          Toggling a product off instantly removes it from AISHA's knowledge.
          Fill in variants and upsell fields for more accurate customer answers.
        </p>
      </div>

      {/* Search + filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2
                                        -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name, category, description…"
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200
                       text-sm text-slate-700 placeholder-slate-400
                       focus:outline-none focus:ring-2 focus:ring-amber-400
                       focus:border-transparent bg-white"
          />
        </div>

        <div className="flex gap-2 flex-wrap">
          {[
            { key: 'all',         label: 'All' },
            { key: 'available',   label: 'Active' },
            { key: 'unavailable', label: 'Out of stock' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilterStatus(key)}
              className={`px-3 py-2.5 rounded-xl text-xs font-medium
                          transition-colors shrink-0
                          ${filterStatus === key
                            ? 'bg-slate-900 text-white'
                            : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'}`}
            >
              {label}
            </button>
          ))}

          {categories.length > 1 && (
            <select
              value={filterCategory}
              onChange={e => setFilterCategory(e.target.value)}
              className="px-3 py-2.5 rounded-xl border border-slate-200 text-xs
                         text-slate-600 bg-white focus:outline-none
                         focus:ring-2 focus:ring-amber-400"
            >
              {categories.map(c => (
                <option key={c} value={c}>
                  {c === 'all' ? 'All categories' : c}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Cards grid */}
      {products === null ? (
        <div className="flex items-center justify-center h-40">
          <p className="text-sm text-slate-400">Loading products…</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Package size={36} className="text-slate-300" />
          <p className="text-sm text-slate-400">
            {search || filterStatus !== 'all' || filterCategory !== 'all'
              ? 'No products match your filters'
              : 'No products yet — add your first one'}
          </p>
          {!search && filterStatus === 'all' && filterCategory === 'all' && (
            <button
              onClick={goToCreate}
              className="text-sm text-amber-600 font-medium hover:underline"
            >
              Add a product
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(p => (
            <ProductCard
              key={p.id}
              product={p}
              onEdit={goToEdit}
              onDelete={setDeleteTarget}
              onToggle={handleToggle}
              toggling={toggling}
            />
          ))}
        </div>
      )}

      {/* Delete modal */}
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
                  Delete product?
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  This cannot be undone.
                </p>
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-5">
              <strong>{deleteTarget.name}</strong> will be permanently removed
              and AISHA will no longer offer it to customers.
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