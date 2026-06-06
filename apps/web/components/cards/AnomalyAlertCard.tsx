import styles from './Card.module.css';

interface Anomaly {
    merchant: string;
    amount: number;
    date: string;
    reason: string;
}

interface AnomalyPayload {
    alerts_found: number;
    anomalies: Anomaly[];
    message: string;
}

export default function AnomalyAlertCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as AnomalyPayload;
    if (data.alerts_found === undefined) return null;

    return (
        <div className={styles.card} style={{ border: '1px solid #ef4444' }}>
            <div className={styles.header}>
                <h3 className={styles.title} style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                    Unusual Spending
                </h3>
            </div>

            <p className={styles.subtext} style={{ color: 'var(--text-primary)' }}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.transactionList}>
                {data.anomalies?.map((item, idx) => (
                    <div key={idx} style={{ padding: '12px', backgroundColor: 'rgba(239, 68, 68, 0.05)', borderRadius: '8px', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span className={styles.transactionMerchant}>{item.merchant}</span>
                            <span className={styles.transactionAmount} style={{ color: '#ef4444' }}>₹{item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                            <span className={styles.transactionDate}>{item.date}</span>
                            <span style={{ color: 'var(--text-secondary)' }}>{item.reason}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
