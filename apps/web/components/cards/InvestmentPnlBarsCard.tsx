'use client';

import { useMemo } from 'react';
import { BarChart2 } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import { getChartColors } from '@/lib/themes/chartColors';
import styles from './Card.module.css';
import dashStyles from './SpendingDashboardCard.module.css';

interface PnlRow {
    name: string;
    pnl_percent?: number | null;
    pnl_amount?: number | null;
}

interface Payload {
    by_pnl_percent?: PnlRow[];
    by_pnl_amount?: PnlRow[];
    message?: string;
}

function formatInr(n: number) {
    return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function BarSection({
    title,
    rows,
    valueKey,
    format,
    colors,
}: {
    title: string;
    rows: PnlRow[];
    valueKey: 'pnl_percent' | 'pnl_amount';
    format: (n: number) => string;
    colors: string[];
}) {
    if (!rows.length) return null;
    const values = rows.map((r) => Math.abs(r[valueKey] ?? 0));
    const max = Math.max(...values, 1);

    return (
        <section className={dashStyles.chartPanel}>
            <h4 className={dashStyles.chartTitle}>{title}</h4>
            <div className={dashStyles.barChart}>
                {rows.map((row, i) => {
                    const val = row[valueKey] ?? 0;
                    const height = (Math.abs(val) / max) * 100;
                    return (
                        <div key={row.name} className={dashStyles.barCol}>
                            <div className={dashStyles.barTrack}>
                                <div
                                    className={dashStyles.barFill}
                                    style={{
                                        height: `${height}%`,
                                        background: colors[i % colors.length],
                                    }}
                                />
                            </div>
                            <span className={dashStyles.barLabel} title={row.name}>
                                {row.name.slice(0, 8)}
                            </span>
                            <span className={dashStyles.barLabel}>{format(val)}</span>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}

export default function InvestmentPnlBarsCard({ payload }: { payload: Record<string, unknown> }) {
    const chartColors = useMemo(() => getChartColors(6), [payload]);
    const data = payload as Payload;
    const byPct = data.by_pnl_percent ?? [];
    const byAmt = data.by_pnl_amount ?? [];

    if (!byPct.length && !byAmt.length) {
        return (
            <div className={`${styles.card} fade-up`}>
                <div className={styles.cardHeader}>
                    <span className={styles.cardIcon}>
                        <AppIcon icon={BarChart2} size={18} color="var(--accent)" />
                    </span>
                    <span className={styles.cardTitle}>P&L drill-down</span>
                </div>
                <p className={dashStyles.narrative}>
                    No holdings with P&L yet. Set invested and current values on your accounts.
                </p>
            </div>
        );
    }

    return (
        <div className={`${styles.card} ${dashStyles.dashboard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={BarChart2} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>P&L drill-down</span>
            </div>
            {data.message && <p className={dashStyles.narrative}>{data.message}</p>}
            <div className={dashStyles.chartsGrid}>
                <BarSection
                    title="Top by %"
                    rows={byPct}
                    valueKey="pnl_percent"
                    format={(n) => `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`}
                    colors={chartColors}
                />
                <BarSection
                    title="Top by ₹"
                    rows={byAmt}
                    valueKey="pnl_amount"
                    format={formatInr}
                    colors={chartColors}
                />
            </div>
        </div>
    );
}
