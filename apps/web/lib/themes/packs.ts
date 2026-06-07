import {
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_MODE,
    DEFAULT_FONT_SIZE,
    isFontFamilyId,
    isFontMode,
    isFontSizeId,
    type FontFamilyId,
    type FontMode,
    type FontSizeId,
} from '@/lib/themes/fonts';

export type ThemePackId = 'paper' | 'midnight' | 'coral' | 'slate';
export type DensityId = 'comfortable' | 'compact';

export interface ThemePackMeta {
    id: ThemePackId;
    label: string;
    description: string;
    mode: 'light' | 'dark';
    preview: [string, string, string];
}

export const DEFAULT_THEME_PACK: ThemePackId = 'paper';
export const DEFAULT_DENSITY: DensityId = 'comfortable';

export const THEME_STORAGE_KEY = 'fc_prefs';

export interface ThemePrefs {
    themePack: ThemePackId;
    density: DensityId;
    fontMode: FontMode;
    fontFamily: FontFamilyId;
    fontSize: FontSizeId;
}

export const DEFAULT_THEME_PREFS: ThemePrefs = {
    themePack: DEFAULT_THEME_PACK,
    density: DEFAULT_DENSITY,
    fontMode: DEFAULT_FONT_MODE,
    fontFamily: DEFAULT_FONT_FAMILY,
    fontSize: DEFAULT_FONT_SIZE,
};

export const THEME_PACKS: ThemePackMeta[] = [
    {
        id: 'paper',
        label: 'Paper',
        description: 'Warm light surfaces with high-contrast text',
        mode: 'light',
        preview: ['#f7f5f2', '#ffffff', '#4f46e5'],
    },
    {
        id: 'midnight',
        label: 'Midnight',
        description: 'Deep dark with indigo accents',
        mode: 'dark',
        preview: ['#0a0a0f', '#18181f', '#6366f1'],
    },
    {
        id: 'coral',
        label: 'Coral',
        description: 'Light with warm coral and amber accents',
        mode: 'light',
        preview: ['#faf8f6', '#ffffff', '#e85d4c'],
    },
    {
        id: 'slate',
        label: 'Slate',
        description: 'Cool blue-gray dark variant',
        mode: 'dark',
        preview: ['#0f1419', '#1a2332', '#38bdf8'],
    },
];

export function isThemePackId(value: string): value is ThemePackId {
    return THEME_PACKS.some((p) => p.id === value);
}

export function isDensityId(value: string): value is DensityId {
    return value === 'comfortable' || value === 'compact';
}

export function parseThemePrefs(raw: string | null): ThemePrefs {
    if (!raw) return DEFAULT_THEME_PREFS;
    try {
        const parsed = JSON.parse(raw) as Partial<ThemePrefs>;
        return {
            themePack: parsed.themePack && isThemePackId(parsed.themePack)
                ? parsed.themePack
                : DEFAULT_THEME_PACK,
            density: parsed.density && isDensityId(parsed.density)
                ? parsed.density
                : DEFAULT_DENSITY,
            fontMode: parsed.fontMode && isFontMode(parsed.fontMode)
                ? parsed.fontMode
                : DEFAULT_FONT_MODE,
            fontFamily: parsed.fontFamily && isFontFamilyId(parsed.fontFamily)
                ? parsed.fontFamily
                : DEFAULT_FONT_FAMILY,
            fontSize: parsed.fontSize && isFontSizeId(parsed.fontSize)
                ? parsed.fontSize
                : DEFAULT_FONT_SIZE,
        };
    } catch {
        return DEFAULT_THEME_PREFS;
    }
}
