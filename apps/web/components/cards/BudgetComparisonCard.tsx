import styles from './Card.module.css';

interface Budget {
    category: string;
    budget: number;
    actual: number;
    status: string;
}

interface BudgetPayload {
    categories: Budget[];
    message: string;
}

export default function BudgetComparisonCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as BudgetPayload;
    if (!data.categories) return null;

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>Budget vs Actual</h3>
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.transactionList}>
                {data.categories.map((item, idx) => {
                    const percent = Math.min(100, Math.max(0, (item.actual / item.budget) * 100));
                    const isOver = percent >= 100;
                    return (
                        <div key={idx} style={{ marginBottom: '16px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                <span className={styles.label} style={{ color: 'var(--text-primary)' }}>{item.category}</span>
                                <span className={styles.value} style={{ color: isOver ? '#ef4444' : 'var(--text-primary)' }}>
                                    ₹{item.actual.toLocaleString()} / ₹{item.budget.toLocaleString()}
                                </span>
                            </div>
                            <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--border-color)', borderRadius: '4px', overflow: 'hidden' }}>
                                <div style={{
                                    width: `${percent}%`,
                                    height: '100%',
                                    backgroundColor: isOver ? '#ef4444' : '#10b981',
                                    borderRadius: '4px',
                                    transition: 'width 0.5s ease-in-out'
                                }} />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
