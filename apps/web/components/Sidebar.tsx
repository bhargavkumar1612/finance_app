'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import styles from './Sidebar.module.css';

const NAV = [
    { href: '/chat', label: 'Chat', icon: '💬' },
    { href: '/accounts', label: 'Accounts', icon: '🏦' },
    { href: '/transactions', label: 'Transactions', icon: '📋' },
];

function userInitial(email: string): string {
    const local = email.split('@')[0] ?? '';
    return (local[0] ?? '?').toUpperCase();
}

export default function Sidebar() {
    const pathname = usePathname();
    const { user, logout } = useAuth();
    return (
        <aside className={styles.sidebar}>
            <div className={styles.logo}>
                <span className={styles.logoIcon}>₹</span>
                <span className={styles.logoText}>Finance Copilot</span>
            </div>
            <nav className={styles.nav}>
                {NAV.map(({ href, label, icon }) => (
                    <Link
                        key={href}
                        href={href}
                        className={`${styles.navItem} ${pathname.startsWith(href) ? styles.active : ''}`}
                    >
                        <span className={styles.navIcon}>{icon}</span>
                        <span>{label}</span>
                    </Link>
                ))}
            </nav>
            <div className={styles.footer}>
                {user && (
                    <div className={styles.userBlock}>
                        <div className={styles.userAvatar} aria-hidden>
                            {userInitial(user.email)}
                        </div>
                        <div className={styles.userMeta}>
                            <span className={styles.userLabel}>Signed in as</span>
                            <span className={styles.userEmail} title={user.email}>
                                {user.email}
                            </span>
                        </div>
                    </div>
                )}
                <button type="button" className={styles.logoutBtn} onClick={logout}>
                    Log out
                </button>
                <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className={styles.docsLink}>
                    API Docs ↗
                </a>
            </div>
        </aside>
    );
}
