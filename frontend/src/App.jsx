/**
 * ============================================================================
 * AISHA AI - MAIN APPLICATION ROUTER ENTRYPOINT
 * ============================================================================
 * This is the master coordinator of the frontend app. It manages application-wide
 * initializations, wraps child components inside the AuthProvider token box,
 * and builds a fully responsive layout framework containing global navigation guards.
 * 
 * @module App
 */

import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth'
import ProtectedRoute, { GuestRoute } from './components/ProtectedRoute'
import LoadingSpinner from './components/LoadingSpinner'

import Sidebar    from './components/Sidebar'
import TopBar     from './components/TopBar'
import BottomNav  from './components/BottomNav'

// Pages
import Login from './pages/Login'
import Signup from './pages/Signup'
import Overview      from './pages/Overview'
import Conversations from './pages/Conversations'
import KnowledgeBase from './pages/KnowledgeBase'
import Products      from './pages/Products'
import Settings      from './pages/Settings'

/**
 * ============================================================================
 * TOPIC 1: APP CONTENT ENGINE & ROUTING CHECKPOINTS
 * ============================================================================
 * AppContent manages the global routing grid, security checkpoints,
 * and structural layout scaling based on screen size.
 */

function AppContent() {
  const {isAuthenticated, loading} = useAuth()

  //gatekeeper: Prevents UI flickering while validating token on refresh
  if (loading) {
    return <LoadingSpinner fullScreen />;
  }
  
  return (
    <Routes>
      <Route path="/login" element={<GuestRoute><Login /></GuestRoute>} />
      <Route path="/signup" element={<GuestRoute><Signup /></GuestRoute>} />

      {/* SECURE DASHBOARD PLATFORM ROUTES */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden">
              {/* ── Desktop sidebar — hidden below md ── */}
              <div className="hidden md:flex md:shrink-0">
                <Sidebar />
              </div>

              {/* ── Right side: topbar + scrollable content + mobile bottom nav ── */}
              <div className="flex flex-col flex-1 min-w-0 overflow-hidden">

                <TopBar />

                {/* Page content — scrolls independently */}
                <main className="flex-1 overflow-y-auto pb-16 md:pb-0">
                  <Routes>
                    <Route path="overview" element={<Overview />} />
                    <Route path="conversations" element={<Conversations />} />
                    <Route path="products" element={<Products />} />
                    <Route path="knowledge-base" element={<KnowledgeBase />} />
                    <Route path="settings" element={<Settings />} />
                    {/*catch-all fallback framework for  broken inside-dashboard links*/}
                    <Route path="/*" element={<Navigate to="/overview" replace />} />
                    <Route path="*" element={<Navigate to="/overview" replace />} />
                  </Routes>
                </main>

                {/* ── Mobile bottom nav — hidden on md+ ── */}
                <BottomNav />
              </div>
            </div>
          </ProtectedRoute>
        }
      />

      {/*Top levelnavigation navigation TRiggers (optimized Route for Cascade Fallback)*/}
      <Route path="/" element={<Navigate to={isAuthenticated ? "/overview" : "/login"} replace />} />
      <Route path="*" element={<Navigate to={isAuthenticated ? "/overview" : "/login"} replace />} />
    </Routes>
  )
}

/**
 * ============================================================================
 * TOPIC 2: MASTER ROOT INITIALIZATION
 * ============================================================================
 * Establishes the core data state provider box and browser navigation context.
 */

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
}
    
