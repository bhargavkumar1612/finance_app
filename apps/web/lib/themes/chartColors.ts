/** Read chart palette from CSS variables (--chart-1 … --chart-10). */
export function getChartColors(count = 10): string[] {
    if (typeof window === 'undefined') {
        return FALLBACK_CHART_COLORS.slice(0, count);
    }
    const styles = getComputedStyle(document.documentElement);
    return Array.from({ length: count }, (_, i) => {
        const value = styles.getPropertyValue(`--chart-${i + 1}`).trim();
        return value || FALLBACK_CHART_COLORS[i % FALLBACK_CHART_COLORS.length];
    });
}

const FALLBACK_CHART_COLORS = [
    '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#64748b',
];
