'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from './Sidebar.module.css';

const NAV = [
    { href: '/chat', label: 'Chat', icon: '💬' },
    { href: '/accounts', label: 'Accounts', icon: '🏦' },
    { href: '/transactions', label: 'Transactions', icon: '📋' },
    { href: '/import', label: 'Import', icon: '📂' },
];

export default function Sidebar() {
    const pathname = usePathname();
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
                <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className={styles.docsLink}>
                    API Docs ↗
                </a>
            </div>
        </aside>
    );
}
