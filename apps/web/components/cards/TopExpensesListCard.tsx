import styles from './Card.module.css';

interface Expense {
    merchant: string;
    amount: number;
    date: string;
}

interface TopExpensesPayload {
    period: string;
    expenses: Expense[];
    message: string;
}

export default function TopExpensesListCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as TopExpensesPayload;
    if (!data.expenses) return null;

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>Top Expenses</h3>
                <span className={styles.subtitle}>{data.period.replace('_', ' ')}</span>
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.transactionList}>
                {data.expenses.map((exp, idx) => (
                    <div key={idx} className={styles.transactionRow}>
                        <div className={styles.indexCircle}>{idx + 1}</div>
                        <div style={{ flex: 1, marginLeft: '12px' }}>
                            <div className={styles.transactionMerchant}>{exp.merchant}</div>
                            <div className={styles.transactionDate}>{exp.date}</div>
                        </div>
                        <div className={styles.transactionAmount}>₹{exp.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
