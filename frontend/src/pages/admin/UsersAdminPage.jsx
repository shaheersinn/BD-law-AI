/**
 * pages/admin/UsersAdminPage.jsx — ConstructLex Pro user management.
 */

import { useEffect, useState } from 'react'
import AppShell from '../../components/layout/AppShell'
import { Skeleton } from '../../components/Skeleton'

const ROLE_COLORS = {
  admin:    { bg: '#FEF3C7', color: '#92400E' },
  partner:  { bg: 'var(--accent-light)', color: 'var(--accent-dark)' },
  associate:{ bg: 'var(--surface-raised)', color: 'var(--text-secondary)' },
  readonly: { bg: 'var(--surface-raised)', color: 'var(--text-tertiary)' },
}

function RoleBadge({ role }) {
  const { bg, color } = ROLE_COLORS[role] || ROLE_COLORS.readonly
  return (
    <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 999, background: bg, color, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
      {role}
    </span>
  )
}

export default function UsersAdminPage() {
  const [users,   setUsers]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    fetch('/api/v1/auth/users', {
      headers: { Authorization: `Bearer ${sessionStorage.getItem('oracle_token')}` },
    })
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
      .then(d => setUsers(Array.isArray(d) ? d : d.users || []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const thStyle = {
    padding: '9px 16px', fontSize: 10, fontWeight: 600,
    color: 'var(--text-tertiary)', textTransform: 'uppercase',
    letterSpacing: '0.08em', textAlign: 'left',
    background: 'var(--surface-raised)', border: 'none',
    borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap',
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 30, color: 'var(--text)', marginBottom: '0.5rem' }}>
          User Management
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: '2rem', margin: '0 0 2rem' }}>
          All registered users and their access roles
        </p>

        {error && (
          <div style={{ color: 'var(--error)', background: 'var(--error-bg)', border: '1px solid var(--error)', borderRadius: 'var(--radius-md)', padding: '10px 14px', fontSize: 13, marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
          {loading ? (
            <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={40} />)}
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={thStyle}>Email</th>
                  <th style={{ ...thStyle, textAlign: 'center' }}>Role</th>
                  <th style={{ ...thStyle }}>Created</th>
                  <th style={{ ...thStyle, textAlign: 'center' }}>Status</th>
                  <th style={{ ...thStyle, textAlign: 'right' }}>Lockout Count</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <tr key={u.id || u.email} style={{ borderBottom: '1px solid var(--surface-raised)', background: i % 2 === 0 ? 'transparent' : 'var(--surface-raised)' }}>
                    <td style={{ padding: '10px 16px', fontSize: 13, color: 'var(--text)', fontWeight: 500 }}>
                      {u.email}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                      <RoleBadge role={u.role} />
                    </td>
                    <td style={{ padding: '10px 16px', fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                      {u.created_at ? new Date(u.created_at).toLocaleDateString('en-CA') : '—'}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                      <span style={{
                        fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                        ...(u.is_active !== false
                          ? { background: 'var(--success-bg)', color: 'var(--success)' }
                          : { background: 'var(--error-bg)', color: 'var(--error)' })
                      }}>
                        {u.is_active !== false ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: u.failed_login_count > 0 ? 'var(--warning)' : 'var(--text-tertiary)' }}>
                      {u.failed_login_count ?? 0}
                    </td>
                  </tr>
                ))}
                {!users.length && (
                  <tr>
                    <td colSpan={5} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppShell>
  )
}
