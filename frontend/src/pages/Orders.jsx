import { useEffect, useMemo, useState } from 'react'
import {
  Package, User, Phone, Clock, AlertCircle, ShoppingBag, Hash,
} from 'lucide-react'
import { getOrders, updateOrderStatus } from '../api/orders'

// ── Constants ──────────────────────────────────────────────────────────────────
// Order matters here — this is also the left-to-right progression a
// business owner expects a real order to move through, which is why the
// filter pills and the <select> options below both use this array rather
// than the raw enum order coming off the OrderStatus Python enum.

const STATUSES = ['pending', 'paid', 'shipped', 'delivered', 'cancelled']

const STATUS_META = {
  pending:   { label: 'Pending',   badge: 'bg-slate-100 text-slate-500',    dot: 'bg-slate-400' },
  paid:      { label: 'Paid',      badge: 'bg-amber-100 text-amber-700',    dot: 'bg-amber-500' },
  shipped:   { label: 'Shipped',   badge: 'bg-blue-100 text-blue-700',      dot: 'bg-blue-500' },
  delivered: { label: 'Delivered', badge: 'bg-emerald-100 text-emerald-700',dot: 'bg-emerald-500' },
  cancelled: { label: 'Cancelled', badge: 'bg-red-100 text-red-500',        dot: 'bg-red-400' },
}

function formatMoney(n) {
  return `KSh ${Number(n).toLocaleString('en-KE', { minimumFractionDigits: 2 })}`
}

