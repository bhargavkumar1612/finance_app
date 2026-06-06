'use client';
import styles from './Card.module.css';
import cardStyles from './TransactionConfirmCard.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

export default function TransactionConfirmCard({ payload, onAccept, onReject }: Props) {
    const amount = Math.abs((payload.amount as number) ?? 0);
    const merchant = (payload.merchant as string) ?? '';
    const category = (payload.category as string) ?? '';
    const date = (payload.transaction_date as string) ?? '';
    const preview = payload.preview === true;
    const committed = payload.committed === true || Boolean(payload.created_id);
    const summary = (payload.summary as string) ?? '';

    const title = committed
        ? 'Saved'
        : preview
          ? 'Confirm transaction'
          : 'Transaction';

    return (
        <div className={`${styles.card} ${styles.confirmCard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>{committed ? '✓' : '?'}</span>
                <span className={styles.cardTitle}>{title}</span>
            </div>

            {summary && <p className={cardStyles.summaryText}>{summary}</p>}

            <div className={cardStyles.records}>
                <div className={styles.confirmRow}>
                    <span className={styles.confirmLabel}>Amount (₹)</span>
                    <span>{amount.toLocaleString()}</span>
                </div>
                {merchant && (
                    <div className={styles.confirmRow}>
                        <span className={styles.confirmLabel}>Merchant</span>
                        <span>{merchant}</span>
                    </div>
                )}
                {category && (
                    <div className={styles.confirmRow}>
                        <span className={styles.confirmLabel}>Category</span>
                        <span>{category}</span>
                    </div>
                )}
                {date && (
                    <div className={styles.confirmRow}>
                        <span className={styles.confirmLabel}>Date</span>
                        <span>{date}</span>
                    </div>
                )}
                {payload.nw_impact != null && (
                    <div className={styles.confirmRow}>
                        <span className={styles.confirmLabel}>Type</span>
                        <span>{String(payload.nw_impact)}</span>
                    </div>
                )}
            </div>

            <div className={styles.confirmActions}>
                {preview && !committed ? (
                    <>
                        <button className="btn btn-success" onClick={() => onAccept?.()}>
                            Confirm
                        </button>
                        <button className="btn btn-ghost" onClick={() => onReject?.()}>
                            Cancel
                        </button>
                    </>
                ) : committed ? (
                    <span style={{ opacity: 0.6, fontSize: '0.9rem' }}>Recorded in your ledger</span>
                ) : null}
            </div>
        </div>
    );
}
