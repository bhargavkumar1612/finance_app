'use client';

import { useEffect, useMemo, useState } from 'react';
import QRCode from 'react-qr-code';
import {
    initialMobileAccessUrl,
    isLocalDevHost,
    normalizeMobileAccessUrl,
    readStoredMobileAccessUrl,
    storeMobileAccessUrl,
} from '@/lib/mobileAccessUrl';
import styles from './MobileAccessQr.module.css';

async function fetchConfiguredLanUrl(): Promise<string | null> {
    try {
        const response = await fetch('/api/dev/lan-url');
        if (!response.ok) return null;
        const data = (await response.json()) as { url?: string | null };
        return data.url ?? null;
    } catch {
        return null;
    }
}

export default function MobileAccessQr() {
    const [urlInput, setUrlInput] = useState('');
    const [copied, setCopied] = useState(false);
    const [needsManualUrl, setNeedsManualUrl] = useState(false);
    const [ready, setReady] = useState(false);

    useEffect(() => {
        let cancelled = false;

        async function init() {
            const { origin, hostname } = window.location;
            const manual = isLocalDevHost(hostname);
            setNeedsManualUrl(manual);

            if (!manual) {
                setUrlInput(initialMobileAccessUrl(origin, hostname));
                setReady(true);
                return;
            }

            const stored = readStoredMobileAccessUrl();
            if (stored) {
                setUrlInput(stored);
                setReady(true);
                return;
            }

            const configured = await fetchConfiguredLanUrl();
            if (!cancelled) {
                setUrlInput(configured ?? '');
                setReady(true);
            }
        }

        void init();
        return () => {
            cancelled = true;
        };
    }, []);

    const accessUrl = useMemo(() => normalizeMobileAccessUrl(urlInput), [urlInput]);

    useEffect(() => {
        if (accessUrl && needsManualUrl) {
            storeMobileAccessUrl(accessUrl);
        }
    }, [accessUrl, needsManualUrl]);

    const handleCopy = async () => {
        if (!accessUrl || !navigator.clipboard) return;
        await navigator.clipboard.writeText(accessUrl);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 2000);
    };

    if (!ready) {
        return <p className={styles.pending}>Loading network URL…</p>;
    }

    return (
        <div className={styles.wrap}>
            {needsManualUrl && (
                <label className={styles.field}>
                    <span className={styles.fieldLabel}>Network URL</span>
                    <input
                        className={styles.input}
                        type="text"
                        inputMode="url"
                        autoComplete="off"
                        spellCheck={false}
                        value={urlInput}
                        onChange={(e) => setUrlInput(e.target.value)}
                        onBlur={(e) => setUrlInput(e.target.value.trim())}
                        placeholder="e.g. http://192.168.1.2:3000"
                        aria-describedby="mobile-access-hint"
                    />
                    {!accessUrl && (
                        <p className={styles.fieldHint}>
                            Paste your Mac&apos;s LAN address — the gray example is not filled in until you type.
                        </p>
                    )}
                </label>
            )}

            {accessUrl ? (
                <div className={styles.qrBlock}>
                    <div className={styles.qrFrame} aria-hidden="true">
                        <QRCode value={accessUrl} size={168} level="M" />
                    </div>
                    <p className={styles.url}>{accessUrl}</p>
                    <button type="button" className={styles.copyBtn} onClick={handleCopy}>
                        {copied ? 'Copied' : 'Copy link'}
                    </button>
                    <p className={styles.hint} id="mobile-access-hint">
                        Scan with your phone camera while on the same Wi‑Fi network.
                    </p>
                </div>
            ) : (
                <p className={styles.pending} id="mobile-access-hint">
                    {needsManualUrl
                        ? 'Enter your computer’s LAN address (same Wi‑Fi as your phone). Find it with ipconfig getifaddr en0 on macOS, or set DEV_LAN_URL in .env.'
                        : 'Enter a valid network URL to generate a QR code.'}
                </p>
            )}
        </div>
    );
}
