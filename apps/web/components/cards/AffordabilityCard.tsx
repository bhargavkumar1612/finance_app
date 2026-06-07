import { Calculator } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

const RISK_META = {
    low: { label: 'Low Risk', colorVar: 'var(--success)' },
    medium: { label: 'Medium Risk', colorVar: 'var(--warning)' },
    high: { label: 'High Risk', colorVar: 'var(--danger)' },
    unknown: { label: 'Unknown', colorVar: 'var(--text-muted)' },
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
                <span className={styles.cardIcon}>
                    <AppIcon icon={Calculator} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>Affordability Check</span>
            </div>
            <div className={styles.affordEmi}>
                ₹{safeEmi.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                <span className={styles.affordEmiLabel}>/month safe EMI</span>
            </div>
            <div
                className={styles.affordRisk}
                style={{
                    background: `color-mix(in srgb, ${meta.colorVar} 12%, transparent)`,
                    borderColor: `color-mix(in srgb, ${meta.colorVar} 20%, transparent)`,
                }}
            >
                <span style={{ color: meta.colorVar, fontWeight: 600 }}>{meta.label}</span>
            </div>
            <div className={styles.affordStats}>
                <div className={styles.affordStat}>
                    <span className={styles.affordStatLabel}>Net Worth</span>
                    <span className={`${styles.affordStatValue} amount-asset`}>
                        ₹{netWorth.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </span>
                </div>
                <div className={styles.affordStat}>
                    <span className={styles.affordStatLabel}>Monthly Spend</span>
                    <span className={`${styles.affordStatValue} amount-liability`}>
                        ₹{monthlySpend.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </span>
                </div>
            </div>
            {message && <p className={styles.affordMessage}>{message}</p>}
        </div>
    );
}
