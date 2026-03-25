/**
 * pages/admin/UsersAdminPage.jsx — User management (admin only).
 */

import { useEffect, useState } from 'react'
import { authApi } from '../../api/client'

const S = {
  page:  { minHeight: '100vh', background: '#F8F7F4', fontFamily: 'Plus Jakarta Sans, system-ui, sans-serif' },
  main:  { maxWidth: 900, margin: '0 auto', padding: '2rem 1.5rem' },
  back:  { color: '#6b7280', fontSize: '0.875rem', textDecoration: 'none', display: 'inline-block', marginBottom: '1.25rem' },
  h1:    { fontSize: '1.4rem', fontWeight: 700, color: '#111827', marginBottom: '1.5rem' },
  table: { width: '100%', background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, borderCollapse: 'collapse', overflow: 'hidden' },
  th:    { padding: '10px 14px', textAlign: 'left', fontSize: '0.75rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', borderBottom: '1px solid #e5e7eb', background: '#f9fafb' },
  td:    { padding: '10px 14px', fontSize: '0.85rem', color: '#374151', borderBottom: '1px solid #f3f4f6' },
  badge: (role) => ({
    fontSize: '0.7rem',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 999,
    background: role === 'admin' ? '#dbeafe' : role === 'partner' ? '#ecfdf5' : '#f3f4f6',
    color:      role === 'admin' ? '#1e40af' : role === 'partner' ? '#065f46' : '#374151',
  }),
}

export default function UsersAdminPage() {
  const [users, setUsers]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    authApi.listUsers()
      .then((data) => setUsers(Array.isArray(data) ? data : data.users || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={S.page}>
      <main style={S.main}>
        <a href="/dashboard" style={S.back}>← Dashboard</a>
        <h1 style={S.h1}>User Management</h1>

        {loading && <p style={{ color: '#9ca3af' }}>Loading…</p>}
        {error   && <p style={{ color: '#ef4444' }}>Error: {error}</p>}

        {!loading && !error && (
          <table style={S.table}>
            <thead>
              <tr>
                {['ID', 'Email', 'Role', 'Active', 'Created'].map((h) => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr><td colSpan={5} style={{ ...S.td, textAlign: 'center', color: '#9ca3af' }}>No users</td></tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id}>
                    <td style={S.td}>{u.id}</td>
                    <td style={S.td}>{u.email}</td>
                    <td style={S.td}><span style={S.badge(u.role)}>{u.role}</span></td>
                    <td style={S.td}>{u.is_active ? '✓' : '✗'}</td>
                    <td style={S.td}>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </main>
    </div>
  )
}
