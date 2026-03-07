import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

export default function NetWorthBreakdownCard({ payload }: Props) {
    const netWorth = payload.net_worth as number ?? 0;
    const assets = payload.assets_total as number ?? 0;
    const liabilities = payload.liabilities_total as number ?? 0;
    const isPositive = netWorth >= 0;

    return (
        <div className={`${styles.card} ${styles.netWorthCard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>💎</span>
                <span className={styles.cardTitle}>Net Worth</span>
            </div>
            <div className={`${styles.netWorthValue} ${isPositive ? styles.positive : styles.negative}`}>
                {isPositive ? '' : '−'}₹{Math.abs(netWorth).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <div className={styles.netWorthBreakdown}>
                <div className={styles.nwRow}>
                    <div className={styles.nwDot} style={{ background: '#10b981' }} />
                    <span className={styles.nwLabel}>Total Assets</span>
                    <span className={`${styles.nwAmount} text-success`}>
                        ₹{assets.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                </div>
                <div className={styles.nwDivider} />
                <div className={styles.nwRow}>
                    <div className={styles.nwDot} style={{ background: '#ef4444' }} />
                    <span className={styles.nwLabel}>Total Liabilities</span>
                    <span className={`${styles.nwAmount} text-danger`}>
                        ₹{liabilities.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                </div>
                {assets > 0 || liabilities > 0 ? (
                    <div className={styles.nwBar}>
                        <div
                            className={styles.nwAssetBar}
                            style={{ width: `${assets / (assets + liabilities) * 100}%` }}
                        />
                    </div>
                ) : null}
            </div>
            <p className={styles.nwHint}>
                {assets === 0 && liabilities === 0
                    ? 'Add assets and liabilities to see your full net worth.'
                    : 'Assets minus liabilities. Updated in real-time.'}
            </p>
        </div>
    );
}
