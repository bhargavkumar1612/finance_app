'use client';

import { useCallback, useEffect, useState } from 'react';
import { getPersona, updatePersona } from '@/lib/api';
import styles from '@/app/settings/Settings.module.css';

export default function FinancialPersonaEditor() {
    const [body, setBody] = useState('');
    const [savedBody, setSavedBody] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const data = await getPersona();
                if (!cancelled) {
                    setBody(data.body);
                    setSavedBody(data.body);
                }
            } catch (e) {
                if (!cancelled) {
                    setError(e instanceof Error ? e.message : 'Failed to load persona');
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    const handleSave = useCallback(async () => {
        setSaving(true);
        setError('');
        setMessage('');
        try {
            const data = await updatePersona({ body });
            setSavedBody(data.body);
            setMessage('Persona saved.');
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to save');
        } finally {
            setSaving(false);
        }
    }, [body]);

    const dirty = body !== savedBody;

    return (
        <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Financial persona</h2>
            <p className={styles.sectionDesc}>
                Optional notes for the copilot — income patterns, goals, tone preferences. Not used for
                balances or transactions.
            </p>
            {loading ? (
                <p className={styles.note}>Loading…</p>
            ) : (
                <>
                    <textarea
                        className={styles.personaTextarea}
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                        rows={6}
                        placeholder="e.g. Salary on 1st. SIP-heavy investor. Prefer blunt nudges."
                        aria-label="Financial persona notes"
                    />
                    <div style={{ display: 'flex', gap: 10, marginTop: 12, alignItems: 'center' }}>
                        <button
                            type="button"
                            className="btn btn-primary"
                            onClick={handleSave}
                            disabled={saving || !dirty}
                        >
                            {saving ? 'Saving…' : 'Save persona'}
                        </button>
                        {message && <span className={styles.note}>{message}</span>}
                        {error && <span style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{error}</span>}
                    </div>
                </>
            )}
        </section>
    );
}
