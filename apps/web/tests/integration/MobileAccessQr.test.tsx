import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MobileAccessQr from '@/components/settings/MobileAccessQr';

function mockLocation(origin: string, hostname: string) {
    const original = window.location;
    Object.defineProperty(window, 'location', {
        configurable: true,
        value: { ...original, origin, hostname },
    });
    return () => {
        Object.defineProperty(window, 'location', { configurable: true, value: original });
    };
}

describe('MobileAccessQr', () => {
    beforeEach(() => {
        vi.stubGlobal('navigator', {
            ...navigator,
            clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
        });
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

    it('renders QR and copy button when opened from a network host', async () => {
        const restore = mockLocation('http://192.168.1.2:3000', '192.168.1.2');
        render(<MobileAccessQr />);

        expect(await screen.findByText('http://192.168.1.2:3000')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Copy link' })).toBeInTheDocument();
        expect(document.querySelector('svg')).toBeInTheDocument();
        expect(screen.getByText(/Scan with your phone camera/i)).toBeInTheDocument();
        expect(screen.queryByPlaceholderText('e.g. http://192.168.1.2:3000')).not.toBeInTheDocument();

        restore();
    });

    it('shows manual URL input on localhost and generates QR after entry', async () => {
        const user = userEvent.setup();
        const restore = mockLocation('http://localhost:3000', 'localhost');
        render(<MobileAccessQr />);

        expect(await screen.findByPlaceholderText('e.g. http://192.168.1.2:3000')).toBeInTheDocument();
        expect(screen.getByText(/Paste your Mac's LAN address/i)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Copy link' })).not.toBeInTheDocument();

        await user.type(screen.getByPlaceholderText('e.g. http://192.168.1.2:3000'), 'http://192.168.1.5:3000');

        await waitFor(() => {
            expect(screen.getByText('http://192.168.1.5:3000')).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Copy link' })).toBeInTheDocument();
            expect(document.querySelector('svg')).toBeInTheDocument();
        });

        restore();
    });

    it('shows Copied feedback after copy link is clicked', async () => {
        const user = userEvent.setup();
        const restore = mockLocation('http://192.168.1.2:3000', '192.168.1.2');
        render(<MobileAccessQr />);

        await user.click(await screen.findByRole('button', { name: 'Copy link' }));

        expect(await screen.findByRole('button', { name: 'Copied' })).toBeInTheDocument();

        restore();
    });

    it('prefills configured LAN URL from dev API on localhost', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: async () => ({ url: 'http://10.0.0.42:3000' }),
            }),
        );
        const restore = mockLocation('http://localhost:3000', 'localhost');
        render(<MobileAccessQr />);

        expect(await screen.findByText('http://10.0.0.42:3000')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Copy link' })).toBeInTheDocument();

        restore();
    });

    it('rejects localhost in manual input', async () => {
        const user = userEvent.setup();
        const restore = mockLocation('http://localhost:3000', 'localhost');
        render(<MobileAccessQr />);

        await user.type(
            await screen.findByPlaceholderText('e.g. http://192.168.1.2:3000'),
            'http://localhost:3000',
        );

        expect(screen.queryByRole('button', { name: 'Copy link' })).not.toBeInTheDocument();
        expect(screen.getByText(/Enter your computer’s LAN address/i)).toBeInTheDocument();

        restore();
    });
});
