'use client';

import { useMemo } from 'react';
import { PieChart } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import { getChartColors } from '@/lib/themes/chartColors';
import styles from './Card.module.css';
import dashStyles from './SpendingDashboardCard.module.css';

interface PiePoint {
    name: string;
    value: number;
}

interface InvestmentPayload {
    total_invested: number;
    allocation: Record<string, number>;
    pie_data?: PiePoint[];
    pie_by_type?: PiePoint[];
    message: string;
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

export default function InvestmentPieChartCard({ payload }: { payload: Record<string, unknown> }) {
    const chartColors = useMemo(() => getChartColors(8), [payload]);
    const data = payload as unknown as InvestmentPayload;
    if (data.total_invested === undefined) return null;

    const pieData: PiePoint[] =
        data.pie_data ??
        data.pie_by_type ??
        Object.entries(data.allocation || {}).map(([name, pct]) => ({
            name,
            value: (pct / 100) * data.total_invested,
        }));

    const pieSlices = pieData
        .filter((row) => row.value > 0)
        .map((row, i) => ({ ...row, color: chartColors[i % chartColors.length] }));
    const pieTotal = pieSlices.reduce((s, r) => s + r.value, 0);

    return (
        <div className={`${styles.card} ${dashStyles.dashboard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={PieChart} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>Investment allocation</span>
            </div>

            <div className={dashStyles.hero}>
                <div className={dashStyles.heroTotal}>{formatInr(data.total_invested)}</div>
            </div>

            <p className={dashStyles.narrative}>{data.message}</p>

            {pieSlices.length > 0 && (
                <div className={dashStyles.chartsGrid}>
                    <section className={dashStyles.chartPanel}>
                        <h4 className={dashStyles.chartTitle}>By type</h4>
                        <div className={dashStyles.pieWrap}>
                            <div
                                className={dashStyles.pieDonut}
                                style={{ background: buildConicGradient(pieSlices, pieTotal) }}
                                role="img"
                                aria-label="Investment allocation pie chart"
                            >
                                <div className={dashStyles.pieHole}>
                                    <span className={dashStyles.pieHoleLabel}>Total</span>
                                    <span className={dashStyles.pieHoleValue}>{formatInr(pieTotal)}</span>
                                </div>
                            </div>
                            <ul className={dashStyles.pieLegend}>
                                {pieSlices.map((row) => (
                                    <li key={row.name}>
                                        <span className={dashStyles.dot} style={{ background: row.color }} />
                                        <span className={dashStyles.legendName}>{row.name}</span>
                                        <span className={dashStyles.legendPct}>
                                            {pieTotal > 0 ? Math.round((row.value / pieTotal) * 100) : 0}%
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </section>
                </div>
            )}
        </div>
    );
}
