'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/AuthContext';
import styles from './page.module.css';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [error, setError] = useState('');
    const { login, isLoading } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!email.includes('@')) {
            setError('Please enter a valid email address');
            return;
        }

        try {
            await login(email);
        } catch (err: any) {
            setError(err.message || 'Login failed');
        }
    };

    return (
        <div className={styles.container}>
            <div className={styles.loginBox}>
                <h1>Welcome to Finance Copilot</h1>
                <p>Login to view your chats and transactions</p>

                <form onSubmit={handleSubmit} className={styles.form}>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="user@example.com"
                        required
                        disabled={isLoading}
                        className={styles.input}
                    />
                    {error && <div className={styles.error}>{error}</div>}
                    <button type="submit" disabled={isLoading} className="btn btn-primary" style={{ marginTop: '0.5rem' }}>
                        {isLoading ? 'Logging in...' : 'Log In'}
                    </button>
                </form>
            </div>
        </div>
    );
}
