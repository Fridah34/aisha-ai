import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, Package,
  BookOpen, Settings, LogOut, Store,ShoppingCart, ShoppingBag,
} from 'lucide-react'
import { getSettings } from '../api/settings'
import { useAuth } from '../hooks/useAuth'

const links = [
  { to: '/overview',      label: 'Overview',      icon: LayoutDashboard },
  { to: '/conversations', label: 'Conversations', icon: MessageSquare },
  { to: '/products',      label: 'Products',      icon: Package },
  { to: '/categories',      label: 'Categories',      icon: ShoppingBag },
  { to: '/orders',      label: 'Orders',      icon: ShoppingCart },
  { to: '/knowledge-base', label: 'Knowledge Base', icon: BookOpen },
  { to: '/settings',      label: 'Settings',      icon: Settings },
]

/**
 * Desktop-only sidebar — always fully expanded, no collapse toggle.
 * This component is mounted inside a `hidden md:flex` wrapper in App.jsx,
 * so it is never rendered on mobile at all.
 */
export default function Sidebar() {
  const [business, setBusiness] = useState(null)
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  useEffect(() => {
    getSettings().then(setBusiness).catch(() => setBusiness(null))
  }, [])

  const handleLogoutClick = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <aside className="flex flex-col w-60 bg-slate-900 border-r border-slate-800 h-screen shrink-0">

      {/* ── Logo / brand ── */}
      <div className="flex items-center gap-3 h-16 px-5 border-b border-slate-800 shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500 shrink-0">
          <Store size={16} className="text-slate-900" />
        </div>
        <div>
          <p className="text-white font-bold text-base leading-tight">AISHA AI </p>
          <p className="text-amber-500 text-xs font-medium">AI Sales Assistant</p>
        </div>
      </div>

      {/* ── Navigation links ── */}
      <nav className="flex-1 px-2 py-5 space-y-1 overflow-hidden">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
               transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-inset
               ${isActive
                 ? 'bg-amber-500 text-slate-900'
                 : 'text-slate-400 hover:text-white hover:bg-slate-800'}`
            }
          >
            <Icon size={20} className="shrink-0" />
            <span className="whitespace-nowrap">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* ── Business info card ── */}
      <div className="mx-2 mb-2 px-3 py-3 rounded-xl bg-slate-800">
        {business ? (
          <>
            <p className="text-white text-sm font-semibold truncate">
              {business.business_name}
            </p>
            <p className="text-slate-400 text-xs truncate mt-0.5 capitalize">
              {business.business_type}
            </p>
            {business.whatsapp_phone_number && (
              <p className="text-amber-500 text-xs mt-1 truncate">
                {business.whatsapp_phone_number}
              </p>
            )}
          </>
        ) : (
          <>
            <p className="text-white text-sm font-semibold truncate">
              {user?.name || 'Active User'}
            </p>
            <p className="text-slate-400 text-xs truncate mt-0.5">
              {user?.email || 'Loading business data...'}
            </p>
          </>
        )}
      </div>

      {/* ── Logout ── */}
      <div className="px-2 pb-4 border-t border-slate-800 pt-3">
        <button
          onClick={handleLogoutClick}
          className="flex items-center gap-3 w-full px-4 py-3 rounded-xl
                     text-slate-400 hover:text-red-400 hover:bg-slate-800
                     transition-colors text-sm font-medium"
        >
          <LogOut size={20} className="shrink-0" />
          <span>Log out</span>
        </button>
      </div>
    </aside>
  )
}