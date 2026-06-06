import styles from './Card.module.css';

interface CategoryDrilldownPayload {
    category: string;
    period: string;
    total: number;
    message: string;
    transactions: { date: string; merchant: string; amount: number }[];
}

export default function CategoryDrilldownCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as CategoryDrilldownPayload;
    if (!data.category) return null;

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>{data.category} Breakdown</h3>
                <span className={styles.subtitle}>{data.period.replace('_', ' ')}</span>
            </div>

            <div className={styles.largeMetric}>
                <span className={styles.currency}>₹</span>
                {data.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.transactionList}>
                {data.transactions?.map((t, idx) => (
                    <div key={idx} className={styles.transactionRow}>
                        <div>
                            <div className={styles.transactionMerchant}>{t.merchant}</div>
                            <div className={styles.transactionDate}>{t.date}</div>
                        </div>
                        <div className={styles.transactionAmount}>₹{t.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
