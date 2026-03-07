'use client';
import { useEffect, useState } from 'react';
import { getAccounts, type Account } from '@/lib/api';

export default function AccountsPage() {
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getAccounts().then(data => {
            setAccounts(data);
            setLoading(false);
        }).catch(err => {
            console.error(err);
            setLoading(false);
        });
    }, []);

    return (
        <div style={{ padding: '28px 32px', maxWidth: 900 }}>
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: 4 }}>Accounts</h1>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Manage your bank accounts and credit cards</p>
            </div>

            {loading ? (
                <div className="spinner" />
            ) : accounts.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 48 }}>
                    <p className="text-muted">No accounts found. Use the chat to add one.</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {accounts.map(acc => (
                        <div key={acc.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>{acc.name}</h3>
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                    {acc.institution} · {acc.account_type}
                                </p>
                            </div>
                            <span className="badge badge-muted">Active</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
