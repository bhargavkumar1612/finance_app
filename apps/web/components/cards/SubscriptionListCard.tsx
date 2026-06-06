import styles from './Card.module.css';

interface Subscription {
    service: string;
    amount: number;
    frequency: string;
}

interface SubscriptionPayload {
    subscriptions: Subscription[];
    total_monthly: number;
    message: string;
}

export default function SubscriptionListCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as SubscriptionPayload;
    if (!data.subscriptions) return null;

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>Active Subscriptions</h3>
                <span className={styles.subtitle}>Recurring Bills</span>
            </div>

            <div className={styles.largeMetric}>
                <span className={styles.currency}>₹</span>
                {data.total_monthly?.toLocaleString(undefined, { minimumFractionDigits: 2 })}<span className={styles.subtext}>/mo</span>
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.transactionList}>
                {data.subscriptions.map((sub, idx) => (
                    <div key={idx} className={styles.transactionRow}>
                        <div>
                            <div className={styles.transactionMerchant}>{sub.service}</div>
                            <div className={styles.transactionDate}>{sub.frequency}</div>
                        </div>
                        <div className={styles.transactionAmount}>₹{sub.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
