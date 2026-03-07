'use client';
import { useEffect, useState } from 'react';
import { getTransactions, type Transaction } from '@/lib/api';

export default function TransactionsPage() {
    const [txns, setTxns] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getTransactions().then(data => {
            setTxns(data);
            setLoading(false);
        }).catch(err => {
            console.error(err);
            setLoading(false);
        });
    }, []);

    return (
        <div style={{ padding: '28px 32px', maxWidth: 1000 }}>
            <div style={{ marginBottom: 24 }}>
                <h1 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: 4 }}>Transactions</h1>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Your unified ledger</p>
            </div>

            {loading ? (
                <div className="spinner" />
            ) : txns.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 48 }}>
                    <p className="text-muted">No transactions found. Try importing a statement.</p>
                </div>
            ) : (
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                        <thead>
                            <tr>
                                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontWeight: 500, background: 'var(--bg-elevated)' }}>Date</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontWeight: 500, background: 'var(--bg-elevated)' }}>Merchant</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontWeight: 500, background: 'var(--bg-elevated)' }}>Category</th>
                                <th style={{ padding: '12px 16px', textAlign: 'right', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontWeight: 500, background: 'var(--bg-elevated)' }}>Amount</th>
                                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', fontWeight: 500, background: 'var(--bg-elevated)' }}>Source</th>
                            </tr>
                        </thead>
                        <tbody>
                            {txns.map(tx => (
                                <tr key={tx.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                    <td style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>{tx.transaction_date}</td>
                                    <td style={{ padding: '12px 16px', fontWeight: 500 }}>{tx.merchant || '—'}</td>
                                    <td style={{ padding: '12px 16px' }}><span className="badge badge-muted" style={{ fontSize: '0.7rem' }}>{tx.category || 'uncategorized'}</span></td>
                                    <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: tx.amount < 0 ? 'var(--danger)' : 'var(--success)' }}>
                                        ₹{Math.abs(tx.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                    </td>
                                    <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>{tx.source}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
