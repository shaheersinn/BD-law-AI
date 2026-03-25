/**
 * components/PrivateRoute.jsx
 *
 * Wraps routes that require authentication.
 * Redirects to /login if no token is present.
 * Optionally restricts to a specific role (adminOnly).
 */

import { Navigate } from 'react-router-dom'
import useAuthStore from '../stores/auth'

export default function PrivateRoute({ children, adminOnly = false }) {
  const { token, user } = useAuthStore()

  if (!token) {
    return <Navigate to="/login" replace />
  }

  if (adminOnly && user && user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
