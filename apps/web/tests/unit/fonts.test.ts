import { describe, expect, it } from 'vitest';
import {
    DEFAULT_FONT_FAMILY,
    FONT_FAMILIES,
    FONT_SIZES,
    THEME_DEFAULT_FONTS,
    getFontFamilyMeta,
    isFontFamilyId,
    isFontMode,
    isFontSizeId,
    resolveEffectiveFontFamily,
} from '@/lib/themes/fonts';

describe('resolveEffectiveFontFamily', () => {
    it('returns theme default when fontMode is default', () => {
        expect(resolveEffectiveFontFamily('paper', 'default', 'geist')).toBe('dm-sans');
        expect(resolveEffectiveFontFamily('midnight', 'default', 'lora')).toBe('geist');
        expect(resolveEffectiveFontFamily('coral', 'default', 'inter')).toBe('lora');
        expect(resolveEffectiveFontFamily('slate', 'default', 'dm-sans')).toBe('inter');
    });

    it('returns stored font when fontMode is custom', () => {
        expect(resolveEffectiveFontFamily('paper', 'custom', 'jetbrains-mono')).toBe('jetbrains-mono');
    });
});

describe('THEME_DEFAULT_FONTS', () => {
    it('maps every theme pack to a valid font', () => {
        for (const font of Object.values(THEME_DEFAULT_FONTS)) {
            expect(isFontFamilyId(font)).toBe(true);
        }
    });
});

describe('getFontFamilyMeta', () => {
    it('returns metadata for known fonts', () => {
        expect(getFontFamilyMeta('geist').label).toBe('Geist');
    });

    it('falls back to first font for unknown id', () => {
        expect(getFontFamilyMeta('bogus' as typeof DEFAULT_FONT_FAMILY).id).toBe(FONT_FAMILIES[0].id);
    });
});

describe('isFontFamilyId', () => {
    it('accepts catalog fonts', () => {
        for (const font of FONT_FAMILIES) {
            expect(isFontFamilyId(font.id)).toBe(true);
        }
    });

    it('rejects unknown values', () => {
        expect(isFontFamilyId('comic-sans')).toBe(false);
    });
});

describe('isFontSizeId', () => {
    it('accepts small, medium, large', () => {
        for (const size of FONT_SIZES) {
            expect(isFontSizeId(size.id)).toBe(true);
        }
    });

    it('rejects unknown values', () => {
        expect(isFontSizeId('huge')).toBe(false);
    });
});

describe('isFontMode', () => {
    it('accepts default and custom', () => {
        expect(isFontMode('default')).toBe(true);
        expect(isFontMode('custom')).toBe(true);
    });

    it('rejects unknown values', () => {
        expect(isFontMode('auto')).toBe(false);
    });
});
