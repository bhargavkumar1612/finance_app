'use client';

import { CalendarClock } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';
import dashStyles from './SpendingDashboardCard.module.css';

interface SipRow {
    name: string;
    emi_amount?: number;
    last_paid_on?: string | null;
    next_expected_on?: string | null;
    status_label?: string;
    sip_paid_count?: number | null;
    sip_pending_count?: number | null;
}

interface Payload {
    sips?: SipRow[];
    message?: string;
}

function formatInr(n: number) {
    return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export default function SipScheduleSummaryCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as Payload;
    const sips = data.sips ?? [];

    if (!sips.length) {
        return (
            <div className={`${styles.card} fade-up`}>
                <div className={styles.cardHeader}>
                    <span className={styles.cardIcon}>
                        <AppIcon icon={CalendarClock} size={18} color="var(--accent)" />
                    </span>
                    <span className={styles.cardTitle}>SIP status</span>
                </div>
                <p className={dashStyles.narrative}>
                    {data.message ?? 'No SIP mutual funds set up.'}
                </p>
            </div>
        );
    }

    return (
        <div className={`${styles.card} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={CalendarClock} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>SIP status</span>
            </div>
            {data.message && <p className={dashStyles.narrative}>{data.message}</p>}
            <div className={dashStyles.categoryTable}>
                {sips.map((sip) => (
                    <div key={sip.name} className={dashStyles.categoryRow} style={{ gridTemplateColumns: '1fr' }}>
                        <div>
                            <span className={dashStyles.catName}>
                                <strong>{sip.name}</strong>
                                {sip.emi_amount != null && ` · ${formatInr(sip.emi_amount)}/mo`}
                            </span>
                            <div className={dashStyles.muted} style={{ fontSize: '0.8rem', marginTop: 4 }}>
                                {sip.status_label}
                                {sip.last_paid_on && ` · Last paid ${sip.last_paid_on}`}
                                {sip.next_expected_on && ` · Next ${sip.next_expected_on}`}
                            </div>
                            {(sip.sip_paid_count != null || sip.sip_pending_count != null) && (
                                <div className={dashStyles.muted} style={{ fontSize: '0.75rem' }}>
                                    {sip.sip_paid_count ?? 0} paid
                                    {sip.sip_pending_count != null && ` · ${sip.sip_pending_count} pending`}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
