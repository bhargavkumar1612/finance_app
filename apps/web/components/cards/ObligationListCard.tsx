'use client';

import { CalendarDays } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';
import dashStyles from './SpendingDashboardCard.module.css';

interface ObligationItem {
    name: string;
    amount?: number;
    emi_amount?: number;
    next_due_on?: string | null;
    status_label?: string;
    outstanding?: number;
    frequency?: string;
    loan_type?: string | null;
    emi_pending_count?: number | null;
}

interface Sections {
    sips?: ObligationItem[];
    loan_emis?: ObligationItem[];
    recurring_bills?: ObligationItem[];
    credit_cards?: ObligationItem[];
}

interface Payload {
    sections?: Sections;
    commitments?: Record<string, number>;
    total_monthly_commitments?: number;
    message?: string;
}

const SECTION_LABELS: Record<string, string> = {
    sips: 'SIP installments',
    loan_emis: 'Loan EMIs',
    recurring_bills: 'Recurring bills',
    credit_cards: 'Credit cards',
};

function formatInr(n: number) {
    return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function itemAmount(item: ObligationItem) {
    return item.amount ?? item.emi_amount ?? item.outstanding;
}

function ObligationSection({ title, items }: { title: string; items: ObligationItem[] }) {
    if (!items.length) return null;
    return (
        <div style={{ marginTop: 16 }}>
            <h3 className={dashStyles.sectionTitle} style={{ fontSize: '0.85rem', marginBottom: 8 }}>
                {title}
            </h3>
            <div className={dashStyles.categoryTable}>
                {items.map((item) => {
                    const amt = itemAmount(item);
                    return (
                        <div
                            key={`${title}-${item.name}`}
                            className={dashStyles.categoryRow}
                            style={{ gridTemplateColumns: '1fr' }}
                        >
                            <div>
                                <span className={dashStyles.catName}>
                                    <strong>{item.name}</strong>
                                    {amt != null && amt > 0 && ` · ${formatInr(amt)}`}
                                    {item.frequency && ` / ${item.frequency}`}
                                </span>
                                <div className={dashStyles.muted} style={{ fontSize: '0.8rem', marginTop: 4 }}>
                                    {item.status_label}
                                    {item.next_due_on && ` · Due ${item.next_due_on}`}
                                    {item.emi_pending_count != null && ` · ${item.emi_pending_count} EMIs left`}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function ObligationListCard({ payload }: { payload: Record<string, unknown> }) {
    const data = payload as Payload;
    const sections = data.sections ?? {};
    const hasSections = Object.values(sections).some((s) => (s?.length ?? 0) > 0);

    return (
        <div className={`${styles.card} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={CalendarDays} size={18} color="var(--accent)" />
                </span>
                <span className={styles.cardTitle}>Upcoming obligations</span>
            </div>
            {data.message && <p className={dashStyles.narrative}>{data.message}</p>}
            {data.total_monthly_commitments != null && data.total_monthly_commitments > 0 && (
                <p className={dashStyles.narrative} style={{ fontWeight: 600 }}>
                    Total commitments: {formatInr(data.total_monthly_commitments)}/month
                </p>
            )}
            {!hasSections ? (
                <p className={dashStyles.muted}>Add loans, SIPs, or recurring bills to see obligations.</p>
            ) : (
                Object.entries(SECTION_LABELS).map(([key, label]) => (
                    <ObligationSection
                        key={key}
                        title={label}
                        items={(sections as Record<string, ObligationItem[]>)[key] ?? []}
                    />
                ))
            )}
        </div>
    );
}
