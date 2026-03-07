import styles from './Card.module.css';

interface PayoffPayload {
    total_debt: number;
    strategy: string;
    recommended_monthly_payment: number;
    months_to_payoff: number;
    message: string;
}

export default function DebtPayoffPlanCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as PayoffPayload;
    if (data.total_debt === undefined) return null;

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>Debt Payoff Planner</h3>
                <span className={styles.subtitle}>{data.strategy} Method</span>
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.row}>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Total Debt</div>
                    <div className={styles.value} style={{ color: '#ef4444' }}>₹{data.total_debt?.toLocaleString()}</div>
                </div>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Est. Time</div>
                    <div className={styles.value}>{data.months_to_payoff} months</div>
                </div>
            </div>

            <div className={styles.divider} />

            <div className={styles.largeMetric} style={{ textAlign: 'center' }}>
                <div className={styles.label} style={{ fontSize: '0.875rem', marginBottom: '8px' }}>Recommended Monthly Payment</div>
                <span className={styles.currency}>₹</span>
                {data.recommended_monthly_payment?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
        </div>
    );
}
