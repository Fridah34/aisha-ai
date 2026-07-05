import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Settings, User, Bell, ChevronDown, LogOut, } from 'lucide-react'
import { getSettings } from '../api/settings'
import { useAuth } from '../hooks/useAuth'

export default function TopBar() {
  const navigate      = useNavigate()
  const { logout }   = useAuth()
  const [open, setOpen]   = useState(false)
  const [owner, setOwner] = useState(null)
  const dropdownRef       = useRef(null)

  useEffect(() => {
    getSettings().then(setOwner).catch(() => setOwner(null))
  }, [])

  useEffect(() => {
    function handler(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const initials = owner?.business_name
    ? owner.business_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'AI'

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center
                       justify-between px-4 md:px-6 shrink-0">

      {/* Left — hamburger on mobile, AISHA title always */}
      <div className="flex items-center gap-3">
        {/* Hamburger — only visible on mobile */}

        <div className="flex items-center gap-2">
          <span className="text-amber-500 font-bold text-xl tracking-wide">AISHA</span>
          <span className="text-slate-400 text-sm font-medium hidden sm:block">AI</span>
        </div>
      </div>

      {/* Right — bell + account */}
      <div className="flex items-center gap-2">
        <button className="relative p-2 text-slate-400 hover:text-slate-600
                           hover:bg-slate-100 rounded-lg transition-colors">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500" />
        </button>

        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setOpen(prev => !prev)}
            className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl
                       hover:bg-slate-100 transition-colors"
          >
            <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center
                            justify-center text-slate-900 font-bold text-xs shrink-0">
              {initials}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-slate-800 text-sm font-medium leading-tight
                            truncate max-w-[130px]">
                {owner?.business_name ?? '—'}
              </p>
              <p className="text-slate-400 text-xs truncate max-w-[130px]">
                {owner?.email ?? 'Loading...'}
              </p>
            </div>
            <ChevronDown
              size={14}
              className={`text-slate-400 transition-transform duration-200
                          ${open ? 'rotate-180' : ''}`}
            />
          </button>

          {open && (
            <div className="absolute right-0 top-[52px] w-60 bg-white rounded-xl
                            shadow-xl border border-slate-200 py-1.5 z-50">
              <div className="px-4 py-3 border-b border-slate-100">
                {owner ? (
                  <>
                    <p className="text-slate-800 text-sm font-semibold">{owner.business_name}</p>
                    <p className="text-slate-500 text-xs mt-0.5">{owner.email}</p>
                    {owner.whatsapp_phone_number && (
                      <p className="text-slate-500 text-xs">{owner.whatsapp_phone_number}</p>
                    )}
                    <span className="inline-block mt-2 px-2 py-0.5 rounded-full
                                     bg-amber-100 text-amber-700 text-xs font-medium capitalize">
                      {owner.business_type ?? 'general'}
                    </span>
                  </>
                ) : (
                  <p className="text-slate-400 text-xs">Start backend to load profile</p>
                )}
              </div>

              <button
                onClick={() => { navigate('/settings'); setOpen(false) }}
                className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm
                           text-slate-600 hover:bg-slate-50 transition-colors"
              >
                <Settings size={15} /> Settings
              </button>
              <button
                onClick={() => { navigate('/settings'); setOpen(false) }}
                className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm
                           text-slate-600 hover:bg-slate-50 transition-colors"
              >
                <User size={15} /> Profile
              </button>

              <div className="border-t border-slate-100 mt-1 pt-1">
                <button
                  onClick={logout} // FIXED: Wipes browser cache strings and forces clean redirects instantly
                  className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm
                             text-red-500 hover:bg-red-50 transition-colors"
                >
                  <LogOut size={15} /> Log out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}