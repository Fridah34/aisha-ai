import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, Package,
  Settings, LogOut, ChevronLeft, ChevronRight, Store,
} from 'lucide-react'
import { getSettings } from '../api/settings'

const links = [
  { to: '/overview',      label: 'Overview',       icon: LayoutDashboard },
  { to: '/conversations', label: 'Conversations',  icon: MessageSquare },
  { to: '/products',      label: 'Products',       icon: Package },
  { to: '/settings',      label: 'Settings',       icon: Settings },
]

export default function Sidebar({ collapsed, onToggle, onNavClick }) {
  const [business, setBusiness] = useState(null)

  useEffect(() => {
    getSettings().then(setBusiness).catch(() => setBusiness(null))
  }, [])

  return (
    <aside
      style={{ width: collapsed ? '64px' : '240px' }}
      className="relative flex flex-col bg-slate-900 border-r border-slate-800
                 transition-all duration-300 ease-in-out shrink-0 h-screen"
    >
      {/* Toggle — hidden on mobile since hamburger handles it */}
      <button
        onClick={onToggle}
        style={{ right: '-14px' }}
        className="hidden md:flex absolute top-[68px] z-50 items-center justify-center
                   w-7 h-7 rounded-full bg-amber-500 text-slate-900
                   hover:bg-amber-400 transition-colors shadow-lg border-2 border-slate-900"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed
          ? <ChevronRight size={13} strokeWidth={2.5} />
          : <ChevronLeft  size={13} strokeWidth={2.5} />}
      </button>

      {/* Logo */}
      <div
        className="flex items-center border-b border-slate-800 h-16 shrink-0 overflow-hidden"
        style={{ padding: collapsed ? '0 16px' : '0 20px', gap: collapsed ? 0 : '12px' }}
      >
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500 shrink-0">
          <Store size={16} className="text-slate-900" />
        </div>
        {!collapsed && (
          <div>
            <p className="text-white font-bold text-base leading-tight whitespace-nowrap">AISHA</p>
            <p className="text-amber-500 text-xs font-medium whitespace-nowrap">AI Sales Assistant</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-5 space-y-1 overflow-hidden">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavClick}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl font-medium transition-colors
               ${collapsed ? 'justify-center px-0 py-3' : 'px-4 py-3'}
               ${isActive
                 ? 'bg-amber-500 text-slate-900'
                 : 'text-slate-400 hover:text-white hover:bg-slate-800'}`
            }
          >
            <Icon size={20} className="shrink-0" />
            {!collapsed && <span className="text-sm whitespace-nowrap">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Business card */}
      {!collapsed && (
        <div className="mx-2 mb-2 px-3 py-3 rounded-xl bg-slate-800">
          {business ? (
            <>
              <p className="text-white text-sm font-semibold truncate">{business.business_name}</p>
              <p className="text-slate-400 text-xs truncate mt-0.5 capitalize">{business.business_type}</p>
              {business.whatsapp_phone_number && (
                <p className="text-amber-500 text-xs mt-1 truncate">{business.whatsapp_phone_number}</p>
              )}
            </>
          ) : (
            <p className="text-slate-500 text-xs">Start backend to load</p>
          )}
        </div>
      )}

      {/* Logout */}
      <div className="px-2 pb-4 border-t border-slate-800 pt-3">
        <button
          onClick={() => alert('AUTH NOTE: wire to Eve\'s JWT logout endpoint')}
          title={collapsed ? 'Log out' : undefined}
          className={`flex items-center gap-3 w-full rounded-xl py-3
                      text-slate-400 hover:text-red-400 hover:bg-slate-800
                      transition-colors text-sm font-medium
                      ${collapsed ? 'justify-center px-0' : 'px-4'}`}
        >
          <LogOut size={20} className="shrink-0" />
          {!collapsed && <span>Log out</span>}
        </button>
      </div>
    </aside>
  )
}