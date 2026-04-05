/**
 * pages/admin/UsersAdminPage.jsx — Admin UI Update
 * Digital Atelier user management.
 * Applied strict DM typography and injected CSS.
 */

import { useEffect, useState } from 'react'
import AppShell from '../../components/layout/AppShell'
import { Skeleton } from '../../components/Skeleton'

const USERS_CSS = `
.usr-root {
  max-width: 900px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
}
.usr-title {
  font-family: var(--font-editorial);
  font-weight: 500;
  font-size: 1.75rem;
  color: var(--color-primary);
  margin-bottom: 0.5rem;
  margin-top: 0;
  letter-spacing: -0.01em;
}
.usr-subtitle {
  color: var(--color-on-surface-variant);
  font-size: 0.8125rem;
  margin-bottom: 2rem;
  margin-top: 0;
  font-family: var(--font-data);
}
.usr-error {
  color: var(--color-error);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 0.8125rem;
  margin-bottom: 1rem;
  font-family: var(--font-data);
}
.usr-card {
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-ambient);
}

.usr-table {
  width: 100%;
  border-collapse: collapse;
}
.usr-th {
  padding: 10px 16px;
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-align: left;
  background: var(--color-surface-container-low);
  font-family: var(--font-data);
  white-space: nowrap;
}
.usr-tr {
  transition: background var(--transition-fast);
}
.usr-td {
  padding: 10px 16px;
  font-size: 0.8125rem;
  color: var(--color-on-surface);
  font-weight: 600;
  font-family: var(--font-data);
}
.usr-td-center {
  text-align: center;
}
.usr-td-right {
  text-align: right;
}
.usr-td-mono {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  color: var(--color-on-surface-variant);
  white-space: nowrap;
}

.usr-badge {
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-family: var(--font-data);
}
`
function injectCSS() {
  if (typeof document !== 'undefined' && !document.getElementById('usr-styles')) {
    const el = document.createElement('style')
    el.id = 'usr-styles'
    el.textContent = USERS_CSS
    document.head.appendChild(el)
  }
}

const ROLE_COLORS = {
  admin:    { bg: 'var(--color-secondary-container)', color: 'var(--color-on-secondary-container)' },
  partner:  { bg: 'var(--color-secondary-container)', color: 'var(--color-on-secondary-container)' },
  associate:{ bg: 'var(--color-surface-container-high)', color: 'var(--color-on-surface-variant)' },
  readonly: { bg: 'var(--color-surface-container-high)', color: 'var(--color-on-surface-variant)' },
}

function RoleBadge({ role }) {
  const { bg, color } = ROLE_COLORS[role] || ROLE_COLORS.readonly
  return (
    <span className="usr-badge" style={{ background: bg, color }}>
      {role}
    </span>
  )
}

export default function UsersAdminPage() {
  injectCSS()
  const [users,   setUsers]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    fetch('/api/auth/users', {
      headers: { Authorization: \`Bearer \${sessionStorage.getItem('bdforlaw_token')}\` },
    })
      .then(r => { if (!r.ok) throw new Error(\`\${r.status}\`); return r.json() })
      .then(d => setUsers(Array.isArray(d) ? d : d.users || []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <AppShell>
      <div className="usr-root">
        <h1 className="usr-title">User Management</h1>
        <p className="usr-subtitle">All registered users and their access roles</p>

        {error && <div className="usr-error">{error}</div>}

        <div className="usr-card">
          {loading ? (
            <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={40} />)}
            </div>
          ) : (
            <table className="usr-table">
              <thead>
                <tr>
                  <th className="usr-th">Email</th>
                  <th className="usr-th usr-td-center">Role</th>
                  <th className="usr-th">Created</th>
                  <th className="usr-th usr-td-center">Status</th>
                  <th className="usr-th usr-td-right">Lockout Count</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, i) => (
                  <tr key={u.id || u.email} className="usr-tr" style={{ background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-container-low)' }}>
                    <td className="usr-td">{u.email}</td>
                    <td className="usr-td usr-td-center"><RoleBadge role={u.role} /></td>
                    <td className="usr-td usr-td-mono">{u.created_at ? new Date(u.created_at).toLocaleDateString('en-CA') : '—'}</td>
                    <td className="usr-td usr-td-center">
                      <span className="usr-badge" style={{ ...(u.is_active !== false ? { background: 'var(--color-success-bg)', color: 'var(--color-success)' } : { background: 'var(--color-error-bg)', color: 'var(--color-error)' }) }}>
                        {u.is_active !== false ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                    <td className="usr-td usr-td-right" style={{ fontFamily: 'var(--font-mono)', color: u.failed_login_count > 0 ? 'var(--color-warning)' : 'var(--color-on-surface-variant)' }}>
                      {u.failed_login_count ?? 0}
                    </td>
                  </tr>
                ))}
                {!users.length && (
                  <tr>
                    <td colSpan={5} style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-on-surface-variant)', fontSize: 13, fontFamily: 'var(--font-data)' }}>
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
