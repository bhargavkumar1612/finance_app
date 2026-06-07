import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SettingsPage from '@/app/settings/page';
import { renderWithTheme } from '../renderWithTheme';

describe('SettingsPage', () => {
    beforeEach(() => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: async () => ({ url: null }),
            }),
        );
        localStorage.clear();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });
    it('renders four theme packs, typography controls, and two density options', () => {
        renderWithTheme(<SettingsPage />);

        expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Appearance' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Typography' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Density' })).toBeInTheDocument();

        expect(screen.getByRole('button', { name: /Paper/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Midnight/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Coral/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Slate/i })).toBeInTheDocument();

        expect(screen.getByRole('button', { name: /Theme default/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /^Custom/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /^Small/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /^Medium/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /^Large/i })).toBeInTheDocument();

        expect(screen.getByRole('button', { name: /Comfortable/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /^Compact/i })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Open on phone' })).toBeInTheDocument();
    });

    it('shows QR when opened from a network host', () => {
        const original = window.location;
        Object.defineProperty(window, 'location', {
            configurable: true,
            value: { ...original, origin: 'http://192.168.1.2:3000', hostname: '192.168.1.2' },
        });

        renderWithTheme(<SettingsPage />);

        expect(screen.getByText('http://192.168.1.2:3000')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Copy link' })).toBeInTheDocument();

        Object.defineProperty(window, 'location', { configurable: true, value: original });
    });

    it('prompts for LAN URL when opened on localhost', async () => {
        const original = window.location;
        Object.defineProperty(window, 'location', {
            configurable: true,
            value: { ...original, origin: 'http://localhost:3000', hostname: 'localhost' },
        });

        renderWithTheme(<SettingsPage />);

        expect(await screen.findByPlaceholderText('e.g. http://192.168.1.2:3000')).toBeInTheDocument();
        expect(screen.getByText(/Paste your Mac's LAN address/i)).toBeInTheDocument();

        Object.defineProperty(window, 'location', { configurable: true, value: original });
    });

    it('generates QR on settings page after entering LAN URL on localhost', async () => {
        const user = userEvent.setup();
        const original = window.location;
        Object.defineProperty(window, 'location', {
            configurable: true,
            value: { ...original, origin: 'http://localhost:3000', hostname: 'localhost' },
        });

        renderWithTheme(<SettingsPage />);
        const input = await screen.findByPlaceholderText('e.g. http://192.168.1.2:3000');
        await user.type(input, 'http://10.0.0.8:3000');

        await waitFor(() => {
            expect(screen.getByText('http://10.0.0.8:3000')).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Copy link' })).toBeInTheDocument();
        });

        Object.defineProperty(window, 'location', { configurable: true, value: original });
    });

    it('selects midnight theme and updates DOM', async () => {
        const user = userEvent.setup();
        renderWithTheme(<SettingsPage />);

        await user.click(screen.getByRole('button', { name: /Midnight/i }));

        await waitFor(() => {
            expect(screen.getByRole('button', { name: /Midnight/i })).toHaveAttribute('aria-pressed', 'true');
            expect(document.documentElement.dataset.theme).toBe('midnight');
        });
    });

    it('selects compact density and updates DOM', async () => {
        const user = userEvent.setup();
        renderWithTheme(<SettingsPage />);

        await user.click(screen.getByRole('button', { name: /^Compact/i }));

        await waitFor(() => {
            expect(screen.getByRole('button', { name: /^Compact/i })).toHaveAttribute('aria-pressed', 'true');
            expect(document.documentElement.dataset.density).toBe('compact');
        });
    });

    it('shows custom font picker and applies selection', async () => {
        const user = userEvent.setup();
        renderWithTheme(<SettingsPage />);

        await user.click(screen.getByRole('button', { name: /^Custom/i }));
        await user.click(screen.getByRole('button', { name: /JetBrains Mono/i }));

        await waitFor(() => {
            expect(document.documentElement.dataset.font).toBe('jetbrains-mono');
            expect(document.documentElement.dataset.fontMode).toBe('custom');
        });
    });

    it('selects large text size and updates DOM', async () => {
        const user = userEvent.setup();
        renderWithTheme(<SettingsPage />);

        await user.click(screen.getByRole('button', { name: /^Large/i }));

        await waitFor(() => {
            expect(document.documentElement.dataset.fontSize).toBe('large');
        });
    });
});

describe('SettingsPage — FinancialPersonaEditor', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    function stubPersonaFetch(body = '') {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockImplementation((url: string, init?: RequestInit) => {
                if (url.includes('/v1/persona') && (!init || init.method === 'GET' || !init.method)) {
                    return Promise.resolve({
                        ok: true,
                        status: 200,
                        text: async () => JSON.stringify({ body, traits: {}, updated_at: null }),
                    });
                }
                if (url.includes('/v1/persona') && init?.method === 'PUT') {
                    const sent = JSON.parse(init.body as string);
                    return Promise.resolve({
                        ok: true,
                        status: 200,
                        text: async () => JSON.stringify({ body: sent.body, traits: {}, updated_at: '2026-06-07T00:00:00' }),
                    });
                }
                return Promise.resolve({
                    ok: true,
                    status: 200,
                    text: async () => JSON.stringify({ url: null }),
                });
            }),
        );
    }

    it('renders Financial persona section with textarea', async () => {
        stubPersonaFetch('');
        renderWithTheme(<SettingsPage />);
        expect(await screen.findByRole('heading', { name: 'Financial persona' })).toBeInTheDocument();
        expect(screen.getByRole('textbox', { name: /Financial persona notes/i })).toBeInTheDocument();
    });

    it('Save persona button is disabled when body is unchanged', async () => {
        stubPersonaFetch('');
        renderWithTheme(<SettingsPage />);
        await screen.findByRole('heading', { name: 'Financial persona' });
        const btn = screen.getByRole('button', { name: /Save persona/i });
        expect(btn).toBeDisabled();
    });

    it('Save persona button enables after typing and shows success on save', async () => {
        stubPersonaFetch('');
        const user = userEvent.setup();
        renderWithTheme(<SettingsPage />);
        await screen.findByRole('heading', { name: 'Financial persona' });

        const textarea = screen.getByRole('textbox', { name: /Financial persona notes/i });
        await user.type(textarea, 'SIP-heavy investor');

        const btn = screen.getByRole('button', { name: /Save persona/i });
        expect(btn).not.toBeDisabled();

        await user.click(btn);

        await waitFor(() => {
            expect(screen.getByText('Persona saved.')).toBeInTheDocument();
        });
    });
});
