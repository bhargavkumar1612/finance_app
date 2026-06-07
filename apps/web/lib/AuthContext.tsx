'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
    AUTH_TOKEN_KEY,
    AuthUser,
    forgotPassword as apiForgotPassword,
    getMe,
    login as apiLogin,
    logoutApi,
    register as apiRegister,
} from './api';

const USER_KEY = 'finance_user';
// Pages reachable without an authenticated session.
export const PUBLIC_ROUTES = ['/login', '/register', '/forgot-password'];

interface AuthContextType {
    user: AuthUser | null;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    register: (username: string, password: string) => Promise<string>;
    forgotPassword: (username: string) => Promise<string>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    isLoading: true,
    login: async () => { },
    register: async () => '',
    forgotPassword: async () => '',
    logout: () => { },
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<AuthUser | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    // On mount: if a token exists, validate it against the API.
    useEffect(() => {
        let active = true;
        const init = async () => {
            const token = localStorage.getItem(AUTH_TOKEN_KEY);
            if (!token) {
                if (active) setIsLoading(false);
                return;
            }
            try {
                const me = await getMe();
                if (active) {
                    setUser(me);
                    localStorage.setItem(USER_KEY, JSON.stringify(me));
                }
            } catch {
                localStorage.removeItem(AUTH_TOKEN_KEY);
                localStorage.removeItem(USER_KEY);
            } finally {
                if (active) setIsLoading(false);
            }
        };
        init();
        return () => {
            active = false;
        };
    }, []);

    // Redirect unauthenticated users away from protected pages.
    useEffect(() => {
        if (!isLoading && !user && !PUBLIC_ROUTES.includes(pathname)) {
            router.push('/login');
        }
    }, [isLoading, user, pathname, router]);

    const login = async (username: string, password: string) => {
        const { token, user: u } = await apiLogin(username, password);
        localStorage.setItem(AUTH_TOKEN_KEY, token);
        localStorage.setItem(USER_KEY, JSON.stringify(u));
        setUser(u);
        router.push('/chat');
    };

    const register = async (username: string, password: string) => {
        const { message } = await apiRegister(username, password);
        return message;
    };

    const forgotPassword = async (username: string) => {
        const { message } = await apiForgotPassword(username);
        return message;
    };

    const logout = () => {
        // Best-effort server-side invalidation; clear locally regardless.
        logoutApi().catch(() => { });
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setUser(null);
        router.push('/login');
    };

    return (
        <AuthContext.Provider value={{ user, isLoading, login, register, forgotPassword, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
