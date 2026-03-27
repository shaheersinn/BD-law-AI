/**
 * pages/admin/UsersAdminPage.jsx — Digital Atelier user management.
 */

import { useEffect, useState } from 'react'
import AppShell from '../../components/layout/AppShell'
import { Skeleton } from '../../components/Skeleton'

const ROLE_COLORS = {
  admin:    { bg: 'var(--color-secondary-container)', color: 'var(--color-on-secondary-container)' },
  partner:  { bg: 'var(--color-secondary-container)', color: 'var(--color-on-secondary-container)' },
  associate:{ bg: 'var(--color-surface-container-high)', color: 'var(--color-on-surface-variant)' },
  readonly: { bg: 'var(--color-surface-container-high)', color: 'var(--color-on-surface-variant)' },
}

function RoleBadge({ role }) {
  const { bg, color } = ROLE_COLORS[role] || ROLE_COLORS.readonly
  return (
    <span style={{
      fontSize: '0.6875rem', fontWeight: 700, padding: '2px 8px',
      borderRadius: 'var(--radius-full)', background: bg, color,
      textTransform: 'uppercase', letterSpacing: '0.05em',
      fontFamily: 'var(--font-data)',
    }}>
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
    padding: '10px 16px',
    fontSize: '0.6875rem',
    fontWeight: 700,
    color: 'var(--color-on-surface-variant)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    textAlign: 'left',
    background: 'var(--color-surface-container-low)',
    fontFamily: 'var(--font-data)',
    whiteSpace: 'nowrap',
  }

  return (
    <AppShell>
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '2.5rem 2rem' }}>
        <h1 style={{
          fontFamily: 'var(--font-editorial)',
          fontWeight: 500,
          fontSize: '1.75rem',
          color: 'var(--color-primary)',
          marginBottom: '0.5rem',
          letterSpacing: '-0.01em',
        }}>
          User Management
        </h1>
        <p style={{
          color: 'var(--color-on-surface-variant)',
          fontSize: 13,
          marginBottom: '2rem',
          margin: '0 0 2rem',
          fontFamily: 'var(--font-data)',
        }}>
          All registered users and their access roles
        </p>

        {error && (
          <div style={{
            color: 'var(--color-error)',
            background: 'var(--color-error-bg)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            fontSize: 13,
            marginBottom: '1rem',
            fontFamily: 'var(--font-data)',
          }}>
            {error}
          </div>
        )}

        <div style={{
          background: 'var(--color-surface-container-lowest)',
          borderRadius: 'var(--radius-xl)',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-ambient)',
        }}>
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
                  <tr key={u.id || u.email} style={{
                    background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-container-low)',
                  }}>
                    <td style={{ padding: '10px 16px', fontSize: 13, color: 'var(--color-on-surface)', fontWeight: 600, fontFamily: 'var(--font-data)' }}>
                      {u.email}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                      <RoleBadge role={u.role} />
                    </td>
                    <td style={{ padding: '10px 16px', fontSize: 11, color: 'var(--color-on-surface-variant)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
                      {u.created_at ? new Date(u.created_at).toLocaleDateString('en-CA') : '—'}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                      <span style={{
                        fontSize: '0.6875rem', fontWeight: 700, padding: '2px 8px',
                        borderRadius: 'var(--radius-full)',
                        fontFamily: 'var(--font-data)',
                        ...(u.is_active !== false
                          ? { background: 'var(--color-success-bg)', color: 'var(--color-success)' }
                          : { background: 'var(--color-error-bg)', color: 'var(--color-error)' })
                      }}>
                        {u.is_active !== false ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                    <td style={{
                      padding: '10px 16px', textAlign: 'right',
                      fontFamily: 'var(--font-mono)', fontSize: 12,
                      color: u.failed_login_count > 0 ? 'var(--color-warning)' : 'var(--color-on-surface-variant)',
                    }}>
                      {u.failed_login_count ?? 0}
                    </td>
                  </tr>
                ))}
                {!users.length && (
                  <tr>
                    <td colSpan={5} style={{
                      padding: '3rem', textAlign: 'center',
                      color: 'var(--color-on-surface-variant)', fontSize: 13,
                      fontFamily: 'var(--font-data)',
                    }}>
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
