'use client';

import { Calendar } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';
import dashStyles from './SpendingDashboardCard.module.css';

interface DepositRow {
    name: string;
    type?: string;
    maturity_date?: string;
    start_date?: string;
    tenure_months?: number;
    message?: string;
}

interface Payload {
    deposits?: DepositRow[];
    message?: string;
}

export default function FdMaturityCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as Payload;
    const deposits = data.deposits ?? [];

    if (!deposits.length) {
        return (
            <div className={`${styles.card} fade-up`}>
                <div className={styles.cardHeader}>
                    <span className={styles.cardIcon}>
                        <AppIcon icon={Calendar} size={18} color="var(--accent)" />
                    </span>
                    <span className={styles.cardTitle}>FD / RD maturity</span>
                </div>
                <p className={dashStyles.narrative}>{data.message ?? 'No fixed or recurring deposits found.'}</p>
            </div>
        );
    }

    return (
        <div className={`${styles.card} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={Calendar} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>FD / RD maturity</span>
            </div>
            {data.message && <p className={dashStyles.narrative}>{data.message}</p>}
            <div className={dashStyles.categoryTable}>
                {deposits.map((d) => (
                    <div key={d.name} className={dashStyles.categoryRow} style={{ gridTemplateColumns: '1fr' }}>
                        <div>
                            <span className={dashStyles.catName}>
                                <strong>{d.name}</strong>
                                {d.type && ` · ${d.type.replace('_', ' ')}`}
                            </span>
                            <div className={dashStyles.muted} style={{ fontSize: '0.8rem', marginTop: 4 }}>
                                {d.maturity_date
                                    ? `Matures ${d.maturity_date}`
                                    : d.message ?? 'Set start_date and tenure_months'}
                                {d.start_date && d.tenure_months != null && (
                                    <span> · {d.tenure_months} months from {d.start_date}</span>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
