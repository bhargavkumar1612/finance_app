import styles from './Card.module.css';

interface FutureBalancePayload {
    current_balance: number;
    projected_eom_balance: number;
    upcoming_bills: number;
    message: string;
}

export default function FutureBalanceProjectionCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as FutureBalancePayload;
    if (data.current_balance === undefined) return null;

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>Future Balance Projection</h3>
                <span className={styles.subtitle}>End of Month</span>
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.row}>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Current Balance</div>
                    <div className={styles.value}>₹{data.current_balance?.toLocaleString()}</div>
                </div>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Upcoming Bills</div>
                    <div className={styles.value} style={{ color: '#ef4444' }}>-₹{data.upcoming_bills?.toLocaleString()}</div>
                </div>
            </div>

            <div className={styles.divider} />

            <div className={styles.largeMetric} style={{ textAlign: 'center' }}>
                <div className={styles.label} style={{ fontSize: '0.875rem', marginBottom: '8px' }}>Projected Balance</div>
                <span className={styles.currency}>₹</span>
                {data.projected_eom_balance?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
        </div>
    );
}
