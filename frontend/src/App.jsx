import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar    from './components/Sidebar'
import TopBar     from './components/TopBar'
import BottomNav  from './components/BottomNav'
import Overview      from './pages/Overview'
import Conversations from './pages/Conversations'
import Products      from './pages/Products'
import Settings      from './pages/Settings'

/**
 * Layout:
 *   Desktop (md+) → left sidebar always expanded + topbar + page content
 *   Mobile  (<md) → topbar + page content + bottom nav bar
 *
 * No collapsed/hamburger state needed — the two layouts are fully separate.
 * Sidebar never appears on mobile; BottomNav never appears on desktop.
 */
export default function App() {
  return (
    <BrowserRouter>
      {/* Outer shell — full viewport, no scroll */}
      <div className="flex h-screen bg-slate-50 overflow-hidden">

        {/* ── Desktop sidebar — hidden below md ── */}
        <div className="hidden md:flex md:shrink-0">
          <Sidebar />
        </div>

        {/* ── Right side: topbar + scrollable content + mobile bottom nav ── */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">

          <TopBar />

          {/* Page content — scrolls independently */}
          <main className="flex-1 overflow-y-auto pb-16 md:pb-0">
            {/*
              pb-16 on mobile adds bottom padding so content is never
              hidden behind the fixed bottom nav bar (h-16 = 64px).
              md:pb-0 removes it on desktop where there is no bottom nav.
            */}
            <Routes>
              <Route path="/"              element={<Navigate to="/overview" replace />} />
              <Route path="/overview"      element={<Overview />} />
              <Route path="/conversations" element={<Conversations />} />
              <Route path="/products"      element={<Products />} />
              <Route path="/settings"      element={<Settings />} />
            </Routes>
          </main>

          {/* ── Mobile bottom nav — hidden on md+ ── */}
          <BottomNav />
        </div>

      </div>
    </BrowserRouter>
  )
}