'use client';

import { useMemo } from 'react';
import { PieChart } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import { getChartColors } from '@/lib/themes/chartColors';
import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
    food: 'var(--danger)',
    rent: 'var(--warning)',
    travel: 'var(--neutral)',
    emi: 'var(--accent)',
    utilities: 'var(--chart-6)',
    shopping: 'var(--chart-7)',
    health: 'var(--success)',
    other: 'var(--text-muted)',
    uncategorized: 'var(--text-muted)',
};

export default function MonthlySummaryCard({ payload }: Props) {
    const chartColors = useMemo(() => getChartColors(8), [payload]);
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
                <span className={styles.cardIcon}>
                    <AppIcon icon={PieChart} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>Monthly Spending</span>
            </div>
            <div className={styles.summaryTotal}>
                ₹{totalSpend.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            {period && <p className={styles.summaryPeriod}>{period}</p>}
            <div className={styles.categoryList}>
                {sortedCategories.length === 0 ? (
                    <p className="text-muted" style={{ fontSize: '0.875rem' }}>No expenses in this period.</p>
                ) : sortedCategories.map(([cat, amt], i) => {
                    const pct = (amt / maxAmount) * 100;
                    const color = CATEGORY_COLORS[cat.toLowerCase()] ?? chartColors[i % chartColors.length];
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
