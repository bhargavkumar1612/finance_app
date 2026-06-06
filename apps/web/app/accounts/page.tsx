'use client';

import { useCallback, useEffect, useState } from 'react';
import {
    createAccount,
    deleteAccount,
    getAccounts,
    updateAccount,
    type Account,
    type AccountType,
    type CreateAccountRequest,
} from '@/lib/api';
import styles from './Accounts.module.css';

const ACCOUNT_TYPES: { value: AccountType; label: string }[] = [
    { value: 'bank', label: 'Bank' },
    { value: 'credit_card', label: 'Credit card' },
    { value: 'wallet', label: 'Wallet' },
    { value: 'cash', label: 'Cash' },
];

function typeLabel(t: string): string {
    return ACCOUNT_TYPES.find((x) => x.value === t)?.label ?? t.replace(/_/g, ' ');
}

const emptyForm = (): CreateAccountRequest => ({
    account_type: 'bank',
    name: '',
    institution: '',
    credit_limit: undefined,
    currency: 'INR',
    parent_account_id: undefined,
});

export default function AccountsPage() {
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState<CreateAccountRequest>(emptyForm);
    const [saving, setSaving] = useState(false);
    const [editing, setEditing] = useState<Account | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<Account | null>(null);
    const [deleting, setDeleting] = useState(false);

    const load = useCallback(async () => {
        setError(null);
        setLoading(true);
        try {
            setAccounts(await getAccounts());
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load accounts');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const resetForm = () => {
        setForm(emptyForm());
        setEditing(null);
        setShowForm(false);
    };

    const openEdit = (acc: Account) => {
        setEditing(acc);
        setForm({
            account_type: acc.account_type,
            name: acc.name,
            institution: acc.institution ?? '',
            credit_limit: acc.credit_limit ?? undefined,
            currency: acc.currency ?? 'INR',
            parent_account_id: acc.parent_account_id ?? undefined,
        });
        setShowForm(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) {
            setError('Name is required');
            return;
        }
        if (
            (form.account_type === 'credit_card' || form.account_type === 'wallet')
            && !form.parent_account_id
        ) {
            setError('Select a linked bank account for credit card or wallet accounts');
            return;
        }
        setSaving(true);
        setError(null);
        try {
            const payload: CreateAccountRequest = {
                account_type: form.account_type,
                name: form.name.trim(),
                institution: form.institution?.trim() || undefined,
                currency: form.currency || 'INR',
            };
            if (form.account_type === 'credit_card' && form.credit_limit != null && form.credit_limit > 0) {
                payload.credit_limit = form.credit_limit;
            }
            if (
                (form.account_type === 'credit_card' || form.account_type === 'wallet')
                && form.parent_account_id
            ) {
                payload.parent_account_id = form.parent_account_id;
            }
            if (editing) {
                await updateAccount(editing.id, {
                    ...payload,
                    credit_limit:
                        form.account_type === 'credit_card'
                            ? form.credit_limit ?? null
                            : null,
                    parent_account_id:
                        form.account_type === 'credit_card' || form.account_type === 'wallet'
                            ? form.parent_account_id ?? null
                            : null,
                });
            } else {
                await createAccount(payload);
            }
            resetForm();
            await load();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Save failed');
        } finally {
            setSaving(false);
        }
    };

    const runDelete = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        setError(null);
        try {
            await deleteAccount(deleteTarget.id);
            setDeleteTarget(null);
            await load();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Delete failed');
            setDeleteTarget(null);
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <h1 className={styles.title}>Accounts</h1>
                <p className={styles.subtitle}>
                    Bank accounts, credit cards, wallets, and cash — set credit limits on cards
                </p>
            </div>

            <div className={styles.toolbar}>
                <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                        if (showForm && !editing) {
                            resetForm();
                        } else {
                            setEditing(null);
                            setForm(emptyForm());
                            setShowForm(true);
                        }
                    }}
                >
                    {showForm && !editing ? 'Cancel' : 'Add account'}
                </button>
            </div>

            {error && <p className={styles.error}>{error}</p>}

            {showForm && (
                <form className={`card ${styles.formCard}`} onSubmit={handleSubmit}>
                    <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: 12 }}>
                        {editing ? 'Edit account' : 'New account'}
                    </h2>
                    <div className={styles.formGrid}>
                        <div>
                            <label className={styles.label} htmlFor="acc-type">
                                Type
                            </label>
                            <select
                                id="acc-type"
                                className={styles.select}
                                value={form.account_type}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        account_type: e.target.value as AccountType,
                                    }))
                                }
                            >
                                {ACCOUNT_TYPES.map((t) => (
                                    <option key={t.value} value={t.value}>
                                        {t.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-name">
                                Name
                            </label>
                            <input
                                id="acc-name"
                                className={styles.input}
                                value={form.name}
                                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                                placeholder="HDFC Savings"
                                required
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-inst">
                                Institution (optional)
                            </label>
                            <input
                                id="acc-inst"
                                className={styles.input}
                                value={form.institution ?? ''}
                                onChange={(e) => setForm((f) => ({ ...f, institution: e.target.value }))}
                                placeholder="HDFC Bank"
                            />
                        </div>
                        {(form.account_type === 'credit_card' || form.account_type === 'wallet') && (
                            <div>
                                <label className={styles.label} htmlFor="acc-parent">
                                    Linked bank account
                                </label>
                                <select
                                    id="acc-parent"
                                    className={styles.select}
                                    value={form.parent_account_id ?? ''}
                                    onChange={(e) =>
                                        setForm((f) => ({
                                            ...f,
                                            parent_account_id: e.target.value || undefined,
                                        }))
                                    }
                                    required
                                >
                                    <option value="">Select primary account…</option>
                                    {accounts
                                        .filter((a) => a.account_type === 'bank' || a.account_type === 'cash')
                                        .map((a) => (
                                            <option key={a.id} value={a.id}>
                                                {a.name} ({typeLabel(a.account_type)})
                                            </option>
                                        ))}
                                </select>
                                {accounts.filter((a) => a.account_type === 'bank' || a.account_type === 'cash').length === 0 && (
                                    <p className={styles.hint}>
                                        Create a bank or cash account first, then link this card to it.
                                    </p>
                                )}
                            </div>
                        )}
                        {form.account_type === 'credit_card' && (
                            <div>
                                <label className={styles.label} htmlFor="acc-limit">
                                    Credit limit (₹)
                                </label>
                                <input
                                    id="acc-limit"
                                    type="number"
                                    min={0}
                                    step={1}
                                    className={styles.input}
                                    value={form.credit_limit ?? ''}
                                    onChange={(e) =>
                                        setForm((f) => ({
                                            ...f,
                                            credit_limit: e.target.value
                                                ? Number(e.target.value)
                                                : undefined,
                                        }))
                                    }
                                    placeholder="500000"
                                />
                            </div>
                        )}
                    </div>
                    <div className={styles.formActions}>
                        <button type="submit" className="btn btn-primary" disabled={saving}>
                            {saving ? 'Saving…' : editing ? 'Save changes' : 'Create account'}
                        </button>
                        <button type="button" className="btn btn-ghost" onClick={resetForm}>
                            Cancel
                        </button>
                    </div>
                </form>
            )}

            {loading ? (
                <div className="spinner" />
            ) : accounts.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 48 }}>
                    <p className="text-muted">No accounts yet. Add one above or ask chat: “add HDFC savings account”.</p>
                </div>
            ) : (
                <div className={styles.list}>
                    {accounts.map((acc) => (
                        <div key={acc.id} className="card">
                            <div className={styles.cardRow}>
                                <div>
                                    <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>{acc.name}</h3>
                                    <p className={styles.cardMeta}>
                                        {typeLabel(acc.account_type)}
                                        {acc.institution ? ` · ${acc.institution}` : ''}
                                        {acc.credit_limit != null
                                            ? ` · limit ₹${acc.credit_limit.toLocaleString('en-IN')}`
                                            : ''}
                                        {acc.parent_account_id
                                            ? ` · linked to ${accounts.find((a) => a.id === acc.parent_account_id)?.name ?? 'bank'}`
                                            : ''}
                                        {typeof acc.transaction_count === 'number'
                                            ? ` · ${acc.transaction_count} transaction${acc.transaction_count === 1 ? '' : 's'}`
                                            : ''}
                                    </p>
                                </div>
                                <div className={styles.cardActions}>
                                    <button type="button" className="btn btn-ghost" onClick={() => openEdit(acc)}>
                                        Edit
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-ghost"
                                        style={{ color: 'var(--danger, #f87171)' }}
                                        onClick={() => setDeleteTarget(acc)}
                                    >
                                        Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {deleteTarget && (
                <div className={styles.modalBackdrop} role="dialog" aria-modal="true">
                    <div className={styles.modal}>
                        <h2 className={styles.modalTitle}>Delete account?</h2>
                        <p className={styles.modalText}>
                            Remove “{deleteTarget.name}”?
                            {(deleteTarget.transaction_count ?? 0) > 0
                                ? ' This account has transactions — delete those first.'
                                : ' This cannot be undone.'}
                        </p>
                        <div className={styles.modalActions}>
                            <button
                                type="button"
                                className="btn btn-ghost"
                                onClick={() => setDeleteTarget(null)}
                                disabled={deleting}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="btn btn-primary"
                                style={{ background: 'var(--danger, #dc2626)' }}
                                disabled={deleting || (deleteTarget.transaction_count ?? 0) > 0}
                                onClick={runDelete}
                            >
                                {deleting ? 'Deleting…' : 'Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
