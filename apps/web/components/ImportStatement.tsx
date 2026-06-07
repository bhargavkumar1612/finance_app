'use client';

import { useState, useCallback, useEffect } from 'react';
import { CheckCircle2 } from 'lucide-react';
import {
    uploadImport,
    confirmImport,
    getRecurringSuggestions,
    type NormalizedRow,
    type RecurringBillSuggestion,
} from '@/lib/api';
import AppIcon from '@/components/icons/AppIcon';
import styles from '@/app/import/Import.module.css';

type RowState = NormalizedRow & { selected: boolean };

type Stage = 'idle' | 'uploading' | 'review' | 'confirming' | 'done';

interface ImportStatementProps {
    onClose?: () => void;
    onImported?: () => void;
    compact?: boolean;
}

export default function ImportStatement({ onClose, onImported, compact }: ImportStatementProps) {
    const [stage, setStage] = useState<Stage>('idle');
    const [rows, setRows] = useState<RowState[]>([]);
    const [accountId, setAccountId] = useState('');
    const [result, setResult] = useState<{ inserted: number; errors: string[] } | null>(null);
    const [error, setError] = useState('');
    const [billSuggestions, setBillSuggestions] = useState<RecurringBillSuggestion[]>([]);

    useEffect(() => {
        if (stage !== 'done' || !result || result.inserted <= 0) {
            setBillSuggestions([]);
            return;
        }
        let cancelled = false;
        (async () => {
            try {
                const data = await getRecurringSuggestions();
                if (!cancelled && data.suggestions.length > 0) {
                    setBillSuggestions(data.suggestions.slice(0, 3));
                }
            } catch {
                /* suggestions are optional */
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [stage, result]);

    const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setStage('uploading');
        setError('');
        try {
            const data = await uploadImport(file);
            setAccountId(data.account_id);
            setRows(data.rows.map((r) => ({ ...r, selected: !r.is_duplicate })));
            setStage('review');
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : String(err));
            setStage('idle');
        }
    }, []);

    const toggleRow = (i: number) => {
        setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, selected: !r.selected } : r)));
    };

    const toggleAll = () => {
        const allSelected = rows.every((r) => r.selected);
        setRows((prev) => prev.map((r) => ({ ...r, selected: !allSelected })));
    };

    const handleConfirm = async () => {
        const selected = rows.filter((r) => r.selected);
        if (!selected.length) {
            setError(
                dupCount === rows.length
                    ? 'All rows are already in your ledger. Delete existing transactions first if you want to re-import.'
                    : 'Select at least one new row to import.',
            );
            return;
        }
        setStage('confirming');
        setError('');
        try {
            const res = await confirmImport(accountId, selected);
            setResult(res);
            setStage('done');
            onImported?.();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : String(err));
            setStage('review');
        }
    };

    const reset = () => {
        setStage('idle');
        setRows([]);
        setAccountId('');
        setResult(null);
        setError('');
    };

    const selectedCount = rows.filter((r) => r.selected).length;
    const dupCount = rows.filter((r) => r.is_duplicate).length;

    return (
        <div className={compact ? styles.compactRoot : undefined}>
            {!compact && (
                <div className={styles.header}>
                    <h2 className={styles.title}>Import statement</h2>
                    <p className={styles.subtitle}>Upload a bank CSV (HDFC-style) or PDF statement</p>
                </div>
            )}

            {(stage === 'idle' || stage === 'uploading') && (
                <div className={`card ${styles.uploadCard}`}>
                    <label className={styles.dropZone} htmlFor="import-file-input">
                        <div className={styles.dropIcon}>📂</div>
                        <p className={styles.dropTitle}>
                            {stage === 'uploading' ? 'Parsing statement…' : 'Click to upload CSV or PDF'}
                        </p>
                        <p className={styles.dropHint}>HDFC-style CSV with categories, or text-based PDF</p>
                        {stage === 'uploading' && <div className="spinner" style={{ marginTop: 12 }} />}
                    </label>
                    <input
                        id="import-file-input"
                        type="file"
                        accept=".csv,.txt,.pdf"
                        className={styles.fileInput}
                        onChange={handleUpload}
                        disabled={stage === 'uploading'}
                    />
                    {error && <p className={styles.errorText}>⚠ {error}</p>}
                </div>
            )}

            {(stage === 'review' || stage === 'confirming') && (
                <div className={styles.reviewSection}>
                    {dupCount === rows.length && rows.length > 0 && (
                        <div className={styles.dupBanner}>
                            <strong>Already imported.</strong> Every row matches a transaction already in
                            your ledger. Use <em>Delete all</em> on the Transactions page if you want to
                            replace them, then import again.
                        </div>
                    )}
                    {dupCount > 0 && dupCount < rows.length && (
                        <div className={styles.dupBanner}>
                            <strong>{dupCount} duplicate(s)</strong> skipped by default — they are already
                            in your ledger. You can still check them to force re-import (not recommended).
                        </div>
                    )}

                    <div className={styles.reviewStats}>
                        <div className={styles.stat}>
                            <span className={styles.statNum}>{rows.length}</span>
                            <span className={styles.statLabel}>Parsed rows</span>
                        </div>
                        <div className={styles.stat}>
                            <span className={`${styles.statNum} text-warning`}>{dupCount}</span>
                            <span className={styles.statLabel}>Duplicates</span>
                        </div>
                        <div className={styles.stat}>
                            <span className={`${styles.statNum} text-accent`}>{selectedCount}</span>
                            <span className={styles.statLabel}>Selected</span>
                        </div>
                    </div>

                    <div className={`card ${styles.tableCard}`}>
                        <table className={styles.table}>
                            <thead>
                                <tr>
                                    <th>
                                        <input
                                            type="checkbox"
                                            aria-label="Select all"
                                            checked={rows.length > 0 && rows.every((r) => r.selected)}
                                            onChange={toggleAll}
                                            className={styles.checkbox}
                                            disabled={stage === 'confirming'}
                                        />
                                    </th>
                                    <th>Date</th>
                                    <th>Merchant</th>
                                    <th>Category</th>
                                    <th>NW impact</th>
                                    <th style={{ textAlign: 'right' }}>Amount</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((row, i) => (
                                    <tr
                                        key={i}
                                        className={`${styles.tableRow} ${row.is_duplicate ? styles.duplicate : ''} ${row.selected ? styles.selected : ''}`}
                                        onClick={() => stage !== 'confirming' && toggleRow(i)}
                                    >
                                        <td onClick={(e) => e.stopPropagation()}>
                                            <input
                                                type="checkbox"
                                                checked={row.selected}
                                                onChange={() => toggleRow(i)}
                                                className={styles.checkbox}
                                                disabled={stage === 'confirming'}
                                            />
                                        </td>
                                        <td className={styles.dateCell}>{row.date}</td>
                                        <td className={styles.merchantCell}>
                                            {row.merchant || <span className="text-muted">—</span>}
                                        </td>
                                        <td>
                                            <span className="badge badge-muted" style={{ fontSize: '0.7rem' }}>
                                                {row.suggested_category || 'General'}
                                            </span>
                                        </td>
                                        <td>
                                            <span className="badge badge-muted" style={{ fontSize: '0.7rem' }}>
                                                {row.nw_impact || row.suggested_nw_impact || 'unknown'}
                                            </span>
                                        </td>
                                        <td
                                            className={`${styles.amountCell} ${Number(row.amount) < 0 ? 'text-danger' : 'text-success'}`}
                                        >
                                            ₹{Math.abs(Number(row.amount)).toLocaleString('en-IN', {
                                                minimumFractionDigits: 2,
                                            })}
                                        </td>
                                        <td>
                                            {row.is_duplicate ? (
                                                <span className="badge badge-warning">Duplicate</span>
                                            ) : (
                                                <span className="badge badge-success">New</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {error && <p className={styles.errorText}>⚠ {error}</p>}

                    <div className={styles.reviewActions}>
                        <button className="btn btn-ghost" onClick={reset} disabled={stage === 'confirming'}>
                            ← Upload different file
                        </button>
                        <button
                            className="btn btn-primary"
                            onClick={handleConfirm}
                            disabled={selectedCount === 0 || stage === 'confirming'}
                        >
                            {stage === 'confirming' ? (
                                <span className="spinner" style={{ width: 16, height: 16 }} />
                            ) : (
                                `Confirm ${selectedCount} transactions`
                            )}
                        </button>
                    </div>
                </div>
            )}

            {stage === 'done' && result && (
                <div className={`card ${styles.doneCard}`}>
                    <div className={styles.doneIcon}>
                        <AppIcon icon={CheckCircle2} size={32} color="var(--success)" />
                    </div>
                    <h2 className={styles.doneTitle}>
                        {result.inserted > 0 ? 'Import complete!' : 'Nothing new to import'}
                    </h2>
                    <p className={styles.doneStat}>
                        <span className={result.inserted > 0 ? 'text-success' : 'text-warning'}>
                            {result.inserted}
                        </span>{' '}
                        transactions added
                    </p>
                    {result.inserted === 0 && (
                        <p className={styles.doneHint}>
                            Selected rows were already in your ledger (duplicates).
                        </p>
                    )}
                    {result.errors.length > 0 && (
                        <div className={styles.doneErrors}>
                            {result.errors.map((e, i) => (
                                <p key={i} style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                    {e}
                                </p>
                            ))}
                        </div>
                    )}
                    {billSuggestions.length > 0 && (
                        <div className={styles.doneHint} style={{ marginTop: 16, textAlign: 'left' }}>
                            <strong>Recurring bill suggestions</strong>
                            <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                                {billSuggestions.map((s) => (
                                    <li key={s.bill_id}>
                                        {s.name} — ₹{Math.abs(s.amount).toLocaleString('en-IN')} due{' '}
                                        {s.suggested_date}
                                    </li>
                                ))}
                            </ul>
                            <p style={{ fontSize: '0.8rem', marginTop: 8 }}>
                                Confirm from Accounts → Recurring bills, or ask chat: &quot;what&apos;s due this
                                month?&quot;
                            </p>
                        </div>
                    )}
                    <div style={{ display: 'flex', gap: 10, marginTop: 20, justifyContent: 'center', flexWrap: 'wrap' }}>
                        <button className="btn btn-ghost" onClick={reset}>
                            Import more
                        </button>
                        {onClose && (
                            <button className="btn btn-primary" onClick={onClose}>
                                Done
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
