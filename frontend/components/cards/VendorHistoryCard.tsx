import styles from './Card.module.css';

interface VendorPayload {
    merchant: string;
    lifetime_spend: number;
    transaction_count: number;
    average_transaction: number;
    message: string;
}

export default function VendorHistoryCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as VendorPayload;
    if (!data.merchant) return null;

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>{data.merchant}</h3>
                <span className={styles.subtitle}>Lifetime Spend</span>
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.row}>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Total Count</div>
                    <div className={styles.value}>{data.transaction_count} trips</div>
                </div>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Average Amount</div>
                    <div className={styles.value}>₹{data.average_transaction?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                </div>
            </div>

            <div className={styles.divider} />

            <div className={styles.largeMetric} style={{ textAlign: 'center' }}>
                <div className={styles.label} style={{ fontSize: '0.875rem', marginBottom: '8px' }}>Lifetime Total Spent</div>
                <span className={styles.currency}>₹</span>
                {data.lifetime_spend?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
        </div>
    );
}
