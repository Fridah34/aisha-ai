import { NavLink } from 'react-router-dom'
import { LayoutDashboard, MessageSquare, Package, Settings } from 'lucide-react'

const links = [
  { to: '/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/conversations', label: 'Conversations', icon: MessageSquare },
  { to: '/products', label: 'Products', icon: Package },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <aside className="w-60 bg-slate-900 flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-slate-800">
        <span className="text-amber-500 font-bold text-lg tracking-wide">AISHA</span>
        <p className="text-slate-400 text-xs mt-0.5">Sales Assistant</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-amber-500 text-slate-900'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-800">
        <p className="text-slate-500 text-xs">Zawadi Boutique</p>
        <p className="text-slate-600 text-xs">test@zawadi.com</p>
      </div>
    </aside>
  )
}