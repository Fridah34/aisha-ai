
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

import { AuthProvider, useAuth } from './hooks/useAuth';
import ProtectedRoute, { GuestRoute } from './components/ProtectedRoute';
import LoadingSpinner from './components/LoadingSpinner';
import { WebSocketProvider } from './context/WebSocketContext';

import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import BottomNav from './components/BottomNav';

// Pages
import Login from './pages/Login';
import Signup from './pages/Signup';
import Overview from './pages/Overview';
import Conversations from './pages/Conversations';
import Products from './pages/Products';
import Categories from './pages/Categories';
import Settings from './pages/Settings';

/**
 * ============================================================================
 * APP CONTENT ENGINE & ROUTING CHECKPOINTS
 * ============================================================================
 */

function AppContent() {
  const { isAuthenticated, loading } = useAuth();

  // Prevent UI flicker while validating token
  if (loading) {
    return <LoadingSpinner fullScreen />;
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={
          <GuestRoute>
            <Login />
          </GuestRoute>
        }
      />

      <Route
        path="/signup"
        element={
          <GuestRoute>
            <Signup />
          </GuestRoute>
        }
      />

      {/* Protected dashboard */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden">

              {/* Desktop sidebar */}
              <div className="hidden md:flex md:shrink-0">
                <Sidebar />
              </div>

              {/* Main content */}
              <div className="flex flex-col flex-1 min-w-0 overflow-hidden">

                <TopBar />

                <main className="flex-1 overflow-y-auto pb-16 md:pb-0">
                  <Routes>
                    <Route path="overview" element={<Overview />} />
                    <Route path="conversations" element={<Conversations />} />
                    <Route path="products" element={<Products />} />
                    <Route path="categories" element={<Categories />} />
                    <Route path="settings" element={<Settings />} />

                    {/* Dashboard fallback */}
                    <Route path="/" element={<Navigate to="/overview" replace />} />
                    <Route path="*" element={<Navigate to="/overview" replace />} />
                  </Routes>
                </main>

                {/* Mobile navigation */}
                <BottomNav />
              </div>
            </div>
          </ProtectedRoute>
        }
      />

      {/* Root redirect */}
      <Route path="/" element={<Navigate to={isAuthenticated ? "/overview" : "/login"} replace /> } />

     {/* Global fallback */}
      <Route path="*" element={<Navigate to={isAuthenticated ? "/overview" : "/login"} replace /> } />
    </Routes>
  )
}

/**
 * ============================================================================
 * ROOT APPLICATION
 * ============================================================================
 */

export default function App() {
  return (
    <AuthProvider>
      <WebSocketProvider>
        <Router>
          <AppContent />
        </Router>
      </WebSocketProvider>
    </AuthProvider>
  );
}