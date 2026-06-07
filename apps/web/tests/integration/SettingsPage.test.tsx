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
