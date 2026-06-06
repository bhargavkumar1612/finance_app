'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
    bulkDeleteTransactions,
    deleteAllTransactions,
    deleteTransaction,
    getAccounts,
    getTransactions,
    type Account,
    type Transaction,
} from '@/lib/api';
import {
    EMPTY_FILTERS,
    filterTransactions,
    hasActiveFilters,
    uniqueCategories,
    uniqueSources,
    type TransactionFilterField,
    type TransactionFilters,
} from '@/lib/transactionFilters';
import ImportStatement from '@/components/ImportStatement';
import styles from './Transactions.module.css';

const FILTER_FIELDS: { value: TransactionFilterField; label: string }[] = [
    { value: 'merchant', label: 'Merchant' },
    { value: 'category', label: 'Category' },
    { value: 'subcategory', label: 'Subcategory' },
    { value: 'source', label: 'Source' },
    { value: 'account', label: 'Account' },
    { value: 'amount', label: 'Amount' },
    { value: 'date', label: 'Date' },
    { value: 'raw_description', label: 'Description' },
    { value: 'currency', label: 'Currency' },
];

function accountLabel(acc: Account): string {
    const inst = acc.institution ? ` · ${acc.institution}` : '';
    return `${acc.name}${inst}`;
}

function TransactionsPageContent() {
    const searchParams = useSearchParams();
    const [txns, setTxns] = useState<Transaction[]>([]);
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [filters, setFilters] = useState<TransactionFilters>(EMPTY_FILTERS);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showImport, setShowImport] = useState(false);
    const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);

    const load = useCallback(async () => {
        setError(null);
        setLoading(true);
        try {
            const [data, accs] = await Promise.all([getTransactions(2000), getAccounts()]);
            setTxns(data);
            setAccounts(accs);
            setSelected((prev) => {
                const ids = new Set(data.map((t) => t.id));
                return new Set([...prev].filter((id) => ids.has(id)));
            });
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load transactions');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    useEffect(() => {
        if (searchParams.get('import') === '1') {
            setShowImport(true);
        }
    }, [searchParams]);

    const filteredTxns = useMemo(() => filterTransactions(txns, filters), [txns, filters]);
    const categories = useMemo(() => uniqueCategories(txns), [txns]);
    const sources = useMemo(() => uniqueSources(txns), [txns]);
    const filtersActive = hasActiveFilters(filters);

    const allSelected =
        filteredTxns.length > 0 && filteredTxns.every((t) => selected.has(t.id));
    const someSelected = filteredTxns.some((t) => selected.has(t.id));

    const setFilter = <K extends keyof TransactionFilters>(key: K, value: TransactionFilters[K]) => {
        setFilters((prev) => ({ ...prev, [key]: value }));
    };

    const clearFilters = () => setFilters(EMPTY_FILTERS);

    const toggleAll = () => {
        if (allSelected) {
            setSelected((prev) => {
                const next = new Set(prev);
                filteredTxns.forEach((t) => next.delete(t.id));
                return next;
            });
        } else {
            setSelected((prev) => {
                const next = new Set(prev);
                filteredTxns.forEach((t) => next.add(t.id));
                return next;
            });
        }
    };

    const toggleOne = (id: string) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const handleBulkDelete = async () => {
        const ids = [...selected];
        if (ids.length === 0) return;
        if (!window.confirm(`Delete ${ids.length} transaction${ids.length === 1 ? '' : 's'}? This cannot be undone.`)) {
            return;
        }
        setDeleting(true);
        setError(null);
        try {
            const result = await bulkDeleteTransactions(ids);
            setSelected(new Set());
            await load();
            if (result.not_found.length > 0) {
                setError(`Deleted ${result.deleted}. ${result.not_found.length} could not be found.`);
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Delete failed');
        } finally {
            setDeleting(false);
        }
    };

    const runDeleteAll = async () => {
        setDeleting(true);
        setError(null);
        try {
            const result = await deleteAllTransactions();
            setSelected(new Set());
            setShowDeleteAllConfirm(false);
            await load();
            if (result.deleted === 0) {
                setError('No transactions were deleted.');
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Delete all failed');
        } finally {
            setDeleting(false);
        }
    };

    const handleDeleteOne = async (id: string) => {
        if (!window.confirm('Delete this transaction? This cannot be undone.')) return;
        setDeleting(true);
        setError(null);
        try {
            await deleteTransaction(id);
            setSelected((prev) => {
                const next = new Set(prev);
                next.delete(id);
                return next;
            });
            await load();
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Delete failed');
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <div>
                    <h1 className={styles.title}>Transactions</h1>
                    <p className={styles.subtitle}>Your unified ledger</p>
                </div>
                <div className={styles.toolbar}>
                    <button
                        type="button"
                        className={styles.importBtn}
                        onClick={() => setShowImport(true)}
                    >
                        📂 Import
                    </button>
                    {txns.length > 0 && (
                        <>
                            <span className={styles.selectionMeta}>
                                {someSelected
                                    ? `${selected.size} selected`
                                    : filtersActive
                                      ? `${filteredTxns.length} of ${txns.length}`
                                      : `${txns.length} shown`}
                            </span>
                            <button
                                type="button"
                                className={styles.deleteBtn}
                                disabled={selected.size === 0 || deleting}
                                onClick={handleBulkDelete}
                            >
                                {deleting ? 'Deleting…' : 'Delete selected'}
                            </button>
                            <button
                                type="button"
                                className={styles.deleteAllBtn}
                                disabled={deleting}
                                onClick={() => setShowDeleteAllConfirm(true)}
                            >
                                Delete all
                            </button>
                        </>
                    )}
                </div>
            </div>

            {txns.length > 0 && (
                <div className={`card ${styles.filtersCard}`}>
                    <div className={styles.searchRow}>
                        <input
                            type="search"
                            className={styles.searchInput}
                            placeholder="Search merchant, category, account, amount, date…"
                            value={filters.search}
                            onChange={(e) => setFilter('search', e.target.value)}
                            aria-label="Search transactions"
                        />
                        {filtersActive && (
                            <button type="button" className={styles.clearBtn} onClick={clearFilters}>
                                Clear filters
                            </button>
                        )}
                    </div>
                    <div className={styles.filtersGrid}>
                        <label className={styles.filterField}>
                            <span className={styles.filterLabel}>Account</span>
                            <select
                                className={styles.filterSelect}
                                value={filters.accountId}
                                onChange={(e) => setFilter('accountId', e.target.value)}
                            >
                                <option value="">All accounts</option>
                                {accounts.map((a) => (
                                    <option key={a.id} value={a.id}>
                                        {accountLabel(a)}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className={styles.filterField}>
                            <span className={styles.filterLabel}>Category</span>
                            <select
                                className={styles.filterSelect}
                                value={filters.category}
                                onChange={(e) => setFilter('category', e.target.value)}
                            >
                                <option value="">All categories</option>
                                {categories.map((c) => (
                                    <option key={c} value={c}>
                                        {c}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className={styles.filterField}>
                            <span className={styles.filterLabel}>Source</span>
                            <select
                                className={styles.filterSelect}
                                value={filters.source}
                                onChange={(e) => setFilter('source', e.target.value)}
                            >
                                <option value="">All sources</option>
                                {sources.map((s) => (
                                    <option key={s} value={s}>
                                        {s}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className={styles.filterField}>
                            <span className={styles.filterLabel}>Type</span>
                            <select
                                className={styles.filterSelect}
                                value={filters.amountKind}
                                onChange={(e) =>
                                    setFilter('amountKind', e.target.value as TransactionFilters['amountKind'])
                                }
                            >
                                <option value="all">All</option>
                                <option value="spending">Spending only</option>
                                <option value="income">Income only</option>
                            </select>
                        </label>
                        <label className={styles.filterField}>
                            <span className={styles.filterLabel}>From</span>
                            <input
                                type="date"
                                className={styles.filterSelect}
                                value={filters.dateFrom}
                                onChange={(e) => setFilter('dateFrom', e.target.value)}
                            />
                        </label>
                        <label className={styles.filterField}>
                            <span className={styles.filterLabel}>To</span>
                            <input
                                type="date"
                                className={styles.filterSelect}
                                value={filters.dateTo}
                                onChange={(e) => setFilter('dateTo', e.target.value)}
                            />
                        </label>
                    </div>
                    <div className={styles.fieldFilterRow}>
                        <span className={styles.filterLabel}>Filter field</span>
                        <select
                            className={styles.filterSelect}
                            value={filters.field}
                            onChange={(e) =>
                                setFilter('field', e.target.value as TransactionFilterField)
                            }
                        >
                            {FILTER_FIELDS.map((f) => (
                                <option key={f.value} value={f.value}>
                                    {f.label}
                                </option>
                            ))}
                        </select>
                        <input
                            type="text"
                            className={styles.fieldFilterInput}
                            placeholder="Contains…"
                            value={filters.fieldValue}
                            onChange={(e) => setFilter('fieldValue', e.target.value)}
                        />
                    </div>
                </div>
            )}

            {showDeleteAllConfirm && (
                <div
                    className={`${styles.modalOverlay} ${styles.confirmOverlay}`}
                    role="dialog"
                    aria-modal="true"
                    aria-label="Confirm delete all transactions"
                    onClick={() => !deleting && setShowDeleteAllConfirm(false)}
                >
                    <div className={styles.confirmModal} onClick={(e) => e.stopPropagation()}>
                        <h2 className={styles.confirmTitle}>Delete all transactions?</h2>
                        <p className={styles.confirmText}>
                            This will permanently remove <strong>{txns.length}</strong> transactions
                            from your ledger. Import fingerprints will be cleared so you can re-import
                            the same file later.
                        </p>
                        <div className={styles.confirmActions}>
                            <button
                                type="button"
                                className="btn btn-ghost"
                                disabled={deleting}
                                onClick={() => setShowDeleteAllConfirm(false)}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className={styles.deleteAllConfirmBtn}
                                disabled={deleting}
                                onClick={runDeleteAll}
                            >
                                {deleting ? 'Deleting…' : 'Yes, delete all'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {showImport && (
                <div
                    className={styles.modalOverlay}
                    role="dialog"
                    aria-modal="true"
                    aria-label="Import bank statement"
                    onClick={() => setShowImport(false)}
                >
                    <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
                        <button
                            type="button"
                            className={styles.modalClose}
                            onClick={() => setShowImport(false)}
                            aria-label="Close import"
                        >
                            ×
                        </button>
                        <ImportStatement
                            compact
                            onClose={() => setShowImport(false)}
                            onImported={() => {
                                load();
                            }}
                        />
                    </div>
                </div>
            )}

            {error && <div className={styles.errorBanner}>{error}</div>}

            {loading ? (
                <div className="spinner" />
            ) : txns.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 48 }}>
                    <p className="text-muted" style={{ marginBottom: 16 }}>
                        No transactions yet. Import a bank statement to get started.
                    </p>
                    <button type="button" className="btn btn-primary" onClick={() => setShowImport(true)}>
                        📂 Import statement
                    </button>
                </div>
            ) : filteredTxns.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 48 }}>
                    <p className="text-muted" style={{ marginBottom: 16 }}>
                        No transactions match your search or filters.
                    </p>
                    <button type="button" className="btn btn-ghost" onClick={clearFilters}>
                        Clear filters
                    </button>
                </div>
            ) : (
                <div className={`card ${styles.tableCard}`}>
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th className={styles.thCheck}>
                                    <input
                                        type="checkbox"
                                        checked={allSelected}
                                        onChange={toggleAll}
                                        aria-label="Select all visible transactions"
                                    />
                                </th>
                                <th className={styles.th}>Date</th>
                                <th className={styles.th}>Account</th>
                                <th className={styles.th}>Merchant</th>
                                <th className={styles.th}>Category</th>
                                <th className={styles.thRight}>Amount</th>
                                <th className={styles.th}>Source</th>
                                <th className={styles.thCheck} />
                            </tr>
                        </thead>
                        <tbody>
                            {filteredTxns.map((tx) => (
                                <tr
                                    key={tx.id}
                                    className={selected.has(tx.id) ? styles.rowSelected : undefined}
                                >
                                    <td className={styles.tdCheck}>
                                        <input
                                            type="checkbox"
                                            checked={selected.has(tx.id)}
                                            onChange={() => toggleOne(tx.id)}
                                            aria-label={`Select ${tx.merchant || 'transaction'}`}
                                        />
                                    </td>
                                    <td className={styles.td} style={{ color: 'var(--text-muted)' }}>
                                        {tx.transaction_date}
                                    </td>
                                    <td className={styles.td}>
                                        <span className={styles.accountName}>
                                            {tx.account_name || '—'}
                                        </span>
                                        {tx.account_type && (
                                            <span className={styles.accountType}>
                                                {tx.account_type.replace(/_/g, ' ')}
                                            </span>
                                        )}
                                    </td>
                                    <td className={styles.td} style={{ fontWeight: 500 }}>
                                        {tx.merchant || '—'}
                                    </td>
                                    <td className={styles.td}>
                                        <span className="badge badge-muted" style={{ fontSize: '0.7rem' }}>
                                            {tx.category || 'uncategorized'}
                                        </span>
                                    </td>
                                    <td
                                        className={styles.td}
                                        style={{
                                            textAlign: 'right',
                                            fontWeight: 600,
                                            color: tx.amount < 0 ? 'var(--danger)' : 'var(--success)',
                                        }}
                                    >
                                        ₹{Math.abs(tx.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                    </td>
                                    <td className={styles.td} style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                        {tx.source}
                                    </td>
                                    <td className={styles.tdCheck}>
                                        <button
                                            type="button"
                                            className={styles.rowDelete}
                                            disabled={deleting}
                                            onClick={() => handleDeleteOne(tx.id)}
                                            title="Delete"
                                        >
                                            ✕
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

export default function TransactionsPage() {
    return (
        <Suspense
            fallback={
                <div className={styles.page}>
                    <div className="spinner" />
                </div>
            }
        >
            <TransactionsPageContent />
        </Suspense>
    );
}
