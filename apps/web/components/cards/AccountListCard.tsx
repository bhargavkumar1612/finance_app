'use client';

import type { Account } from '@/lib/api';
import AccountTypeIcon from '@/components/icons/AccountTypeIcon';
import {
    accountDisplayLabel,
    formatAccountMetrics,
} from '@/lib/accountDisplay';

interface AccountRow extends Pick<
    Account,
    | 'loan_type'
    | 'loan_type_description'
    | 'balance'
    | 'credit_used'
    | 'credit_remaining'
    | 'credit_limit'
    | 'sanctioned_amount'
    | 'outstanding'
    | 'amount_paid'
    | 'emi_amount'
    | 'emi_paid_count'
    | 'emi_pending_count'
> {
    id?: string;
    name?: string;
    account_type?: string;
    institution?: string;
    transaction_count?: number;
}

export default function AccountListCard({ payload }: { payload: Record<string, unknown> }) {
    const accounts = (payload.accounts as AccountRow[] | undefined) ?? [];
    const message = payload.message as string | undefined;

    if (!accounts.length) {
        return <p style={{ margin: 0, fontSize: '0.9rem' }}>{message || 'No accounts.'}</p>;
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {message && (
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)', whiteSpace: 'pre-line' }}>
                    {message.split('\n')[0]}
                </p>
            )}
            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {accounts.map((a) => {
                    const row = a as AccountRow & { account_type: string };
                    const metrics = formatAccountMetrics({
                        ...row,
                        account_type: (row.account_type ?? 'bank') as Account['account_type'],
                    });
                    return (
                        <li
                            key={a.id ?? a.name}
                            style={{
                                padding: '10px 12px',
                                borderRadius: 8,
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--border-subtle)',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <AccountTypeIcon
                                    type={row.account_type ?? 'bank'}
                                    loanType={row.loan_type}
                                    size={16}
                                />
                                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{a.name}</span>
                                <span
                                    style={{
                                        fontSize: '0.7rem',
                                        padding: '2px 6px',
                                        borderRadius: 999,
                                        background: 'var(--bg-input)',
                                        color: 'var(--text-muted)',
                                    }}
                                >
                                    {accountDisplayLabel({
                                        account_type: (row.account_type ?? 'bank') as Account['account_type'],
                                        loan_type: row.loan_type ?? null,
                                        loan_type_description: row.loan_type_description ?? null,
                                    })}
                                </span>
                            </div>
                            {metrics.map((line) => (
                                <div key={line} style={{ fontSize: '0.8rem', marginTop: 4, fontWeight: 500 }}>
                                    {line}
                                </div>
                            ))}
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
