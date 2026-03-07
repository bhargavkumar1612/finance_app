import { useState } from 'react';
import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

export default function TransactionConfirmCard({ payload, onAccept, onReject }: Props) {
    const [actionTaken, setActionTaken] = useState(false);

    const amount = payload.amount as number | undefined;
    const merchant = payload.merchant as string | undefined;
    const category = payload.category as string | undefined;
    const summary = payload.summary as string | undefined;
    const txDate = payload.transaction_date as string | undefined;

    return (
        <div className={`${styles.card} ${styles.confirmCard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>✓</span>
                <span className={styles.cardTitle}>Expense Recorded</span>
            </div>
            <div className={styles.confirmAmount}>
                ₹{amount !== undefined && amount !== null ? amount.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '—'}
            </div>
            <div className={styles.confirmDetails}>
                {merchant && (
                    <div className={styles.confirmRow}>
                        <span className={styles.confirmLabel}>Merchant</span>
                        <span className={styles.confirmValue}>{merchant}</span>
                    </div>
                )}
                {category && (
                    <div className={styles.confirmRow}>
                        <span className={styles.confirmLabel}>Category</span>
                        <span className={`badge badge-muted ${styles.confirmBadge}`}>{category}</span>
                    </div>
                )}
                {txDate && (
                    <div className={styles.confirmRow}>
                        <span className={styles.confirmLabel}>Date</span>
                        <span className={styles.confirmValue}>{txDate}</span>
                    </div>
                )}
            </div>
            {summary && <p className={styles.confirmSummary}>{summary}</p>}
            <div className={styles.confirmActions}>
                {!actionTaken ? (
                    <>
                        <button className="btn btn-success" onClick={() => { setActionTaken(true); onAccept?.(); }}>✓ Done</button>
                        <button className="btn btn-ghost" onClick={() => { setActionTaken(true); onReject?.(); }}>Add Another</button>
                    </>
                ) : (
                    <span style={{ opacity: 0.6, fontSize: '0.9rem' }}>Action recorded.</span>
                )}
            </div>
        </div>
    );
}
