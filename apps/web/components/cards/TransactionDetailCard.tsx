'use client';
import { List } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';

interface TxnItem {
    id?: string;
    date?: string;
    merchant?: string;
    category?: string;
    amount?: number;
    nw_impact?: string;
}

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

function amountClass(amount: number): string {
    return amount < 0 ? 'amount-liability' : 'amount-asset';
}

export default function TransactionDetailCard({ payload }: Props) {
    const transactions = (payload.transactions as TxnItem[]) ?? [];
    const msg = (payload.message as string) ?? '';

    return (
        <div className={`${styles.card} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={List} size={18} color="var(--primary)" />
                </span>
                <span className={styles.cardTitle}>Transaction detail</span>
            </div>

            {transactions.length === 0 && (
                <p style={{ color: 'var(--text-secondary)' }}>{msg || 'No transactions found.'}</p>
            )}

            {transactions.length > 0 && (<>

            {msg && <p style={{ marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{msg}</p>}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {transactions.map((t, i) => (
                    <div
                        key={t.id ?? i}
                        style={{
                            padding: '0.5rem 0.75rem',
                            background: 'var(--surface-raised)',
                            borderRadius: 'var(--radius-sm)',
                        }}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                            <span style={{ fontWeight: 600 }}>{t.merchant ?? 'Unknown'}</span>
                            <span className={amountClass(t.amount ?? 0)}>
                                {t.amount != null
                                    ? `${t.amount < 0 ? '−' : '+'}₹${Math.abs(t.amount).toLocaleString('en-IN')}`
                                    : '—'}
                            </span>
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.25rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                            {t.date && <span>{t.date}</span>}
                            {t.category && (
                                <span className="badge badge-muted">{t.category}</span>
                            )}
                            {t.nw_impact && (
                                <span className="badge badge-muted">{t.nw_impact}</span>
                            )}
                        </div>
                    </div>
                ))}
            </div>
            </>)}
        </div>
    );
}
