'use client';

import { useMemo } from 'react';
import { BarChart3 } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import { getChartColors } from '@/lib/themes/chartColors';
import styles from './Card.module.css';
import dashStyles from './SpendingDashboardCard.module.css';

interface MonthPoint {
    month: string;
    label: string;
    amount: number;
}

interface PiePoint {
    name: string;
    value: number;
}

interface Payload {
    total_spend?: number;
    by_category?: Record<string, number>;
    by_month?: MonthPoint[];
    pie_data?: PiePoint[];
    period?: string;
    period_label?: string;
    transaction_count?: number;
    narrative?: string;
}

function formatInr(n: number) {
    return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function buildConicGradient(
    slices: { value: number; color: string }[],
    total: number,
): string {
    if (total <= 0 || slices.length === 0) return 'var(--border)';
    let acc = 0;
    const stops = slices.map((s) => {
        const pct = (s.value / total) * 100;
        const start = acc;
        acc += pct;
        return `${s.color} ${start}% ${acc}%`;
    });
    return `conic-gradient(from -90deg, ${stops.join(', ')})`;
}

export default function SpendingDashboardCard({ payload }: { payload: Record<string, unknown> }) {
    const chartColors = useMemo(() => getChartColors(10), [payload]);
    const data = payload as Payload;
    const total = data.total_spend ?? 0;
    const pieData =
        data.pie_data ??
        Object.entries(data.by_category ?? {})
            .map(([name, value]) => ({ name, value: Math.abs(Number(value)) }))
            .filter((d) => d.value > 0)
            .sort((a, b) => b.value - a.value);
    const monthData = (data.by_month ?? []).map((m) => ({
        ...m,
        amount: Math.abs(Number(m.amount)),
    }));
    const maxMonth = Math.max(...monthData.map((m) => m.amount), 1);

    const pieSlices = pieData.map((row, i) => ({
        ...row,
        color: chartColors[i % chartColors.length],
    }));

    const headerIcon = (
        <span className={styles.cardIcon}>
            <AppIcon icon={BarChart3} size={18} color="var(--accent)" />
        </span>
    );

    if (total === 0 && pieData.length === 0) {
        return (
            <div className={`${styles.card} fade-up`}>
                <div className={styles.cardHeader}>
                    {headerIcon}
                    <span className={styles.cardTitle}>Spending dashboard</span>
                </div>
                <p className={dashStyles.narrative}>No expenses found for this period. Import a statement or add transactions first.</p>
            </div>
        );
    }

    return (
        <div className={`${styles.card} ${dashStyles.dashboard} fade-up`}>
            <div className={styles.cardHeader}>
                {headerIcon}
                <span className={styles.cardTitle}>Spending dashboard</span>
            </div>

            <div className={dashStyles.hero}>
                <div className={dashStyles.heroTotal}>{formatInr(total)}</div>
                <div className={dashStyles.heroMeta}>
                    {data.period_label && <span>{data.period_label}</span>}
                    {data.transaction_count != null && (
                        <span className={dashStyles.muted}>{data.transaction_count} transactions</span>
                    )}
                </div>
            </div>

            {data.narrative && <p className={dashStyles.narrative}>{data.narrative}</p>}

            <div className={dashStyles.chartsGrid}>
                {pieSlices.length > 0 && (
                    <section className={dashStyles.chartPanel}>
                        <h4 className={dashStyles.chartTitle}>By category</h4>
                        <div className={dashStyles.pieWrap}>
                            <div
                                className={dashStyles.pieDonut}
                                style={{ background: buildConicGradient(pieSlices, total) }}
                                role="img"
                                aria-label="Spending by category pie chart"
                            >
                                <div className={dashStyles.pieHole}>
                                    <span className={dashStyles.pieHoleLabel}>Total</span>
                                    <span className={dashStyles.pieHoleValue}>{formatInr(total)}</span>
                                </div>
                            </div>
                            <ul className={dashStyles.pieLegend}>
                                {pieSlices.slice(0, 6).map((row) => (
                                    <li key={row.name}>
                                        <span className={dashStyles.dot} style={{ background: row.color }} />
                                        <span className={dashStyles.legendName}>{row.name}</span>
                                        <span className={dashStyles.legendPct}>
                                            {total > 0 ? ((row.value / total) * 100).toFixed(0) : 0}%
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </section>
                )}

                {monthData.length > 0 && (
                    <section className={dashStyles.chartPanel}>
                        <h4 className={dashStyles.chartTitle}>Monthly trend</h4>
                        <div className={dashStyles.barChart} role="img" aria-label="Monthly spending bar chart">
                            {monthData.map((m) => (
                                <div key={m.month} className={dashStyles.barCol}>
                                    <div className={dashStyles.barTrack}>
                                        <div
                                            className={dashStyles.barFill}
                                            style={{ height: `${(m.amount / maxMonth) * 100}%` }}
                                            title={`${m.label}: ${formatInr(m.amount)}`}
                                        />
                                    </div>
                                    <span className={dashStyles.barLabel}>{m.label.split(' ')[0]}</span>
                                </div>
                            ))}
                        </div>
                    </section>
                )}
            </div>

            {pieData.length > 0 && (
                <div className={dashStyles.categoryTable}>
                    {pieData.slice(0, 8).map((row, i) => {
                        const pct = total > 0 ? (row.value / total) * 100 : 0;
                        return (
                            <div key={row.name} className={dashStyles.categoryRow}>
                                <span
                                    className={dashStyles.dot}
                                    style={{ background: chartColors[i % chartColors.length] }}
                                />
                                <span className={dashStyles.catName}>{row.name}</span>
                                <span className={dashStyles.catAmt}>{formatInr(row.value)}</span>
                                <span className={dashStyles.catPct}>{pct.toFixed(0)}%</span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
