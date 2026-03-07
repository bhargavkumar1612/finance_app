import styles from './Card.module.css';

interface CashFlowPayload {
    period: string;
    total_income: number;
    total_expense: number;
    net_cash_flow: number;
    savings_rate_pct: number;
    message: string;
}

export default function CashFlowSummaryCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as CashFlowPayload;
    if (!data.period) return null;

    const isPositive = data.net_cash_flow >= 0;

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>Cash Flow</h3>
                <span className={styles.subtitle}>{data.period.replace('_', ' ')}</span>
            </div>

            <div className={styles.row}>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Income</div>
                    <div className={styles.value} style={{ color: '#10b981' }}>₹{data.total_income?.toLocaleString()}</div>
                </div>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Expenses</div>
                    <div className={styles.value} style={{ color: '#ef4444' }}>₹{data.total_expense?.toLocaleString()}</div>
                </div>
            </div>

            <div className={styles.divider} />

            <div className={styles.row}>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Net Cash Flow</div>
                    <div className={styles.value} style={{ color: isPositive ? '#10b981' : '#ef4444' }}>
                        {isPositive ? '+' : '-'}₹{Math.abs(data.net_cash_flow).toLocaleString()}
                    </div>
                </div>
                <div style={{ flex: 1 }}>
                    <div className={styles.label}>Savings Rate</div>
                    <div className={styles.value}>{data.savings_rate_pct}%</div>
                </div>
            </div>

            <p className={styles.subtext} style={{ marginTop: '1rem', textAlign: 'center' }}>{data.message}</p>
        </div>
    );
}
