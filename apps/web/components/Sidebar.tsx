'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { IndianRupee, Landmark, List, MessageSquare, Settings } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';
import AppIcon from '@/components/icons/AppIcon';
import UserMenu from '@/components/UserMenu';
import styles from './Sidebar.module.css';

const NAV = [
    { href: '/chat', label: 'Chat', icon: MessageSquare },
    { href: '/accounts', label: 'Accounts', icon: Landmark },
    { href: '/transactions', label: 'Transactions', icon: List },
    { href: '/settings', label: 'Settings', icon: Settings },
] as const;

function userInitial(email: string): string {
    const local = email.split('@')[0] ?? '';
    return (local[0] ?? '?').toUpperCase();
}

interface SidebarProps {
    isOpen?: boolean;
    onNavigate?: () => void;
}

export default function Sidebar({ isOpen = false, onNavigate }: SidebarProps) {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    const handleLogout = () => {
        onNavigate?.();
        logout();
    };

    return (
        <aside
            id="app-nav-drawer"
            className={`${styles.sidebar} ${isOpen ? styles.open : ''}`}
            aria-hidden={isOpen ? undefined : true}
        >
            <div className={styles.logo}>
                <span className={styles.logoIcon}>
                    <AppIcon icon={IndianRupee} size={20} color="white" strokeWidth={2.5} />
                </span>
                <span className={styles.logoText}>Finance Copilot</span>
            </div>
            <nav className={styles.nav}>
                {NAV.map(({ href, label, icon }) => (
                    <Link
                        key={href}
                        href={href}
                        className={`${styles.navItem} ${pathname.startsWith(href) ? styles.active : ''}`}
                        onClick={onNavigate}
                    >
                        <span className={styles.navIcon}>
                            <AppIcon icon={icon} size={18} />
                        </span>
                        <span>{label}</span>
                    </Link>
                ))}
            </nav>
            <div className={styles.footer}>
                {user && (
                    <UserMenu
                        email={user.email}
                        initial={userInitial(user.email)}
                        onNavigate={onNavigate}
                        onLogout={handleLogout}
                    />
                )}
                <a
                    href="http://localhost:8000/docs"
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.docsLink}
                    onClick={onNavigate}
                >
                    API Docs ↗
                </a>
            </div>
        </aside>
    );
}
