import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Overview from './pages/Overview'
import Conversations from './pages/Conversations'
import Products from './pages/Products'
import Settings from './pages/Settings'

export default function App() {
  const [collapsed, setCollapsed ] = useState(false)
  const [mobileOpen, setMobileOpen ] = useState(false)

  //Auto-collapse sidebar on small Screens
  useEffect(() => {
    function handleResize() {
      if (window.innerWidth < 768) {
        setCollapsed(true)
        setMobileOpen(false)
      } else {
        setMobileOpen(false)
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <BrowserRouter>
      <div className="flex h-screen bg-slate-50 overflow-hidden">

        {/* Mobile overlay backdrop */}
        {mobileOpen && (
          <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={() => setMobileOpen(false)}
          />
        )}
        {/* sidebar -on mobile it slides in over content*/}
        <div className={`fixed md:relative inset-y-0 left-0 z-30 h-screen transition-transform duration-300 ease-in-out
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0 md:flex md:shrink-0
        `}>

        <Sidebar
           collapsed= {collapsed} 
           onToggle={() => setCollapsed(prev => !prev)}
           onNavClick={() => setMobileOpen(false)}
          
          />
          </div>
        {/* Right side: topbar + page content*/}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <TopBar onHamburger={() => setMobileOpen(prev => !prev)}
           />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<Navigate to="/overview" replace />} />
              <Route path="/overview" element={<Overview />} />
              <Route path="/conversations" element={<Conversations />} />
              <Route path="/products" element={<Products />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>

      </div>
    </BrowserRouter>
  )
}