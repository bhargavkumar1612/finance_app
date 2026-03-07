import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
    food: '#ef4444',
    rent: '#f59e0b',
    travel: '#3b82f6',
    emi: '#8b5cf6',
    utilities: '#06b6d4',
    shopping: '#ec4899',
    health: '#10b981',
    other: '#6b7280',
    uncategorized: '#6b7280',
};

export default function MonthlySummaryCard({ payload }: Props) {
    const totalSpend = payload.total_spend as number ?? 0;
    const byCategory = (payload.by_category ?? {}) as Record<string, number>;
    const period = payload.period as string ?? '';

    const sortedCategories = Object.entries(byCategory)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8);
    const maxAmount = sortedCategories[0]?.[1] ?? 1;

    return (
        <div className={`${styles.card} ${styles.summaryCard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>📊</span>
                <span className={styles.cardTitle}>Monthly Spending</span>
            </div>
            <div className={styles.summaryTotal}>
                ₹{totalSpend.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            {period && <p className={styles.summaryPeriod}>{period}</p>}
            <div className={styles.categoryList}>
                {sortedCategories.length === 0 ? (
                    <p className="text-muted" style={{ fontSize: '0.875rem' }}>No expenses in this period.</p>
                ) : sortedCategories.map(([cat, amt]) => {
                    const pct = (amt / maxAmount) * 100;
                    const color = CATEGORY_COLORS[cat.toLowerCase()] ?? CATEGORY_COLORS.other;
                    return (
                        <div key={cat} className={styles.categoryRow}>
                            <div className={styles.categoryHeader}>
                                <span className={styles.categoryName}>{cat}</span>
                                <span className={styles.categoryAmount}>₹{Math.abs(amt).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                            </div>
                            <div className={styles.barTrack}>
                                <div
                                    className={styles.barFill}
                                    style={{ width: `${pct}%`, background: color }}
                                />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
