import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

const RISK_META = {
    low: { label: 'Low Risk', color: '#10b981', bg: 'rgba(16, 185, 129, 0.12)' },
    medium: { label: 'Medium Risk', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)' },
    high: { label: 'High Risk', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.12)' },
    unknown: { label: 'Unknown', color: '#6b7280', bg: 'rgba(107, 114, 128, 0.12)' },
};

export default function AffordabilityCard({ payload }: Props) {
    const safeEmi = payload.safe_emi_estimate as number ?? 0;
    const riskLevel = (payload.risk_level as string ?? 'unknown') as keyof typeof RISK_META;
    const netWorth = payload.net_worth as number ?? 0;
    const monthlySpend = payload.monthly_spend as number ?? 0;
    const message = payload.message as string ?? '';
    const meta = RISK_META[riskLevel] ?? RISK_META.unknown;

    return (
        <div className={`${styles.card} ${styles.affordCard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>🧮</span>
                <span className={styles.cardTitle}>Affordability Check</span>
            </div>
            <div className={styles.affordEmi}>
                ₹{safeEmi.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                <span className={styles.affordEmiLabel}>/month safe EMI</span>
            </div>
            <div className={styles.affordRisk} style={{ background: meta.bg, borderColor: meta.color + '33' }}>
                <span style={{ color: meta.color, fontWeight: 600 }}>{meta.label}</span>
            </div>
            <div className={styles.affordStats}>
                <div className={styles.affordStat}>
                    <span className={styles.affordStatLabel}>Net Worth</span>
                    <span className={styles.affordStatValue}>₹{netWorth.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                </div>
                <div className={styles.affordStat}>
                    <span className={styles.affordStatLabel}>Monthly Spend</span>
                    <span className={styles.affordStatValue}>₹{monthlySpend.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                </div>
            </div>
            {message && <p className={styles.affordMessage}>{message}</p>}
        </div>
    );
}