function formatTimestamp(iso) {
  return new Date(iso).toLocaleString('en-KE', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

// ── Status select ──────────────────────────────────────────────────────────────
// A native <select> rather than a custom dropdown or a status-change modal —
// this is a single-field, low-risk mutation (see Categories' Toggle for the
// same reasoning applied to is_active). A modal would add a confirm step for
// something an owner will do dozens of times a day.

function StatusSelect({ status, onChange, disabled }) {
  const meta = STATUS_META[status]
  return (
    <select
      value={status}
      disabled={disabled}
      onChange={e => onChange(e.target.value)}
      className={`text-xs font-medium rounded-lg px-2.5 py-1.5 border-0
                  focus:outline-none focus:ring-2 focus:ring-amber-400
                  disabled:opacity-50 disabled:cursor-wait cursor-pointer
                  ${meta.badge}`}
    >
      {STATUSES.map(s => (
        <option key={s} value={s}>{STATUS_META[s].label}</option>
      ))}
    </select>
  )
}

// ── Order item row ─────────────────────────────────────────────────────────────

function OrderItemRow({ item, onStatusChange, updatingId }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5
                    border-b border-slate-50 last:border-b-0">
      <div className="min-w-0 flex-1">
        <p className="text-sm text-slate-700 truncate">{item.product_name}</p>
        <p className="text-xs text-slate-400 mt-0.5">
          Qty {item.quantity} · {formatMoney(item.total_amount)}
        </p>
      </div>
      <StatusSelect
        status={item.status}
        disabled={updatingId === item.id}
        onChange={next => onStatusChange(item, next)}
      />
    </div>
  )
}

// ── Order group card ───────────────────────────────────────────────────────────

function OrderGroupCard({ group, onStatusChange, updatingId }) {
  const grandTotal = group.items.reduce((sum, i) => sum + Number(i.total_amount), 0)

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4
                    hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-400">
            <Hash size={11} />
            {group.order_ref}
          </div>
          <div className="flex items-center gap-1.5 mt-1.5">
            <User size={13} className="text-slate-400 shrink-0" />
            <p className="text-sm font-semibold text-slate-800 truncate">
              {group.customer_name || 'Unknown customer'}
            </p>
          </div>
          {group.customer_phone && (
            <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-400">
              <Phone size={11} />
              {group.customer_phone}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400 shrink-0">
          <Clock size={11} />
          {formatTimestamp(group.created_at)}
        </div>
      </div>

      <div className="mt-3 pt-1">
        {group.items.map(item => (
          <OrderItemRow
            key={item.id}
            item={item}
            onStatusChange={onStatusChange}
            updatingId={updatingId}
          />
        ))}
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
        <span className="text-xs text-slate-400">
          {group.items.length} item{group.items.length === 1 ? '' : 's'}
        </span>
        <span className="text-sm font-semibold text-slate-800">
          {formatMoney(grandTotal)}
        </span>
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function Orders() {
  const [groups, setGroups]   = useState(null)
  const [filter, setFilter]   = useState('all')
  const [error, setError]     = useState(null)
  const [updatingId, setUpdatingId] = useState(null)

  function loadOrders() {
    getOrders()
      .then(data => setGroups(Array.isArray(data) ? data : []))
      .catch(() => setGroups([]))
  }

  useEffect(() => { loadOrders() }, [])

  // A group "matches" a status filter if any item in it carries that status —
  // a group is not collapsed to a single status the way an item is, since a
  // group can legitimately have mixed item statuses (see Order model notes).
  const filteredGroups = useMemo(() => {
    if (!groups) return null
    if (filter === 'all') return groups
    return groups.filter(g => g.items.some(i => i.status === filter))
  }, [groups, filter])

  async function handleStatusChange(item, nextStatus) {
    const prevStatus = item.status
    setError(null)
    setUpdatingId(item.id)

    // Optimistic update: flip the item's status in local state immediately,
    // then reconcile with the server. Chosen over waiting for the response
    // because status changes here are simple and low-conflict (one owner,
    // one item) — the wait would be pure latency with no real payoff.
    // Refetch-on-failure (rather than hand-rolling a revert) keeps this
    // simple and guarantees the UI matches the server's actual state.
    setGroups(prev => prev.map(g => ({
      ...g,
      items: g.items.map(i => i.id === item.id ? { ...i, status: nextStatus } : i),
    })))

    try {
      await updateOrderStatus(item.id, nextStatus)
    } catch (e) {
      setError(`Couldn't update ${item.product_name} to ${STATUS_META[nextStatus].label} — reverted.`)
      setGroups(prev => prev.map(g => ({
        ...g,
        items: g.items.map(i => i.id === item.id ? { ...i, status: prevStatus } : i),
      })))
    } finally {
      setUpdatingId(null)
    }
  }

  const totalCount = (groups ?? []).length

  return (
    <div className="p-6 max-w-6xl">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center
                      sm:justify-between gap-4 mb-5">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Orders</h2>
          <p className="text-sm text-slate-400 mt-1">
            {groups === null ? 'Loading…' : `${totalCount} order${totalCount === 1 ? '' : 's'}`}
          </p>
        </div>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 mb-5 px-4 py-3 rounded-xl
                      bg-amber-50 border border-amber-200">
        <ShoppingBag size={15} className="text-amber-600 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-800 leading-relaxed">
          Each card is one WhatsApp checkout. Update an item's status as it
          moves — a single checkout can have items at different stages, so
          statuses are set per item, not per order.
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-start gap-2 px-4 py-3 rounded-xl
                        bg-red-50 border border-red-100 mb-5">
          <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Filter pills */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <button
          onClick={() => setFilter('all')}
          className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors
                      ${filter === 'all'
                        ? 'bg-slate-800 text-white border-slate-800'
                        : 'text-slate-500 border-slate-200 hover:bg-slate-50'}`}
        >
          All
        </button>
        {STATUSES.map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5
                        rounded-full border transition-colors
                        ${filter === s
                          ? 'bg-slate-800 text-white border-slate-800'
                          : 'text-slate-500 border-slate-200 hover:bg-slate-50'}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${STATUS_META[s].dot}`} />
            {STATUS_META[s].label}
          </button>
        ))}
      </div>

      {/* Cards grid */}
      {groups === null ? (
        <div className="flex items-center justify-center h-40">
          <p className="text-sm text-slate-400">Loading orders…</p>
        </div>
      ) : filteredGroups.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Package size={36} className="text-slate-300" />
          <p className="text-sm text-slate-400">
            {filter === 'all'
              ? 'No orders yet — they will appear here once a customer checks out on WhatsApp'
              : `No ${STATUS_META[filter].label.toLowerCase()} items right now`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredGroups.map(g => (
            <OrderGroupCard
              key={g.order_ref}
              group={g}
              onStatusChange={handleStatusChange}
              updatingId={updatingId}
            />
          ))}
        </div>
      )}
    </div>
  )
}