'use client';

import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from 'react';
import { usePathname } from 'next/navigation';

interface LayoutContextValue {
    appNavOpen: boolean;
    openAppNav: () => void;
    closeAppNav: () => void;
    toggleAppNav: () => void;
}

const LayoutContext = createContext<LayoutContextValue | null>(null);

export function LayoutProvider({ children }: { children: ReactNode }) {
    const pathname = usePathname();
    const [appNavOpen, setAppNavOpen] = useState(false);

    const openAppNav = useCallback(() => setAppNavOpen(true), []);
    const closeAppNav = useCallback(() => setAppNavOpen(false), []);
    const toggleAppNav = useCallback(() => setAppNavOpen((open) => !open), []);

    useEffect(() => {
        setAppNavOpen(false);
    }, [pathname]);

    useEffect(() => {
        if (!appNavOpen) return;
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') closeAppNav();
        };
        document.addEventListener('keydown', onKeyDown);
        return () => document.removeEventListener('keydown', onKeyDown);
    }, [appNavOpen, closeAppNav]);

    useEffect(() => {
        document.body.style.overflow = appNavOpen ? 'hidden' : '';
        return () => {
            document.body.style.overflow = '';
        };
    }, [appNavOpen]);

    const value = useMemo(
        () => ({ appNavOpen, openAppNav, closeAppNav, toggleAppNav }),
        [appNavOpen, openAppNav, closeAppNav, toggleAppNav],
    );

    return <LayoutContext.Provider value={value}>{children}</LayoutContext.Provider>;
}

export function useLayout(): LayoutContextValue {
    const ctx = useContext(LayoutContext);
    if (!ctx) {
        throw new Error('useLayout must be used within LayoutProvider');
    }
    return ctx;
}
