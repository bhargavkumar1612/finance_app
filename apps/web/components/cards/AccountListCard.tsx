'use client';

interface AccountRow {
    id?: string;
    name?: string;
    account_type?: string;
    institution?: string;
    credit_limit?: number | null;
    currency?: string;
    transaction_count?: number;
}

function typeLabel(t?: string): string {
    if (!t) return 'Account';
    return t.replace(/_/g, ' ');
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
                {accounts.map((a) => (
                    <li
                        key={a.id ?? a.name}
                        style={{
                            padding: '10px 12px',
                            borderRadius: 8,
                            background: 'var(--bg-elevated, rgba(255,255,255,0.04))',
                            border: '1px solid var(--border-subtle, rgba(255,255,255,0.08))',
                        }}
                    >
                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{a.name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                            {typeLabel(a.account_type)}
                            {a.institution ? ` · ${a.institution}` : ''}
                            {a.credit_limit != null ? ` · limit ₹${a.credit_limit.toLocaleString('en-IN')}` : ''}
                            {typeof a.transaction_count === 'number'
                                ? ` · ${a.transaction_count} txn${a.transaction_count === 1 ? '' : 's'}`
                                : ''}
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
