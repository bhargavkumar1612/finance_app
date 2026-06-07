import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import SettingsPage from '@/app/settings/page';
import { ThemeProvider } from '@/lib/ThemeContext';
import { THEME_DEFAULT_FONTS } from '@/lib/themes/fonts';

const FONT_VAR_RULES = `
  [data-font="geist"] { --font-sans-active: var(--font-geist-sans); }
  [data-font="inter"] { --font-sans-active: var(--font-inter); }
  [data-font="dm-sans"] { --font-sans-active: var(--font-dm-sans); }
  [data-font="lora"] { --font-sans-active: var(--font-lora); }
  [data-font="source-serif"] { --font-sans-active: var(--font-source-serif); }
  [data-font="jetbrains-mono"] { --font-sans-active: var(--font-jetbrains-mono); }
  [data-font-size="small"] { --font-size-scale: 0.875; }
  [data-font-size="medium"] { --font-size-scale: 1; }
  [data-font-size="large"] { --font-size-scale: 1.125; }
  html {
    --font-size-base: 15px;
    font-family: var(--font-sans-active, sans-serif);
    font-size: calc(var(--font-size-base) * var(--font-size-scale));
  }
`;

function seedFontVariables() {
    const root = document.documentElement;
    root.style.setProperty('--font-geist-sans', '"Geist", sans-serif');
    root.style.setProperty('--font-inter', '"Inter", sans-serif');
    root.style.setProperty('--font-dm-sans', '"DM Sans", sans-serif');
    root.style.setProperty('--font-lora', '"Lora", serif');
    root.style.setProperty('--font-source-serif', '"Source Serif 4", serif');
    root.style.setProperty('--font-jetbrains-mono', '"JetBrains Mono", monospace');
}

function activeFontToken(id: string): string {
    return getComputedStyle(document.documentElement).getPropertyValue('--font-sans-active').trim();
}

describe('Typography DOM application', () => {
    let styleEl: HTMLStyleElement;

    beforeEach(() => {
        styleEl = document.createElement('style');
        styleEl.textContent = FONT_VAR_RULES;
        document.head.appendChild(styleEl);
        seedFontVariables();
        localStorage.clear();
    });

    afterEach(() => {
        styleEl.remove();
        document.documentElement.removeAttribute('data-font');
        document.documentElement.removeAttribute('data-font-size');
        document.documentElement.removeAttribute('data-font-mode');
        document.documentElement.removeAttribute('data-theme');
    });

    it('sets data-font and --font-sans-active for theme default on html', async () => {
        render(
            <ThemeProvider>
                <SettingsPage />
            </ThemeProvider>,
        );

        await waitFor(() => {
            expect(document.documentElement.dataset.font).toBe(THEME_DEFAULT_FONTS.paper);
            expect(activeFontToken('dm-sans')).toBe('var(--font-dm-sans)');
        });
    });

    it('updates data-font and --font-sans-active when custom font is selected', async () => {
        const user = userEvent.setup();

        render(
            <ThemeProvider>
                <SettingsPage />
            </ThemeProvider>,
        );

        await user.click(screen.getByRole('button', { name: /^Custom/i }));
        await user.click(screen.getByRole('button', { name: /JetBrains Mono/i }));

        await waitFor(() => {
            expect(document.documentElement.dataset.font).toBe('jetbrains-mono');
            expect(document.documentElement.dataset.fontMode).toBe('custom');
            expect(activeFontToken('jetbrains-mono')).toBe('var(--font-jetbrains-mono)');
        });
    });

    it('updates data-font-size and --font-size-scale when large is selected', async () => {
        const user = userEvent.setup();

        render(
            <ThemeProvider>
                <SettingsPage />
            </ThemeProvider>,
        );

        await user.click(screen.getByRole('button', { name: /^Large/i }));

        await waitFor(() => {
            expect(document.documentElement.dataset.fontSize).toBe('large');
            expect(getComputedStyle(document.documentElement).getPropertyValue('--font-size-scale').trim()).toBe(
                '1.125',
            );
        });
    });

    it('switches data-font when theme changes in default mode', async () => {
        const user = userEvent.setup();

        render(
            <ThemeProvider>
                <SettingsPage />
            </ThemeProvider>,
        );

        await user.click(screen.getByRole('button', { name: /Coral/i }));

        await waitFor(() => {
            expect(document.documentElement.dataset.font).toBe('lora');
            expect(activeFontToken('lora')).toBe('var(--font-lora)');
        });
    });
});
