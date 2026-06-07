'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import styles from './page.module.css';

export default function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { login } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!username.trim() || !password) {
            setError('Enter your username and password');
            return;
        }
        setSubmitting(true);
        try {
            await login(username.trim(), password);
        } catch (err: any) {
            setError(err.message || 'Login failed');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.loginBox}>
                <h1>Welcome to Finance Copilot</h1>
                <p>Log in to view your chats and transactions</p>

                <form onSubmit={handleSubmit} className={styles.form}>
                    <input
                        id="login-username"
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
                        id="login-password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Password"
                        autoComplete="current-password"
                        required
                        disabled={submitting}
                        className={styles.input}
                    />
                    {error && <div className={styles.error}>{error}</div>}
                    <button
                        id="login-submit"
                        type="submit"
                        disabled={submitting}
                        className="btn btn-primary"
                        style={{ marginTop: '0.5rem' }}
                    >
                        {submitting ? 'Logging in...' : 'Log In'}
                    </button>
                </form>

                <div className={styles.links}>
                    <Link href="/forgot-password">Forgot password?</Link>
                    <Link href="/register">Create an account</Link>
                </div>
            </div>
        </div>
    );
}
