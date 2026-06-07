'use client';

import { Repeat } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

export default function RecurringBillConfirmCard({ payload, onAccept, onReject }: Props) {
    const name = (payload.name as string) ?? 'Bill';
    const amount = (payload.amount as number) ?? 0;
    const frequency = (payload.frequency as string) ?? 'monthly';
    const accountName = payload.account_name as string | undefined;
    const preview = payload.preview !== false;
    const summary = (payload.summary as string) ?? `Add ${name}?`;

    return (
        <div className={`${styles.card} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={Repeat} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>
                    {preview ? 'Confirm recurring bill' : 'Recurring bill added'}
                </span>
            </div>
            <p className={styles.cardSummary}>{summary}</p>
            <div className={styles.confirmDetails}>
                <div className={styles.confirmRow}>
                    <span className={styles.confirmLabel}>Name</span>
                    <span>{name}</span>
                </div>
                <div className={styles.confirmRow}>
                    <span className={styles.confirmLabel}>Amount</span>
                    <span className="amount-liability">
                        ₹{amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}/{frequency}
                    </span>
                </div>
                {accountName && (
                    <div className={styles.confirmRow}>
                        <span className={styles.confirmLabel}>Account</span>
                        <span>{accountName}</span>
                    </div>
                )}
            </div>
            {preview && onAccept && onReject && (
                <div className={styles.confirmActions}>
                    <button type="button" className="btn btn-primary" onClick={onAccept}>
                        Confirm
                    </button>
                    <button type="button" className="btn btn-ghost" onClick={onReject}>
                        Cancel
                    </button>
                </div>
            )}
        </div>
    );
}
