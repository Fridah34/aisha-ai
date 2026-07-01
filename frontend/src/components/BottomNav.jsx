import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, Package, Settings,
} from 'lucide-react'

const tabs = [
  { to: '/overview',      label: 'Dashboard',      icon: LayoutDashboard },
  { to: '/conversations', label: 'Conversations',  icon: MessageSquare },
  { to: '/products',      label: 'Products',       icon: Package },
  { to: '/settings',      label: 'Settings',       icon: Settings },
]

/**
 * Mobile-only bottom navigation bar.
 * Mounted in App.jsx and hidden on md+ via `md:hidden`.
 * Fixed to the bottom of the viewport so it never scrolls away.
 *
 * Why fixed and not sticky?
 *   sticky only works relative to a scroll container. Since the main content
 *   area scrolls independently (flex-1 overflow-y-auto), sticky on a sibling
 *   element would not follow it. fixed pins to the viewport regardless of
 *   any scroll container — which is exactly what a tab bar needs.
 */
export default function BottomNav() {
  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-40
                 bg-white border-t border-slate-200
                 flex items-stretch h-16"
    >
      {tabs.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center justify-center gap-0.5
             text-[10px] font-medium transition-colors
             ${isActive
               ? 'text-slate-900'
               : 'text-slate-400 hover:text-slate-600'}`
          }
        >
          {({ isActive }) => (
            <>
              {/* Icon — active gets filled amber pill background */}
              <div
                className={`flex items-center justify-center w-10 h-6 rounded-full
                             transition-colors
                             ${isActive ? 'bg-amber-500' : ''}`}
              >
                <Icon
                  size={18}
                  className={isActive ? 'text-slate-900' : 'text-slate-400'}
                  strokeWidth={isActive ? 2.5 : 1.8}
                />
              </div>
              {/* Label */}
              <span className={isActive ? 'text-slate-800' : ''}>
                {label}
              </span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}