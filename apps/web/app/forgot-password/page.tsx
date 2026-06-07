'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import styles from '../login/page.module.css';

export default function ForgotPasswordPage() {
    const [username, setUsername] = useState('');
    const [error, setError] = useState('');
    const [done, setDone] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { forgotPassword } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!username.trim()) {
            setError('Enter your username');
            return;
        }
        setSubmitting(true);
        try {
            const message = await forgotPassword(username.trim());
            setDone(message);
        } catch (err: any) {
            setError(err.message || 'Request failed');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.loginBox}>
                <h1>Reset your password</h1>
                <p>The administrator will set a new password and share it with you</p>

                {done ? (
                    <>
                        <div id="forgot-success" className={styles.success}>{done}</div>
                        <div className={styles.links}>
                            <Link href="/login">Back to login</Link>
                        </div>
                    </>
                ) : (
                    <>
                        <form onSubmit={handleSubmit} className={styles.form}>
                            <input
                                id="forgot-username"
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Username"
                                autoComplete="username"
                                required
                                disabled={submitting}
                                className={styles.input}
                            />
                            {error && <div className={styles.error}>{error}</div>}
                            <button
                                id="forgot-submit"
                                type="submit"
                                disabled={submitting}
                                className="btn btn-primary"
                                style={{ marginTop: '0.5rem' }}
                            >
                                {submitting ? 'Submitting...' : 'Request reset'}
                            </button>
                        </form>
                        <div className={styles.links}>
                            <Link href="/login">Back to login</Link>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
