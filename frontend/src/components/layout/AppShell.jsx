/**
 * components/layout/AppShell.jsx — Authenticated layout wrapper.
 * Renders sidebar + scrollable main content area.
 */
import Sidebar from '../Sidebar'

export default function AppShell({ children }) {
  return (
    <div className="cl-app-shell">
      <Sidebar />
      <main className="cl-main-content">
        {children}
      </main>
    </div>
  )
}
