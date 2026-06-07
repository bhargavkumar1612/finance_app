'use client';

import { AuthProvider, useAuth } from '@/lib/AuthContext';
import { LayoutProvider, useLayout } from '@/lib/LayoutContext';
import { ThemeProvider } from '@/lib/ThemeContext';
import { useIsMobileLayout } from '@/lib/useIsMobileLayout';
import Sidebar from '@/components/Sidebar';
import AppIcon from '@/components/icons/AppIcon';
import { Menu } from 'lucide-react';
import { usePathname } from 'next/navigation';
import styles from './ClientLayout.module.css';

const PAGE_TITLES: Record<string, string> = {
    '/chat': 'Chat',
    '/accounts': 'Accounts',
    '/transactions': 'Transactions',
    '/settings': 'Settings',
};

function pageTitle(pathname: string): string {
    if (pathname.startsWith('/chat')) return PAGE_TITLES['/chat'];
    if (pathname.startsWith('/accounts')) return PAGE_TITLES['/accounts'];
    if (pathname.startsWith('/transactions')) return PAGE_TITLES['/transactions'];
    if (pathname.startsWith('/settings')) return PAGE_TITLES['/settings'];
    return 'Finance Copilot';
}

function AppLayout({ children }: { children: React.ReactNode }) {
    const { user, isLoading } = useAuth();
    const pathname = usePathname();
    const { appNavOpen, toggleAppNav, closeAppNav } = useLayout();
    const isMobile = useIsMobileLayout();
    const sidebarOpen = isMobile ? appNavOpen : true;

    if (isLoading) {
        return <div className={styles.loading}>Loading...</div>;
    }

    if (pathname === '/login') {
        return <>{children}</>;
    }

    if (!user) {
        return null;
    }

    return (
        <div className={styles.shell}>
            <header className={styles.topBar}>
                <button
                    id="app-nav-toggle"
                    type="button"
                    className={styles.menuBtn}
                    aria-label="Open navigation menu"
                    aria-expanded={appNavOpen}
                    aria-controls="app-nav-drawer"
                    onClick={toggleAppNav}
                >
                    <AppIcon icon={Menu} size={20} aria-hidden />
                </button>
                <span className={styles.topBarTitle}>{pageTitle(pathname)}</span>
            </header>
            <div className={styles.shellRow}>
                {appNavOpen && (
                    <button
                        type="button"
                        className={styles.backdrop}
                        aria-label="Close navigation menu"
                        onClick={closeAppNav}
                    />
                )}
                <Sidebar isOpen={sidebarOpen} onNavigate={closeAppNav} />
                <main className={styles.main}>{children}</main>
            </div>
        </div>
    );
}

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    return (
        <AuthProvider>
            <ThemeProvider>
                <LayoutProvider>
                    <AppLayout>{children}</AppLayout>
                </LayoutProvider>
            </ThemeProvider>
        </AuthProvider>
    );
}
