import type { ThemePackId } from '@/lib/themes/packs';

export type FontFamilyId =
    | 'geist'
    | 'inter'
    | 'dm-sans'
    | 'lora'
    | 'source-serif'
    | 'jetbrains-mono';

export type FontSizeId = 'small' | 'medium' | 'large';
export type FontMode = 'default' | 'custom';

export interface FontFamilyMeta {
    id: FontFamilyId;
    label: string;
    description: string;
    sample: string;
}

export interface FontSizeMeta {
    id: FontSizeId;
    label: string;
    description: string;
}

export const DEFAULT_FONT_MODE: FontMode = 'default';
export const DEFAULT_FONT_FAMILY: FontFamilyId = 'geist';
export const DEFAULT_FONT_SIZE: FontSizeId = 'medium';

/** Curated default font per theme pack — applied when fontMode is "default". */
export const THEME_DEFAULT_FONTS: Record<ThemePackId, FontFamilyId> = {
    paper: 'dm-sans',
    midnight: 'geist',
    coral: 'lora',
    slate: 'inter',
};

export const FONT_FAMILIES: FontFamilyMeta[] = [
    {
        id: 'geist',
        label: 'Geist',
        description: 'Modern sans — crisp UI type',
        sample: 'Finance Copilot',
    },
    {
        id: 'inter',
        label: 'Inter',
        description: 'Neutral sans — balanced readability',
        sample: 'Finance Copilot',
    },
    {
        id: 'dm-sans',
        label: 'DM Sans',
        description: 'Friendly geometric sans',
        sample: 'Finance Copilot',
    },
    {
        id: 'lora',
        label: 'Lora',
        description: 'Warm serif — editorial feel',
        sample: 'Finance Copilot',
    },
    {
        id: 'source-serif',
        label: 'Source Serif',
        description: 'Classic serif — long-form reading',
        sample: 'Finance Copilot',
    },
    {
        id: 'jetbrains-mono',
        label: 'JetBrains Mono',
        description: 'Monospace — dense data views',
        sample: 'Finance Copilot',
    },
];

export const FONT_SIZES: FontSizeMeta[] = [
    { id: 'small', label: 'Small', description: 'Smaller body text for more content' },
    { id: 'medium', label: 'Medium', description: 'Default reading size' },
    { id: 'large', label: 'Large', description: 'Easier on the eyes' },
];

export function isFontFamilyId(value: string): value is FontFamilyId {
    return FONT_FAMILIES.some((f) => f.id === value);
}

export function isFontSizeId(value: string): value is FontSizeId {
    return FONT_SIZES.some((s) => s.id === value);
}

export function isFontMode(value: string): value is FontMode {
    return value === 'default' || value === 'custom';
}

export function resolveEffectiveFontFamily(
    themePack: ThemePackId,
    fontMode: FontMode,
    fontFamily: FontFamilyId,
): FontFamilyId {
    if (fontMode === 'custom') {
        return fontFamily;
    }
    return THEME_DEFAULT_FONTS[themePack];
}

export function getFontFamilyMeta(id: FontFamilyId): FontFamilyMeta {
    return FONT_FAMILIES.find((f) => f.id === id) ?? FONT_FAMILIES[0];
}
