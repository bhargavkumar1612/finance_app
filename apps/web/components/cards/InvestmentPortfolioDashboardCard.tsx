'use client';

import { useMemo } from 'react';
import { TrendingUp } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import { getChartColors } from '@/lib/themes/chartColors';
import styles from './Card.module.css';
import dashStyles from './SpendingDashboardCard.module.css';

interface Payload {
    totals?: {
        invested?: number;
        current?: number;
        pnl_amount?: number | null;
        pnl_percent?: number | null;
    };
    by_liquidity?: Array<{ label: string; current_value: number }>;
    by_value?: Array<{ name: string; type: string; current_value: number; as_per_ledger?: boolean }>;
    pie_by_type?: Array<{ name: string; value: number }>;
    physical_assets?: Array<{ name: string; current_value: number }>;
    footer_suggestions?: Array<{ label: string; reason: string }>;
    message?: string;
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

export default function InvestmentPortfolioDashboardCard({ payload }: { payload: Record<string, unknown> }) {
    const chartColors = useMemo(() => getChartColors(8), [payload]);
    const data = payload as Payload;
    const totals = data.totals ?? {};
    const current = totals.current ?? 0;
    const pieData = data.pie_by_type ?? [];
    const pieSlices = pieData.map((row, i) => ({
        ...row,
        color: chartColors[i % chartColors.length],
    }));
    const pieTotal = pieSlices.reduce((s, r) => s + r.value, 0);

    if (current === 0 && pieData.length === 0) {
        return (
            <div className={`${styles.card} fade-up`}>
                <div className={styles.cardHeader}>
                    <span className={styles.cardIcon}>
                        <AppIcon icon={TrendingUp} size={18} color="var(--accent)" />
                    </span>
                    <span className={styles.cardTitle}>Investment portfolio</span>
                </div>
                <p className={dashStyles.narrative}>
                    No investments tracked yet. Add a mutual fund, FD, or stock account to get started.
                </p>
            </div>
        );
    }

    return (
        <div className={`${styles.card} ${dashStyles.dashboard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={TrendingUp} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>Investment portfolio</span>
            </div>

            <div className={dashStyles.hero}>
                <div className={dashStyles.heroTotal}>{formatInr(current)}</div>
                <div className={dashStyles.heroMeta}>
                    {totals.invested != null && <span>Invested {formatInr(totals.invested)}</span>}
                    {totals.pnl_amount != null && totals.pnl_percent != null && (
                        <span className={totals.pnl_amount >= 0 ? styles.positive : styles.negative}>
                            P&L {formatInr(totals.pnl_amount)} ({totals.pnl_percent >= 0 ? '+' : ''}
                            {totals.pnl_percent.toFixed(1)}%)
                        </span>
                    )}
                </div>
            </div>

            {data.message && <p className={dashStyles.narrative}>{data.message}</p>}

            {pieSlices.length > 0 && (
                <div className={dashStyles.chartsGrid}>
                    <section className={dashStyles.chartPanel}>
                        <h4 className={dashStyles.chartTitle}>By type</h4>
                        <div className={dashStyles.pieWrap}>
                            <div
                                className={dashStyles.pieDonut}
                                style={{ background: buildConicGradient(pieSlices, pieTotal) }}
                                role="img"
                                aria-label="Portfolio by type"
                            >
                                <div className={dashStyles.pieHole}>
                                    <span className={dashStyles.pieHoleLabel}>Current</span>
                                    <span className={dashStyles.pieHoleValue}>{formatInr(current)}</span>
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

            {(data.by_liquidity?.length ?? 0) > 0 && (
                <div className={dashStyles.categoryTable}>
                    <h4 className={dashStyles.chartTitle}>By liquidity</h4>
                    {data.by_liquidity!.map((row, i) => (
                        <div key={row.label} className={dashStyles.categoryRow}>
                            <span className={dashStyles.dot} style={{ background: chartColors[i % chartColors.length] }} />
                            <span className={dashStyles.catName}>{row.label}</span>
                            <span className={dashStyles.catAmt}>{formatInr(row.current_value)}</span>
                        </div>
                    ))}
                </div>
            )}

            {(data.by_value?.length ?? 0) > 0 && (
                <div className={dashStyles.categoryTable}>
                    <h4 className={dashStyles.chartTitle}>Top by value</h4>
                    {data.by_value!.slice(0, 5).map((row, i) => (
                        <div key={row.name} className={dashStyles.categoryRow}>
                            <span className={dashStyles.dot} style={{ background: chartColors[i % chartColors.length] }} />
                            <span className={dashStyles.catName}>
                                {row.name}
                                {row.as_per_ledger && (
                                    <span className={dashStyles.muted}> (as per ledger)</span>
                                )}
                            </span>
                            <span className={dashStyles.catAmt}>{formatInr(row.current_value)}</span>
                        </div>
                    ))}
                </div>
            )}

            {(data.footer_suggestions?.length ?? 0) > 0 && (
                <div className={dashStyles.categoryTable}>
                    <h4 className={dashStyles.chartTitle}>Suggested actions</h4>
                    {data.footer_suggestions!.map((s) => (
                        <div key={s.label} className={dashStyles.categoryRow} style={{ gridTemplateColumns: '1fr' }}>
                            <span className={dashStyles.catName}>
                                <strong>{s.label}</strong> — {s.reason}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
