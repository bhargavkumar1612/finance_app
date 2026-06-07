'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import {
    AdminStats,
    AdminUser,
    PasswordResetItem,
    approveUser,
    deleteUser,
    disableUser,
    enableUser,
    getAdminStats,
    getAdminUsers,
    getPasswordResets,
    getPendingSignups,
    rejectUser,
    resolvePasswordReset,
} from '@/lib/api';
import styles from './page.module.css';

function statusBadge(status: string): string {
    switch (status) {
        case 'approved':
            return 'badge badge-success';
        case 'pending':
            return 'badge badge-warning';
        case 'rejected':
            return 'badge badge-danger';
        case 'disabled':
            return 'badge badge-muted';
        default:
            return 'badge badge-neutral';
    }
}

export default function AdminPage() {
    const { user, isLoading } = useAuth();
    const router = useRouter();

    const [stats, setStats] = useState<AdminStats | null>(null);
    const [pending, setPending] = useState<AdminUser[]>([]);
    const [resets, setResets] = useState<PasswordResetItem[]>([]);
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [userTotal, setUserTotal] = useState(0);
    const [userQuery, setUserQuery] = useState('');
    const queryRef = useRef('');
    const [error, setError] = useState('');
    const [loadingData, setLoadingData] = useState(true);

    // Inline password-reset resolution state
    const [resolvingId, setResolvingId] = useState<string | null>(null);
    const [newPw, setNewPw] = useState('');
    const [issuedPw, setIssuedPw] = useState<{ username: string; password: string } | null>(null);

    const isSuperAdmin = user?.role === 'super_admin';

    const loadUsers = useCallback(async (q: string) => {
        const res = await getAdminUsers(100, 0, q);
        setUsers(res.users);
        setUserTotal(res.total);
    }, []);

    const refresh = useCallback(async () => {
        setError('');
        try {
            const [s, p, r] = await Promise.all([
                getAdminStats(),
                getPendingSignups(),
                getPasswordResets(),
            ]);
            setStats(s);
            setPending(p);
            setResets(r);
            await loadUsers(queryRef.current); // preserve any active search
        } catch (err: any) {
            setError(err.message || 'Failed to load admin data');
        } finally {
            setLoadingData(false);
        }
    }, [loadUsers]);

    const doSearch = useCallback(
        (q: string) => {
            queryRef.current = q;
            loadUsers(q).catch((err: any) => setError(err.message || 'Search failed'));
        },
        [loadUsers],
    );

    // Redirect non-admins once auth has resolved.
    useEffect(() => {
        if (!isLoading && user && !isSuperAdmin) {
            router.replace('/chat');
        }
    }, [isLoading, user, isSuperAdmin, router]);

    useEffect(() => {
        if (isSuperAdmin) refresh();
    }, [isSuperAdmin, refresh]);

    const runAction = async (fn: () => Promise<unknown>) => {
        setError('');
        try {
            await fn();
            await refresh();
        } catch (err: any) {
            setError(err.message || 'Action failed');
        }
    };

    const handleDelete = (u: AdminUser) => {
        if (
            window.confirm(
                `Permanently delete "${u.username}" and ALL their financial data? This cannot be undone.`,
            )
        ) {
            runAction(() => deleteUser(u.id));
        }
    };

    const handleResolveReset = async (item: PasswordResetItem) => {
        setError('');
        if (newPw.length < 8) {
            setError('New password must be at least 8 characters');
            return;
        }
        try {
            const res = await resolvePasswordReset(item.id, newPw);
            setIssuedPw({ username: res.username, password: res.new_password });
            setResolvingId(null);
            setNewPw('');
            await refresh();
        } catch (err: any) {
            setError(err.message || 'Failed to set password');
        }
    };

    if (isLoading || (user && !isSuperAdmin)) {
        return <div className={styles.loading}>Loading…</div>;
    }
    if (!user) return null;

    return (
        <div className={styles.page}>
            <h1 className={styles.title}>Admin</h1>
            {error && <div className={styles.error}>{error}</div>}

            {/* Stats */}
            <div className={styles.statsRow}>
                <div className="card">
                    <div className={styles.statLabel}>Users</div>
                    <div className={styles.statValue} id="admin-user-count">{stats?.user_count ?? '—'}</div>
                </div>
                <div className="card">
                    <div className={styles.statLabel}>Pending signups</div>
                    <div className={styles.statValue}>{stats?.pending_signups ?? '—'}</div>
                </div>
                <div className="card">
                    <div className={styles.statLabel}>Password resets</div>
                    <div className={styles.statValue}>{stats?.pending_resets ?? '—'}</div>
                </div>
            </div>

            {/* Issued password banner (shown once) */}
            {issuedPw && (
                <div className={styles.issued}>
                    New password for <strong>{issuedPw.username}</strong>:{' '}
                    <code className={styles.code}>{issuedPw.password}</code> — copy and share it offline.
                    <button className="btn btn-ghost" onClick={() => setIssuedPw(null)}>Dismiss</button>
                </div>
            )}

            {/* Pending signups */}
            <section className={styles.section} id="admin-pending-signups">
                <h2 className={styles.sectionTitle}>Pending signups</h2>
                {pending.length === 0 ? (
                    <p className={styles.empty}>No pending signups.</p>
                ) : (
                    <table className={styles.table}>
                        <thead>
                            <tr><th>Username</th><th>Requested</th><th></th></tr>
                        </thead>
                        <tbody>
                            {pending.map((u) => (
                                <tr key={u.id}>
                                    <td>{u.username}</td>
                                    <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                                    <td className={styles.actions}>
                                        <button
                                            className="btn btn-success"
                                            data-testid="approve-user"
                                            onClick={() => runAction(() => approveUser(u.id))}
                                        >
                                            Approve
                                        </button>
                                        <button className="btn btn-danger" onClick={() => runAction(() => rejectUser(u.id))}>
                                            Reject
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>

            {/* Password resets */}
            <section className={styles.section} id="admin-password-resets">
                <h2 className={styles.sectionTitle}>Password reset queue</h2>
                {resets.length === 0 ? (
                    <p className={styles.empty}>No open reset requests.</p>
                ) : (
                    <table className={styles.table}>
                        <thead>
                            <tr><th>Username</th><th>Requested</th><th></th></tr>
                        </thead>
                        <tbody>
                            {resets.map((item) => (
                                <tr key={item.id}>
                                    <td>{item.username}</td>
                                    <td>{item.requested_at ? new Date(item.requested_at).toLocaleDateString() : '—'}</td>
                                    <td className={styles.actions}>
                                        {resolvingId === item.id ? (
                                            <>
                                                <input
                                                    className={styles.input}
                                                    type="text"
                                                    placeholder="New password"
                                                    value={newPw}
                                                    onChange={(e) => setNewPw(e.target.value)}
                                                />
                                                <button className="btn btn-primary" onClick={() => handleResolveReset(item)}>
                                                    Save
                                                </button>
                                                <button
                                                    className="btn btn-ghost"
                                                    onClick={() => { setResolvingId(null); setNewPw(''); }}
                                                >
                                                    Cancel
                                                </button>
                                            </>
                                        ) : (
                                            <button className="btn btn-primary" onClick={() => setResolvingId(item.id)}>
                                                Set password
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>

            {/* All users */}
            <section className={styles.section} id="admin-users">
                <h2 className={styles.sectionTitle}>Users</h2>
                <div className={styles.searchRow}>
                    <input
                        id="admin-user-search"
                        className={styles.input}
                        type="text"
                        placeholder="Search by username…"
                        value={userQuery}
                        onChange={(e) => setUserQuery(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') doSearch(userQuery); }}
                    />
                    <button className="btn btn-primary" onClick={() => doSearch(userQuery)}>Search</button>
                    {queryRef.current && (
                        <button
                            className="btn btn-ghost"
                            onClick={() => { setUserQuery(''); doSearch(''); }}
                        >
                            Clear
                        </button>
                    )}
                </div>
                {!loadingData && (
                    <div className={styles.tableMeta}>
                        Showing {users.length} of {userTotal}
                        {queryRef.current ? ` matching “${queryRef.current}”` : ' users'}
                    </div>
                )}
                {loadingData ? (
                    <p className={styles.empty}>Loading…</p>
                ) : (
                    <table className={styles.table}>
                        <thead>
                            <tr><th>Username</th><th>Role</th><th>Status</th><th></th></tr>
                        </thead>
                        <tbody>
                            {users.map((u) => (
                                <tr key={u.id}>
                                    <td>{u.username}</td>
                                    <td>{u.role === 'super_admin' ? 'Super admin' : 'User'}</td>
                                    <td><span className={statusBadge(u.status)}>{u.status}</span></td>
                                    <td className={styles.actions}>
                                        {u.id === user.id ? (
                                            <span className={styles.you}>You</span>
                                        ) : (
                                            <>
                                                {u.status === 'disabled' ? (
                                                    <button className="btn btn-success" onClick={() => runAction(() => enableUser(u.id))}>
                                                        Enable
                                                    </button>
                                                ) : (
                                                    <button className="btn btn-ghost" onClick={() => runAction(() => disableUser(u.id))}>
                                                        Disable
                                                    </button>
                                                )}
                                                <button className="btn btn-danger" onClick={() => handleDelete(u)}>
                                                    Delete
                                                </button>
                                            </>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>
        </div>
    );
}
