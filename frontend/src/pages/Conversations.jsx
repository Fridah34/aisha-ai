import { useEffect, useState, useRef } from 'react'
import {
  MessageSquare, AlertTriangle, Phone, Clock,
  UserCheck, CheckCircle, Send, Bot, User
} from 'lucide-react'
import { getInbox, getThread, takeOver, resolve, sendReply } from '../api/conversations'

const HANDOVER_PHRASE = 'Let me connect you with our team'

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatPhone(phone) {
  if (!phone) return '—'
  if (phone.startsWith('+254')) {
    const local = '0' + phone.slice(4)
    return local.slice(0, 4) + ' ' + local.slice(4, 7) + ' ' + local.slice(7)
  }
  return phone
}

function initials(phone) {
  if (!phone) return '?'
  return phone.replace(/\D/g, '').slice(-3, -1)
}

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-KE', {
    hour: '2-digit', minute: '2-digit', hour12: true,
  })
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' })
}

function groupByDate(messages) {
  const groups = []
  let currentDate = null
  let currentGroup = []
  messages.forEach((msg) => {
    const date = formatDate(msg.timestamp)
    if (date !== currentDate) {
      if (currentGroup.length) groups.push({ date: currentDate, messages: currentGroup })
      currentDate = date
      currentGroup = [msg]
    } else {
      currentGroup.push(msg)
    }
  })
  if (currentGroup.length) groups.push({ date: currentDate, messages: currentGroup })
  return groups
}

