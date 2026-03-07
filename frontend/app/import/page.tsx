'use client';
import { useState, useCallback } from 'react';
import { uploadImport, confirmImport, type NormalizedRow } from '@/lib/api';
import styles from './Import.module.css';

type RowState = NormalizedRow & { selected: boolean };

type Stage = 'idle' | 'uploading' | 'review' | 'confirming' | 'done';

export default function ImportPage() {
    const [stage, setStage] = useState<Stage>('idle');
    const [rows, setRows] = useState<RowState[]>([]);
    const [accountId, setAccountId] = useState('');
    const [result, setResult] = useState<{ inserted: number; errors: string[] } | null>(null);
    const [error, setError] = useState('');

    const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setStage('uploading');
        setError('');
        try {
            const data = await uploadImport(file);
            setAccountId(data.account_id);
            setRows(data.rows.map(r => ({ ...r, selected: !r.is_duplicate })));
            setStage('review');
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : String(err));
            setStage('idle');
        }
    }, []);

    const toggleRow = (i: number) => {
        setRows(prev => prev.map((r, idx) => idx === i ? { ...r, selected: !r.selected } : r));
    };
    const toggleAll = () => {
        const allSelected = rows.every(r => r.selected);
        setRows(prev => prev.map(r => ({ ...r, selected: !allSelected })));
    };

    const handleConfirm = async () => {
        const selected = rows.filter(r => r.selected);
        if (!selected.length) return;
        setStage('confirming');
        setError('');
        try {
            const res = await confirmImport(accountId, selected);
            setResult(res);
            setStage('done');
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

    const selectedCount = rows.filter(r => r.selected).length;
    const dupCount = rows.filter(r => r.is_duplicate).length;

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <h1 className={styles.title}>Import Statement</h1>
                <p className={styles.subtitle}>Upload a bank CSV (HDFC, ICICI, SBI) or PDF statement</p>
            </div>

            {(stage === 'idle' || stage === 'uploading') && (
                <div className={`card ${styles.uploadCard}`}>
                    <label className={styles.dropZone} htmlFor="import-file">
                        <div className={styles.dropIcon}>📂</div>
                        <p className={styles.dropTitle}>
                            {stage === 'uploading' ? 'Parsing statement…' : 'Click to upload CSV or PDF'}
                        </p>
                        <p className={styles.dropHint}>Supported: HDFC-style CSV, text-based PDF statements</p>
                        {stage === 'uploading' && <div className="spinner" style={{ marginTop: 12 }} />}
                    </label>
                    <input id="import-file" type="file" accept=".csv,.txt,.pdf" className={styles.fileInput} onChange={handleUpload} disabled={stage === 'uploading'} />
                    {error && <p className={styles.errorText}>⚠ {error}</p>}
                </div>
            )}

            {(stage === 'review' || stage === 'confirming') && (
                <div className={styles.reviewSection}>
                    <div className={styles.reviewStats}>
                        <div className={styles.stat}><span className={styles.statNum}>{rows.length}</span><span className={styles.statLabel}>Parsed rows</span></div>
                        <div className={styles.stat}><span className={`${styles.statNum} text-warning`}>{dupCount}</span><span className={styles.statLabel}>Duplicates</span></div>
                        <div className={styles.stat}><span className={`${styles.statNum} text-accent`}>{selectedCount}</span><span className={styles.statLabel}>Selected</span></div>
                    </div>

                    <div className={`card ${styles.tableCard}`}>
                        <table className={styles.table}>
                            <thead>
                                <tr>
                                    <th><input type="checkbox" aria-label="Select all" checked={rows.length > 0 && rows.every(r => r.selected)} onChange={toggleAll} className={styles.checkbox} disabled={stage === 'confirming'} /></th>
                                    <th>Date</th><th>Merchant</th><th style={{ textAlign: 'right' }}>Amount</th><th>Confidence</th><th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((row, i) => (
                                    <tr key={i} className={`${styles.tableRow} ${row.is_duplicate ? styles.duplicate : ''} ${row.selected ? styles.selected : ''}`} onClick={() => stage !== 'confirming' && toggleRow(i)}>
                                        <td onClick={e => e.stopPropagation()}><input type="checkbox" checked={row.selected} onChange={() => toggleRow(i)} className={styles.checkbox} disabled={stage === 'confirming'} /></td>
                                        <td className={styles.dateCell}>{row.date}</td>
                                        <td className={styles.merchantCell}>{row.merchant || <span className="text-muted">—</span>}</td>
                                        <td className={`${styles.amountCell} ${Number(row.amount) < 0 ? 'text-danger' : 'text-success'}`}>₹{Math.abs(Number(row.amount)).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                        <td>{row.confidence !== undefined && row.confidence !== null ? <ConfidenceBadge score={row.confidence} /> : <span className="text-muted">—</span>}</td>
                                        <td>{row.is_duplicate ? <span className="badge badge-warning">Duplicate</span> : <span className="badge badge-success">New</span>}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {error && <p className={styles.errorText}>⚠ {error}</p>}

                    <div className={styles.reviewActions}>
                        <button className="btn btn-ghost" onClick={reset} disabled={stage === 'confirming'}>← Upload different file</button>
                        <button className="btn btn-primary" onClick={handleConfirm} disabled={selectedCount === 0 || stage === 'confirming'} id="import-confirm">
                            {stage === 'confirming' ? <span className="spinner" style={{ width: 16, height: 16 }} /> : `Confirm ${selectedCount} transactions`}
                        </button>
                    </div>
                </div>
            )}

            {stage === 'confirming' && (
                <div className={styles.reviewSection} style={{ marginTop: 20 }}>
                    <p className="text-muted">Adding transactions to ledger…</p>
                </div>
            )}

            {stage === 'done' && result && (
                <div className={`card ${styles.doneCard}`}>
                    <div className={styles.doneIcon}>✓</div>
                    <h2 className={styles.doneTitle}>Import complete!</h2>
                    <p className={styles.doneStat}><span className="text-success">{result.inserted}</span> transactions added to ledger</p>
                    {result.errors.length > 0 && (
                        <div className={styles.doneErrors}>
                            <p className="text-warning" style={{ fontSize: '0.85rem', marginBottom: 6 }}>Some rows had errors:</p>
                            {result.errors.map((e, i) => <p key={i} style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{e}</p>)}
                        </div>
                    )}
                    <div style={{ display: 'flex', gap: 10, marginTop: 20, justifyContent: 'center' }}>
                        <button className="btn btn-ghost" onClick={reset}>Import more</button>
                    </div>
                </div>
            )}
        </div>
    );
}

function ConfidenceBadge({ score }: { score: number }) {
    const pct = Math.round(score * 100);
    const cls = pct >= 80 ? 'badge-success' : pct >= 50 ? 'badge-warning' : 'badge-danger';
    return <span className={`badge ${cls}`}>{pct}%</span>;
}
