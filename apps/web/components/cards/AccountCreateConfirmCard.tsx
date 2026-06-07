'use client';
import { Building2, HelpCircle, CheckCircle2 } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

function row(label: string, value: string | number | undefined) {
    if (value == null || value === '') return null;
    return (
        <div className={styles.confirmRow} key={label}>
            <span className={styles.confirmLabel}>{label}</span>
            <span>{typeof value === 'number' ? `₹${value.toLocaleString('en-IN')}` : value}</span>
        </div>
    );
}

export default function AccountCreateConfirmCard({ payload, onAccept, onReject }: Props) {
    const preview = payload.preview === true;
    const committed = !preview && !!payload.id;
    const summary = (payload.summary as string) ?? '';

    const rows = [
        row('Type', payload.account_type as string),
        row('Name', payload.name as string),
        row('Institution', payload.institution as string),
        row('Mode', payload.investment_mode as string),
        row('SIP amount', payload.emi_amount as number),
        row('Due day', payload.due_day as number),
        row('Start date', payload.start_date as string),
        row('Tenure', payload.tenure_months != null ? `${payload.tenure_months} months` : undefined),
        row('Loan type', payload.loan_type as string),
        row('Credit limit', payload.credit_limit as number),
        row('Opening balance', payload.opening_balance as number),
    ].filter(Boolean);

    return (
        <div className={`${styles.card} ${styles.confirmCard} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon
                        icon={committed ? CheckCircle2 : HelpCircle}
                        size={18}
                        color={committed ? 'var(--success)' : 'var(--warning)'}
                    />
                </span>
                <span className={styles.cardTitle}>
                    {committed ? 'Account created' : 'Confirm new account'}
                </span>
            </div>

            {summary && <p style={{ marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{summary}</p>}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {rows}
            </div>

            <div className={styles.confirmActions}>
                {preview && !committed ? (
                    <>
                        <button className="btn btn-success" onClick={() => onAccept?.()}>
                            <Building2 size={14} style={{ marginRight: 4 }} />
                            Create account
                        </button>
                        <button className="btn btn-ghost" onClick={() => onReject?.()}>
                            Cancel
                        </button>
                    </>
                ) : committed ? (
                    <span style={{ color: 'var(--success)', fontSize: '0.85rem' }}>Saved to your accounts</span>
                ) : null}
            </div>
        </div>
    );
}