function StatusBadge({ status }) {
  const map = {
    needs_human:  { label: 'Needs you',     cls: 'bg-red-50 text-red-600 border border-red-100' },
    human_active: { label: "You're live",   cls: 'bg-amber-50 text-amber-700 border border-amber-200' },
    resolved:     { label: 'Resolved',      cls: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
    ai_active:    { label: 'AISHA active',  cls: 'bg-slate-100 text-slate-500' },
  }
  const s = map[status] ?? map.ai_active
  return (
    <span className={`text-[10px] font-medium rounded-full px-2 py-0.5 ${s.cls}`}>
      {s.label}
    </span>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Conversations() {
  const [inbox,           setInbox]           = useState(null)
  const [selected,        setSelected]        = useState(null)
  const [thread,          setThread]          = useState(null)
  const [statuses,        setStatuses]        = useState({})
  const [loadingThread,   setLoadingThread]   = useState(false)
  const [replyText,       setReplyText]       = useState('')
  const [sending,         setSending]         = useState(false)
  const [replyError,      setReplyError]      = useState(null)
  const [actionLoading,   setActionLoading]   = useState(false)
  const [failedMessageIds, setFailedMessageIds] = useState(new Set())

  const threadEndRef = useRef(null)
  const replyRef     = useRef(null)

  // Load inbox on mount
  useEffect(() => {
    getInbox()
      .then((data) => {
        const list = Array.isArray(data) ? data : []
        setInbox(list)
        if (list.length > 0) openThread(list[0])
      })
      .catch(() => setInbox([]))
  }, [])

  // Scroll to bottom whenever thread updates
  useEffect(() => {
    if (thread) threadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [thread])

  function openThread(customer) {
    setSelected(customer)
    setThread(null)
    setReplyText('')
    setReplyError(null)
    setLoadingThread(true)
    getThread(customer.customer_id)
      .then((data) => {
        setThread(data)
        // Use real status from DB — not inferred from last_message
        setStatuses(prev => ({
          ...prev,
          [customer.customer_id]: data.conversation_status ?? 'ai_active',
        }))
      })
      .catch(() => setThread(null))
      .finally(() => setLoadingThread(false))
  }

  async function handleTakeOver() {
    if (!selected) return
    setActionLoading(true)
    try {
      await takeOver(selected.customer_id)
      setStatuses(prev => ({ ...prev, [selected.customer_id]: 'human_active' }))
    } catch (e) {
      console.error('Takeover failed', e)
    } finally {
      setActionLoading(false)
    }
  }

  async function handleResolve() {
    if (!selected) return
    setActionLoading(true)
    try {
      await resolve(selected.customer_id)
      setStatuses(prev => ({ ...prev, [selected.customer_id]: 'resolved' }))
      const updated = await getInbox()
      setInbox(Array.isArray(updated) ? updated : [])
    } catch (e) {
      console.error('Resolve failed', e)
    } finally {
      setActionLoading(false)
    }
  }

  async function handleSendReply() {
    if (!replyText.trim() || !selected) return
    setSending(true)
    setReplyError(null)
    try {
      const result = await sendReply(selected.customer_id, replyText.trim())
      setReplyText('')

      // Refresh thread to show the new human message
      const updated = await getThread(selected.customer_id)
      setThread(updated)
      setTimeout(() => threadEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)

      // If Twilio failed, mark that message bubble and show banner
      if (!result.twilio_delivered) {
        setReplyError(
          'Message saved to thread but WhatsApp delivery failed. ' +
          'The customer may not have received it — ' +
          'check that their number has joined the Twilio sandbox.'
        )
      }
    } catch (e) {
      setReplyError('Failed to send. Check that the backend is running.')
      console.error('Reply failed', e)
    } finally {
      setSending(false)
      replyRef.current?.focus()
    }
  }

  function handleReplyKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendReply()
    }
  }

  const currentStatus = selected ? (statuses[selected.customer_id] ?? 'ai_active') : null
  const isHumanActive = currentStatus === 'human_active'
  const isResolved    = currentStatus === 'resolved'

  return (
    <div className="flex h-full overflow-hidden">

      {/* ── LEFT: Inbox ───────────────────────────────────────────── */}
      <aside className="w-80 shrink-0 border-r border-slate-200 bg-white flex flex-col overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h2 className="text-sm font-semibold text-slate-800">Inbox</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {inbox ? `${inbox.length} conversations` : 'Loading…'}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {inbox === null ? (
            <p className="text-sm text-slate-400 text-center py-10">Loading…</p>
          ) : inbox.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-2">
              <MessageSquare size={28} className="text-slate-300" />
              <p className="text-sm text-slate-400">No conversations yet</p>
            </div>
          ) : (
            inbox.map((c) => {
              const active = selected?.customer_id === c.customer_id
              const status = statuses[c.customer_id] ??
                (c.last_message?.includes(HANDOVER_PHRASE) ? 'needs_human' : 'ai_active')
              return (
                <button
                  key={c.customer_id}
                  onClick={() => openThread(c)}
                  className={`w-full text-left px-5 py-4 border-b border-slate-100
                              transition-colors flex items-start gap-3
                              ${active
                                ? 'bg-amber-50 border-l-2 border-l-amber-500'
                                : 'hover:bg-slate-50'}`}
                >
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center
                                   text-xs font-semibold shrink-0 mt-0.5
                                   ${active
                                     ? 'bg-amber-500 text-white'
                                     : 'bg-amber-50 text-amber-700'}`}>
                    {initials(c.customer_phone)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <p className={`text-sm font-medium truncate
                                     ${active ? 'text-amber-700' : 'text-slate-700'}`}>
                        {formatPhone(c.customer_phone)}
                      </p>
                      <span className="text-[10px] text-slate-400 shrink-0">
                        {timeAgo(c.last_message_time)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 truncate mt-0.5">{c.last_message}</p>
                    <div className="mt-1.5">
                      <StatusBadge status={status} />
                    </div>
                  </div>
                </button>
              )
            })
          )}
        </div>
      </aside>

      {/* ── RIGHT: Thread ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-50">
        {!selected ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <MessageSquare size={40} className="text-slate-300" />
            <p className="text-sm text-slate-400">Select a conversation to view messages</p>
          </div>
        ) : (
          <>
            {/* ── Thread header ── */}
            <div className="bg-white border-b border-slate-200 px-6 py-3 shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-amber-50 text-amber-700
                                  flex items-center justify-center text-xs font-semibold">
                    {initials(selected.customer_phone)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-slate-800">
                        {formatPhone(selected.customer_phone)}
                      </p>
                      <StatusBadge status={currentStatus} />
                    </div>
                    <p className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                      <Phone size={10} />
                      {selected.customer_phone}
                      <span className="mx-1">·</span>
                      <Clock size={10} />
                      {selected.total_messages} messages
                    </p>
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-2">
                  {currentStatus === 'needs_human' && (
                    <button
                      onClick={handleTakeOver}
                      disabled={actionLoading}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg
                                 bg-amber-500 text-white text-xs font-medium
                                 hover:bg-amber-600 transition-colors disabled:opacity-50"
                    >
                      <UserCheck size={13} />
                      Take over
                    </button>
                  )}
                  {(currentStatus === 'human_active' || currentStatus === 'needs_human') && (
                    <button
                      onClick={handleResolve}
                      disabled={actionLoading}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg
                                 bg-emerald-500 text-white text-xs font-medium
                                 hover:bg-emerald-600 transition-colors disabled:opacity-50"
                    >
                      <CheckCircle size={13} />
                      Mark resolved
                    </button>
                  )}
                </div>
              </div>

              {/* Status banners */}
              {currentStatus === 'needs_human' && (
                <div className="mt-3 flex items-start gap-2 px-3 py-2 rounded-lg
                                bg-red-50 border border-red-100">
                  <AlertTriangle size={13} className="text-red-500 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-600">
                    AISHA could not handle this — customer needs your direct reply.
                    Click <strong>Take over</strong> to start replying, then{' '}
                    <strong>Mark resolved</strong> when done so AISHA resumes.
                  </p>
                </div>
              )}

              {currentStatus === 'human_active' && (
                <div className="mt-3 flex items-start gap-2 px-3 py-2 rounded-lg
                                bg-amber-50 border border-amber-200">
                  <UserCheck size={13} className="text-amber-600 shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-700">
                    You are handling this conversation. AISHA is paused.
                    Use the reply box below to message the customer directly via WhatsApp.
                    Click <strong>Mark resolved</strong> when done.
                  </p>
                </div>
              )}

              {currentStatus === 'resolved' && (
                <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg
                                bg-emerald-50 border border-emerald-200">
                  <CheckCircle size={13} className="text-emerald-600 shrink-0" />
                  <p className="text-xs text-emerald-700">
                    Resolved. AISHA will resume auto-replying on the next customer message.
                  </p>
                </div>
              )}
            </div>

            {/* ── Messages ── */}
            <div className="flex-1 overflow-y-auto px-6 py-4 min-h-0">
              {loadingThread ? (
                <div className="flex items-center justify-center h-32">
                  <p className="text-sm text-slate-400">Loading messages…</p>
                </div>
              ) : !thread ? (
                <div className="flex items-center justify-center h-32">
                  <p className="text-sm text-slate-400">Failed to load thread</p>
                </div>
              ) : (
                groupByDate(thread.messages).map((group) => (
                  <div key={group.date}>
                    {/* Date separator */}
                    <div className="flex items-center gap-3 my-5">
                      <div className="flex-1 h-px bg-slate-200" />
                      <span className="text-[11px] text-slate-400 font-medium">
                        {group.date}
                      </span>
                      <div className="flex-1 h-px bg-slate-200" />
                    </div>

                    <div className="space-y-2">
                      {group.messages.map((msg) => {

                        // Handover system event — centred pill
                        if (msg.message_text === HANDOVER_PHRASE ||
                            msg.message_text?.includes(HANDOVER_PHRASE)) {
                          return (
                            <div key={msg.id} className="flex justify-center my-4">
                              <span className="flex items-center gap-1.5 text-xs
                                               bg-red-50 text-red-600 border border-red-100
                                               rounded-full px-3 py-1.5 font-medium">
                                <AlertTriangle size={11} />
                                AISHA triggered human handover · {formatTime(msg.timestamp)}
                              </span>
                            </div>
                          )
                        }

                        // Customer message — left aligned, white bubble
                        if (msg.sender === 'customer') {
                          return (
                            <div key={msg.id} className="flex justify-start">
                              <div className="max-w-[68%]">
                                <div className="bg-white border border-slate-200 text-slate-700
                                                px-4 py-2.5 rounded-2xl rounded-tl-sm
                                                text-sm leading-relaxed">
                                  {msg.message_text}
                                </div>
                                <p className="text-[10px] text-slate-400 mt-1 ml-1">
                                  {formatTime(msg.timestamp)}
                                  {msg.language !== 'en' && (
                                    <span className="ml-1.5 uppercase font-medium text-slate-500">
                                      {msg.language}
                                    </span>
                                  )}
                                </p>
                              </div>
                            </div>
                          )
                        }

                        // AISHA reply — right aligned, amber bubble
                        if (msg.sender === 'assistant') {
                          return (
                            <div key={msg.id} className="flex justify-end">
                              <div className="max-w-[68%]">
                                <div className="bg-amber-500 text-white px-4 py-2.5
                                                rounded-2xl rounded-tr-sm text-sm leading-relaxed">
                                  {msg.message_text}
                                </div>
                                <div className="flex items-center justify-end gap-1 mt-1 mr-1">
                                  <Bot size={9} className="text-amber-400" />
                                  <p className="text-[10px] text-slate-400">
                                    AISHA · {formatTime(msg.timestamp)}
                                  </p>
                                </div>
                              </div>
                            </div>
                          )
                        }

                        // Human (owner) reply — right aligned, slate bubble
                        // Shows delivery failure indicator if Twilio didn't deliver
                        if (msg.sender === 'human') {
  const deliveryFailed = msg.delivery_status === 'failed'
  return (
    <div key={msg.id} className="flex justify-end">
      <div className="max-w-[68%]">
        <div className={`px-4 py-2.5 rounded-2xl rounded-tr-sm
                        text-sm leading-relaxed text-white
                        ${deliveryFailed
                          ? 'bg-slate-700 ring-1 ring-red-400'
                          : 'bg-slate-700'}`}>
          {msg.message_text}
        </div>
        <div className="flex items-center justify-end gap-1 mt-1 mr-1">
          {deliveryFailed ? (
            <>
              <AlertTriangle size={9} className="text-red-400" />
              <p className="text-[10px] text-red-400">
                Not delivered · {formatTime(msg.timestamp)}
              </p>
            </>
          ) : (
            <>
              <User size={9} className="text-slate-400" />
              <p className="text-[10px] text-slate-400">
                You · {formatTime(msg.timestamp)}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}     

                        return null
                      })}
                    </div>
                  </div>
                ))
              )}
              <div ref={threadEndRef} />
            </div>

            {/* ── Reply box — only when human_active ── */}
            {isHumanActive && (
              <div className="shrink-0 bg-white border-t border-slate-200 px-6 py-4">

                {/* Delivery failure banner */}
                {replyError && (
                  <div className="flex items-start gap-2 mb-3 px-3 py-2.5 rounded-lg
                                  bg-red-50 border border-red-100">
                    <AlertTriangle size={13} className="text-red-500 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs font-medium text-red-600">
                        WhatsApp delivery failed
                      </p>
                      <p className="text-xs text-red-500 mt-0.5">{replyError}</p>
                    </div>
                    <button
                      onClick={() => setReplyError(null)}
                      className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-2"
                    >
                      ✕
                    </button>
                  </div>
                )}

                <div className="flex items-end gap-3">
                  <textarea
                    ref={replyRef}
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={handleReplyKey}
                    placeholder="Type your reply… (Enter to send, Shift+Enter for new line)"
                    rows={2}
                    className="flex-1 resize-none rounded-xl border border-slate-200
                               px-4 py-3 text-sm text-slate-700 placeholder-slate-400
                               focus:outline-none focus:ring-2 focus:ring-amber-400
                               focus:border-transparent"
                  />
                  <button
                    onClick={handleSendReply}
                    disabled={!replyText.trim() || sending}
                    className="flex items-center gap-2 px-4 py-3 rounded-xl
                               bg-amber-500 text-white text-sm font-medium
                               hover:bg-amber-600 transition-colors
                               disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                  >
                    <Send size={15} />
                    {sending ? 'Sending…' : 'Send'}
                  </button>
                </div>

                <p className="text-[11px] text-slate-400 mt-2">
                  Sends directly to customer via WhatsApp · saved to thread regardless of delivery
                </p>
              </div>
            )}

            {/* ── Read-only footer when AI active or resolved ── */}
            {!isHumanActive && (
              <div className="shrink-0 bg-white border-t border-slate-200 px-6 py-3">
                <p className="text-xs text-slate-400 text-center">
                  {isResolved
                    ? 'Resolved · AISHA will resume on next customer message'
                    : 'AISHA is handling replies automatically via WhatsApp · Read-only view'}
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}