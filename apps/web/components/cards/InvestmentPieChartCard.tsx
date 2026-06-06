import styles from './Card.module.css';

interface InvestmentPayload {
    total_invested: number;
    allocation: Record<string, number>;
    message: string;
}

export default function InvestmentPieChartCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as InvestmentPayload;
    if (data.total_invested === undefined) return null;

    // A simple visual bar representing the pie chart instead of pulling in an SVG library for the mock
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'];
    const entries = Object.entries(data.allocation || {});

    return (
        <div className={styles.card}>
            <div className={styles.header}>
                <h3 className={styles.title}>Investment Portfolio</h3>
            </div>

            <div className={styles.largeMetric}>
                <span className={styles.currency}>₹</span>
                {data.total_invested?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div style={{ display: 'flex', height: '16px', width: '100%', borderRadius: '8px', overflow: 'hidden', marginBottom: '16px' }}>
                {entries.map(([name, pct], i) => (
                    <div key={name} style={{ width: `${pct}%`, backgroundColor: colors[i % colors.length], height: '100%' }} />
                ))}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                {entries.map(([name, pct], i) => (
                    <div key={name} style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: colors[i % colors.length], marginRight: '6px' }} />
                        <span style={{ color: 'var(--text-primary)', marginRight: '4px' }}>{name}</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{pct}%</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
