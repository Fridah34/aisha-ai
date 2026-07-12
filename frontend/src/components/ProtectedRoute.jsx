/**
 * ============================================================================
 * AISHA AI - SECURITY ROUTE GUARDS MODULE
 * ============================================================================
 * This file serves as the traffic controller for our application paths. It 
 * splits incoming traffic into private (Protected) and public (Guest) zones, 
 * preventing data exposure and handling user tracking histories automatically.
 * 
 * @module components/ProtectedRoute
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth'; // Importing our shared AuthContext box
import LoadingSpinner from './LoadingSpinner'; // Importing our cool loading spinner tool

// ============================================================================
// ROUTE GUARD 1: PROTECTED ROUTE (MEMBERS ONLY)
// ============================================================================
// This wraps pages that strictly require a user account (e.g., Dashboard, Chat History).
export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth(); // Read active user log-in status
  const location = useLocation(); // Remember exactly which page the user tried to visit

  // Step A: If the app is still fetching the security token from browser memory,
  // hold tight and show the beautiful full-screen loading spinner overlay.
  if (loading) return <LoadingSpinner fullScreen />;

  // Step B: If the app finishes checking and finds the user is NOT logged in...
  if (!isAuthenticated) {
    // Kick them out to the /login page, but secretly pass a note (`state={{ from: location }}`)
    // so the login page knows where they were trying to go!
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Step C: If they are safely logged in, let them slide through and view the private page!
  return children;
}

// ============================================================================
// ROUTE GUARD 2: GUEST ROUTE (ANONYMOUS VISITORS ONLY)
// ============================================================================
// This wraps pages meant ONLY for people who haven't logged in yet (e.g., Login or Register screens).
export function GuestRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  
  // Step A: If the app is busy checking login status, show the full-screen spinner.
  if (loading) return <LoadingSpinner fullScreen />;
  
  // Step B: If the user is ALREADY logged in, they shouldn't see the login page anymore!
  if (isAuthenticated) {
    // Automatically redirect them away from the login screen and forward them into the /overview dashboard.
    return <Navigate to="/overview" replace />;
  }
  
  // Step C: If they are a true guest (not logged in), let them view the Login/Register form safely.
  return children;
}
