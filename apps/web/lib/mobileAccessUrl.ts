/** Normalize a user-entered URL for mobile LAN access. Returns null if unusable on a phone. */
export function normalizeMobileAccessUrl(raw: string): string | null {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    try {
        const parsed = new URL(trimmed.includes('://') ? trimmed : `http://${trimmed}`);
        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
        if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') return null;
        parsed.hash = '';
        parsed.search = '';
        const path = parsed.pathname.replace(/\/$/, '');
        return `${parsed.origin}${path === '' ? '' : path}`;
    } catch {
        return null;
    }
}

export function isLocalDevHost(hostname: string): boolean {
    return hostname === 'localhost' || hostname === '127.0.0.1';
}

export function initialMobileAccessUrl(origin: string, hostname: string): string {
    if (isLocalDevHost(hostname)) return '';
    return origin;
}

export const MOBILE_ACCESS_URL_STORAGE_KEY = 'fc_mobile_access_url';

export function readStoredMobileAccessUrl(): string {
    if (typeof window === 'undefined') return '';
    try {
        return window.localStorage.getItem(MOBILE_ACCESS_URL_STORAGE_KEY) ?? '';
    } catch {
        return '';
    }
}

export function storeMobileAccessUrl(url: string): void {
    if (typeof window === 'undefined') return;
    try {
        window.localStorage.setItem(MOBILE_ACCESS_URL_STORAGE_KEY, url);
    } catch {
        // ignore quota / private mode
    }
}
