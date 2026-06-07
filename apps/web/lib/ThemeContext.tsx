'use client';

import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from 'react';
import {
    resolveEffectiveFontFamily,
    type FontFamilyId,
    type FontMode,
    type FontSizeId,
} from '@/lib/themes/fonts';
import {
    DEFAULT_THEME_PREFS,
    THEME_STORAGE_KEY,
    parseThemePrefs,
    type DensityId,
    type ThemePackId,
    type ThemePrefs,
} from '@/lib/themes/packs';

interface ThemeContextValue extends ThemePrefs {
    effectiveFontFamily: FontFamilyId;
    setThemePack: (pack: ThemePackId) => void;
    setDensity: (density: DensityId) => void;
    setFontMode: (mode: FontMode) => void;
    setFontFamily: (family: FontFamilyId) => void;
    setFontSize: (size: FontSizeId) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyThemeToDom(prefs: ThemePrefs) {
    const root = document.documentElement;
    const effectiveFont = resolveEffectiveFontFamily(prefs.themePack, prefs.fontMode, prefs.fontFamily);

    root.dataset.theme = prefs.themePack;
    root.dataset.density = prefs.density;
    root.dataset.font = effectiveFont;
    root.dataset.fontSize = prefs.fontSize;
    root.dataset.fontMode = prefs.fontMode;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [prefs, setPrefs] = useState<ThemePrefs>(() => {
        if (typeof document !== 'undefined') {
            const root = document.documentElement;
            return parseThemePrefs(
                JSON.stringify({
                    themePack: root.dataset.theme,
                    density: root.dataset.density,
                    fontMode: root.dataset.fontMode,
                    fontFamily: root.dataset.font,
                    fontSize: root.dataset.fontSize,
                }),
            );
        }
        return DEFAULT_THEME_PREFS;
    });

    useEffect(() => {
        const stored = parseThemePrefs(localStorage.getItem(THEME_STORAGE_KEY));
        setPrefs(stored);
        applyThemeToDom(stored);
    }, []);

    const persist = useCallback((next: ThemePrefs) => {
        setPrefs(next);
        applyThemeToDom(next);
        localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(next));
    }, []);

    const setThemePack = useCallback(
        (themePack: ThemePackId) => {
            persist({ ...prefs, themePack });
        },
        [persist, prefs],
    );

    const setDensity = useCallback(
        (density: DensityId) => {
            persist({ ...prefs, density });
        },
        [persist, prefs],
    );

    const setFontMode = useCallback(
        (fontMode: FontMode) => {
            persist({ ...prefs, fontMode });
        },
        [persist, prefs],
    );

    const setFontFamily = useCallback(
        (fontFamily: FontFamilyId) => {
            persist({ ...prefs, fontFamily, fontMode: 'custom' });
        },
        [persist, prefs],
    );

    const setFontSize = useCallback(
        (fontSize: FontSizeId) => {
            persist({ ...prefs, fontSize });
        },
        [persist, prefs],
    );

    const effectiveFontFamily = resolveEffectiveFontFamily(
        prefs.themePack,
        prefs.fontMode,
        prefs.fontFamily,
    );

    const value = useMemo(
        () => ({
            themePack: prefs.themePack,
            density: prefs.density,
            fontMode: prefs.fontMode,
            fontFamily: prefs.fontFamily,
            fontSize: prefs.fontSize,
            effectiveFontFamily,
            setThemePack,
            setDensity,
            setFontMode,
            setFontFamily,
            setFontSize,
        }),
        [
            prefs,
            effectiveFontFamily,
            setThemePack,
            setDensity,
            setFontMode,
            setFontFamily,
            setFontSize,
        ],
    );

    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
    const ctx = useContext(ThemeContext);
    if (!ctx) {
        throw new Error('useTheme must be used within ThemeProvider');
    }
    return ctx;
}
