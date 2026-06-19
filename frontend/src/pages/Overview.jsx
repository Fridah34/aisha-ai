import { useEffect, useState } from 'react'
import { getInbox } from '../api/conversations'
import { getProducts } from '../api/products'
import { getSettings } from '../api/settings'
import { Users, MessageSquare, Package, AlertTriangle } from 'lucide-react'

const HANDOVER_PHRASE = 'Let me connect you with our team'

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function formatPhone(phone) {
  // +254706040948 → 0706 040 948 (readable)
  if (!phone) return '—'
  if (phone.startsWith('+254')) {
    const local = '0' + phone.slice(4)
    return local.slice(0, 4) + ' ' + local.slice(4, 7) + ' ' + local.slice(7)
  }
  return phone
}

function initials(phone) {
  // No customer names in DB yet — use first digits of phone
  if (!phone) return '?'
  const digits = phone.replace(/\D/g, '')
  return digits.slice(-3, -1) // last 2 meaningful digits as avatar
}

function greeting(name) {
  const h = new Date().getHours()
  const time = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
  return name ? `Good ${time}, ${name}` : `Good ${time}`
}

function StatCard({ label, value, sub, Icon, iconBg, iconColor }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col gap-3">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${iconBg}`}>
        <Icon size={18} className={iconColor}  />
      </div>
      <div>
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</p>
        <p className="text-3xl font-semibold text-slate-800 mt-1 leading-none">
          {value ?? '—'}
        </p>
        <p className="text-xs text-slate-400 mt-1">{sub}</p>
      </div>
    </div>
  )
}

export default function Overview() {
  const [inbox,    setInbox]    = useState(null)
  const [products, setProducts] = useState(null)
  const [settings, setSettings] = useState(null)

  useEffect(() => {
    Promise.allSettled([getInbox(), getProducts(), getSettings()])
      .then(([c, p, s]) => {
        setInbox(   c.status === 'fulfilled' ? (Array.isArray(c.value) ? c.value : []) : [])
        setProducts(p.status === 'fulfilled' ? (Array.isArray(p.value) ? p.value : []) : [])
        setSettings(s.status === 'fulfilled' ? s.value : null)
      })
  }, [])

  // Derive stats from real field names
  const totalMessages = inbox?.reduce((sum, c) => sum + (c.total_messages ?? 0), 0) ?? null
  const handovers     = inbox?.filter(c =>
    c.last_message?.includes(HANDOVER_PHRASE)
  ).length ?? null

  const hasKB   = settings?.knowledge_base_text?.trim().length > 0
  const kbWords = hasKB
    ? settings.knowledge_base_text.trim().split(/\s+/).length
    : 0

  return (
    <div className="p-8 max-w-6xl">

      {/* Greeting */}
      <div className="mb-7">
        <h2 className="text-xl font-semibold text-slate-800">
          {greeting(settings?.business_name)}
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          {settings
            ? `${settings.business_name} · ${settings.whatsapp_phone_number ?? 'WhatsApp not set'}`
            : "Here's what's happening with your business today."}
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        <StatCard
          label="Customers"
          value={inbox?.length}
          sub="unique WhatsApp contacts"
          Icon={Users}
          iconBg="bg-amber-50"
          iconColor="text-amber-500"
        />
        <StatCard
          label="Total messages"
          value={totalMessages}
          sub="across all conversations"
          Icon={MessageSquare}
          iconBg="bg-teal-50"
          iconColor="text-teal-600"
        />
        <StatCard
          label="Products"
          value={products?.length}
          sub="listed in catalogue"
          Icon={Package}
          iconBg="bg-blue-50"
          iconColor="text-blue-500"
        />
        <StatCard
          label="Handovers"
          value={handovers}
          sub="customers needing you"
          Icon={AlertTriangle}
          iconBg="bg-red-50"
          iconColor="text-red-500"
        />
      </div>

      {/* Recent conversations + products */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-4">
            Recent conversations
          </p>
          {inbox === null ? (
            <p className="text-sm text-slate-400 py-4 text-center">Loading…</p>
          ) : inbox.length === 0 ? (
            <p className="text-sm text-slate-400 py-4 text-center">No conversations yet</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {inbox.slice(0, 5).map((c) => {
                const isHandover = c.last_message?.includes(HANDOVER_PHRASE)
                return (
                  <div key={c.customer_id} className="flex items-center gap-3 py-3">
                    {/* Avatar — amber circle with last 2 phone digits */}
                    <div className="w-8 h-8 rounded-full bg-amber-50 text-amber-700
                                    flex items-center justify-center text-xs font-semibold shrink-0">
                      {initials(c.customer_phone)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-700">
                        {formatPhone(c.customer_phone)}
                      </p>
                      <p className="text-xs text-slate-400 truncate">{c.last_message}</p>
                    </div>

                    <div className="flex flex-col items-end gap-1 shrink-0">
                      {isHandover && (
                        <span className="text-[10px] bg-red-50 text-red-600 font-medium
                                         rounded-full px-2 py-0.5">
                          needs you
                        </span>
                      )}
                      <span className="text-xs text-slate-400">
                        {timeAgo(c.last_message_time)}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-4">
            Product catalogue
          </p>
          {products === null ? (
            <p className="text-sm text-slate-400 py-4 text-center">Loading…</p>
          ) : products.length === 0 ? (
            <p className="text-sm text-slate-400 py-4 text-center">No products listed yet</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {products.slice(0, 5).map((p) => (
                <div key={p.id} className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-700">{p.name}</p>
                    <p className="text-xs text-slate-400">{p.description}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0 ml-3">
                    <p className="text-sm font-semibold text-slate-700">
                      KES {Number(p.price).toLocaleString()}
                    </p>
                    <span className={`text-[10px] font-medium rounded-full px-2 py-0.5
                      ${p.is_available
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-slate-100 text-slate-500'}`}>
                      {p.is_available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Business profile + KB status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-4">
            Business profile
          </p>
          {settings ? (
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-800">{settings.business_name}</p>
              <p className="text-xs text-slate-400">{settings.email ?? '—'}</p>
              <p className="text-xs text-slate-400">
                {settings.whatsapp_phone_number ?? 'WhatsApp number not set'}
              </p>
              <span className="inline-block mt-2 px-3 py-0.5 rounded-full bg-amber-50
                               text-amber-700 text-xs font-medium capitalize">
                {settings.business_type ?? 'general'}
              </span>
            </div>
          ) : (
            <p className="text-sm text-slate-400 py-2">Start backend to load profile</p>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-4">
            AI knowledge base
          </p>
          {settings ? (
            <div className="flex items-start gap-3">
              <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0
                              ${hasKB ? 'bg-emerald-500' : 'bg-red-400'}`} />
              <div>
                <p className="text-sm font-medium text-slate-700">
                  {hasKB ? 'Knowledge base active' : 'No knowledge base configured'}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {hasKB
                    ? `${kbWords} words · AISHA uses this to answer customers`
                    : 'Go to Settings and add your business info so AISHA answers accurately'}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 py-2">Start backend to load</p>
          )}
        </div>

      </div>
    </div>
  )
}