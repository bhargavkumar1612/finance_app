import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement } from 'react';
import { ThemeProvider } from '@/lib/ThemeContext';

export function renderWithTheme(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
    return render(ui, {
        wrapper: ({ children }) => <ThemeProvider>{children}</ThemeProvider>,
        ...options,
    });
}
