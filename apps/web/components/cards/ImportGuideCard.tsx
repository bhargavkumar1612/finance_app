'use client';
import { Upload } from 'lucide-react';
import Link from 'next/link';
import AppIcon from '@/components/icons/AppIcon';
import styles from './Card.module.css';

interface Props {
    payload: Record<string, unknown>;
    onAccept?: () => void;
    onReject?: () => void;
}

export default function ImportGuideCard({ payload }: Props) {
    const msg = (payload.message as string) ?? 'Upload your bank statement to import transactions.';
    const url = (payload.action_url as string) ?? '/import';
    const label = (payload.action_label as string) ?? 'Go to Import';
    const formats = (payload.supported_formats as string[]) ?? ['CSV', 'PDF'];

    return (
        <div className={`${styles.card} fade-up`}>
            <div className={styles.cardHeader}>
                <span className={styles.cardIcon}>
                    <AppIcon icon={Upload} size={18} color="var(--primary)" />
                </span>
                <span className={styles.cardTitle}>Import statement</span>
            </div>

            <p style={{ marginBottom: '0.75rem', color: 'var(--text-secondary)' }}>{msg}</p>

            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Supported formats: {formats.join(', ')}
            </p>

            <div className={styles.confirmActions} style={{ marginTop: '0.75rem' }}>
                <Link href={url} className="btn btn-primary" style={{ textDecoration: 'none' }}>
                    {label}
                </Link>
            </div>
        </div>
    );
}
