import { AlertTriangle } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';

interface Anomaly {
    merchant: string;
    amount: number;
    date: string;
    reason: string;
}

interface AnomalyPayload {
    alerts_found: number;
    anomalies: Anomaly[];
    message: string;
}

export default function AnomalyAlertCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as unknown as AnomalyPayload;
    if (data.alerts_found === undefined) return null;

    return (
        <div
            className={styles.card}
            style={{ borderColor: 'color-mix(in srgb, var(--danger) 35%, var(--border))' }}
        >
            <div className={styles.header}>
                <h3 className={`${styles.title} amount-liability`} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AppIcon icon={AlertTriangle} size={20} color="var(--danger)" aria-hidden={false} aria-label="Alert" />
                    Unusual Spending
                </h3>
            </div>

            <p className={styles.subtext}>{data.message}</p>

            <div className={styles.divider} />

            <div className={styles.transactionList}>
                {data.anomalies?.map((item, idx) => (
                    <div
                        key={idx}
                        style={{
                            padding: '12px',
                            backgroundColor: 'color-mix(in srgb, var(--danger) 6%, transparent)',
                            borderRadius: 'var(--radius-sm)',
                            marginBottom: '8px',
                        }}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span className={styles.transactionMerchant}>{item.merchant}</span>
                            <span className={`${styles.transactionAmount} amount-liability`}>
                                ₹{item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                            <span className={styles.transactionDate}>{item.date}</span>
                            <span style={{ color: 'var(--text-secondary)' }}>{item.reason}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
