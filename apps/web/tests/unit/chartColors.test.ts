import { afterEach, describe, expect, it, vi } from 'vitest';
import { getChartColors } from '@/lib/themes/chartColors';

describe('getChartColors', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('returns fallback colors when window is undefined', () => {
        vi.stubGlobal('window', undefined);
        const colors = getChartColors(3);
        expect(colors).toHaveLength(3);
        expect(colors[0]).toBe('#6366f1');
        expect(colors[1]).toBe('#10b981');
        expect(colors[2]).toBe('#f59e0b');
    });

    it('reads CSS variables from document root', () => {
        vi.spyOn(window, 'getComputedStyle').mockReturnValue({
            getPropertyValue: (name: string) => {
                if (name === '--chart-1') return '#111111';
                if (name === '--chart-2') return '#222222';
                return '';
            },
        } as CSSStyleDeclaration);

        const colors = getChartColors(2);
        expect(colors[0]).toBe('#111111');
        expect(colors[1]).toBe('#222222');
    });

    it('uses fallback when CSS variable is empty', () => {
        vi.spyOn(window, 'getComputedStyle').mockReturnValue({
            getPropertyValue: () => '',
        } as CSSStyleDeclaration);

        const colors = getChartColors(1);
        expect(colors[0]).toBe('#6366f1');
    });
});
