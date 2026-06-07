'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import styles from '../login/page.module.css';

export default function RegisterPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [done, setDone] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { register } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!username.trim() || !password) {
            setError('Choose a username and password');
            return;
        }
        if (password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }
        setSubmitting(true);
        try {
            const message = await register(username.trim(), password);
            setDone(message);
        } catch (err: any) {
            setError(err.message || 'Registration failed');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.loginBox}>
                <h1>Create your account</h1>
                <p>Pick any unique username — it doesn&apos;t have to be an email</p>

                {done ? (
                    <>
                        <div id="register-success" className={styles.success}>{done}</div>
                        <div className={styles.links}>
                            <Link href="/login">Back to login</Link>
                        </div>
                    </>
                ) : (
                    <>
                        <form onSubmit={handleSubmit} className={styles.form}>
                            <input
                                id="register-username"
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Username"
                                autoComplete="username"
                                required
                                disabled={submitting}
                                className={styles.input}
                            />
                            <input
                                id="register-password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Password (min 8 characters)"
                                autoComplete="new-password"
                                required
                                disabled={submitting}
                                className={styles.input}
                            />
                            {error && <div className={styles.error}>{error}</div>}
                            <button
                                id="register-submit"
                                type="submit"
                                disabled={submitting}
                                className="btn btn-primary"
                                style={{ marginTop: '0.5rem' }}
                            >
                                {submitting ? 'Creating...' : 'Create account'}
                            </button>
                        </form>
                        <div className={styles.links}>
                            <Link href="/login">Already have an account? Log in</Link>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
