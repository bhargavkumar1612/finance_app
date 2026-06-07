'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LogOut, Settings } from 'lucide-react';
import AppIcon from '@/components/icons/AppIcon';
import styles from './UserMenu.module.css';

interface UserMenuProps {
    email: string;
    initial: string;
    onNavigate?: () => void;
    onLogout: () => void;
}

export default function UserMenu({ email, initial, onNavigate, onLogout }: UserMenuProps) {
    const [open, setOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    useEffect(() => {
        if (!open) return;
        const onDocClick = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', onDocClick);
        return () => document.removeEventListener('mousedown', onDocClick);
    }, [open]);

    const handleSettings = () => {
        setOpen(false);
        onNavigate?.();
        router.push('/settings');
    };

    const handleLogout = () => {
        setOpen(false);
        onNavigate?.();
        onLogout();
    };

    return (
        <div className={styles.wrap} ref={menuRef}>
            <button
                id="user-menu-trigger"
                type="button"
                className={styles.trigger}
                aria-expanded={open}
                aria-haspopup="menu"
                onClick={() => setOpen((v) => !v)}
            >
                <div className={styles.avatar} aria-hidden>
                    {initial}
                </div>
                <div className={styles.meta}>
                    <span className={styles.label}>Signed in as</span>
                    <span className={styles.email} title={email}>
                        {email}
                    </span>
                </div>
            </button>
            {open && (
                <div className={styles.menu} role="menu">
                    <button type="button" className={styles.menuItem} role="menuitem" onClick={handleSettings}>
                        <AppIcon icon={Settings} size={16} />
                        Settings
                    </button>
                    <button type="button" className={styles.menuItem} role="menuitem" onClick={handleLogout}>
                        <AppIcon icon={LogOut} size={16} />
                        Log out
                    </button>
                </div>
            )}
        </div>
    );
}
