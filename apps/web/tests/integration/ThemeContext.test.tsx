import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ThemeProvider, useTheme } from '@/lib/ThemeContext';
import { THEME_STORAGE_KEY } from '@/lib/themes/packs';

function ThemeProbe() {
    const { themePack, density, fontMode, fontSize, setThemePack, setDensity, setFontMode, setFontSize } =
        useTheme();
    return (
        <div>
            <span data-testid="theme">{themePack}</span>
            <span data-testid="density">{density}</span>
            <span data-testid="fontMode">{fontMode}</span>
            <span data-testid="fontSize">{fontSize}</span>
            <button type="button" onClick={() => setThemePack('coral')}>
                Set coral
            </button>
            <button type="button" onClick={() => setDensity('compact')}>
                Set compact
            </button>
            <button type="button" onClick={() => setFontMode('custom')}>
                Set custom font
            </button>
            <button type="button" onClick={() => setFontSize('large')}>
                Set large
            </button>
        </div>
    );
}

describe('ThemeProvider', () => {
    it('applies stored prefs to DOM on mount', async () => {
        localStorage.setItem(
            THEME_STORAGE_KEY,
            JSON.stringify({ themePack: 'midnight', density: 'compact' }),
        );

        render(
            <ThemeProvider>
                <ThemeProbe />
            </ThemeProvider>,
        );

        await waitFor(() => {
            expect(document.documentElement.dataset.theme).toBe('midnight');
            expect(document.documentElement.dataset.density).toBe('compact');
            expect(document.documentElement.dataset.font).toBe('geist');
        });
        expect(screen.getByTestId('theme')).toHaveTextContent('midnight');
        expect(screen.getByTestId('density')).toHaveTextContent('compact');
    });

    it('persists theme pack changes to localStorage and DOM', async () => {
        const user = userEvent.setup();

        render(
            <ThemeProvider>
                <ThemeProbe />
            </ThemeProvider>,
        );

        await user.click(screen.getByRole('button', { name: 'Set coral' }));

        await waitFor(() => {
            expect(document.documentElement.dataset.theme).toBe('coral');
        });
        const stored = JSON.parse(localStorage.getItem(THEME_STORAGE_KEY) ?? '{}');
        expect(stored.themePack).toBe('coral');
    });

    it('persists density changes to localStorage and DOM', async () => {
        const user = userEvent.setup();

        render(
            <ThemeProvider>
                <ThemeProbe />
            </ThemeProvider>,
        );

        await user.click(screen.getByRole('button', { name: 'Set compact' }));

        await waitFor(() => {
            expect(document.documentElement.dataset.density).toBe('compact');
        });
        const stored = JSON.parse(localStorage.getItem(THEME_STORAGE_KEY) ?? '{}');
        expect(stored.density).toBe('compact');
    });

    it('applies theme default font when switching theme in default mode', async () => {
        const user = userEvent.setup();

        render(
            <ThemeProvider>
                <ThemeProbe />
            </ThemeProvider>,
        );

        await user.click(screen.getByRole('button', { name: 'Set coral' }));

        await waitFor(() => {
            expect(document.documentElement.dataset.font).toBe('lora');
        });
    });

    it('persists font size and applies data-font-size', async () => {
        const user = userEvent.setup();

        render(
            <ThemeProvider>
                <ThemeProbe />
            </ThemeProvider>,
        );

        await user.click(screen.getByRole('button', { name: 'Set large' }));

        await waitFor(() => {
            expect(document.documentElement.dataset.fontSize).toBe('large');
        });
        const stored = JSON.parse(localStorage.getItem(THEME_STORAGE_KEY) ?? '{}');
        expect(stored.fontSize).toBe('large');
    });
});
