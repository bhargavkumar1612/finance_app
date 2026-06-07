import { describe, expect, it } from 'vitest';
import {
    DEFAULT_THEME_PREFS,
    isDensityId,
    isThemePackId,
    parseThemePrefs,
    THEME_PACKS,
} from '@/lib/themes/packs';

describe('parseThemePrefs', () => {
    it('returns defaults for null', () => {
        expect(parseThemePrefs(null)).toEqual(DEFAULT_THEME_PREFS);
    });

    it('parses valid JSON', () => {
        expect(parseThemePrefs(JSON.stringify({ themePack: 'midnight', density: 'compact' }))).toEqual({
            themePack: 'midnight',
            density: 'compact',
            fontMode: 'default',
            fontFamily: 'geist',
            fontSize: 'medium',
        });
    });

    it('parses font preferences', () => {
        expect(
            parseThemePrefs(
                JSON.stringify({
                    themePack: 'coral',
                    density: 'comfortable',
                    fontMode: 'custom',
                    fontFamily: 'jetbrains-mono',
                    fontSize: 'large',
                }),
            ),
        ).toEqual({
            themePack: 'coral',
            density: 'comfortable',
            fontMode: 'custom',
            fontFamily: 'jetbrains-mono',
            fontSize: 'large',
        });
    });

    it('falls back to paper for invalid theme pack', () => {
        expect(parseThemePrefs(JSON.stringify({ themePack: 'bogus', density: 'compact' }))).toEqual({
            themePack: 'paper',
            density: 'compact',
            fontMode: 'default',
            fontFamily: 'geist',
            fontSize: 'medium',
        });
    });

    it('falls back to comfortable for invalid density', () => {
        expect(parseThemePrefs(JSON.stringify({ themePack: 'coral', density: 'wide' }))).toEqual({
            themePack: 'coral',
            density: 'comfortable',
            fontMode: 'default',
            fontFamily: 'geist',
            fontSize: 'medium',
        });
    });

    it('returns defaults for malformed JSON', () => {
        expect(parseThemePrefs('not-json')).toEqual(DEFAULT_THEME_PREFS);
    });
});

describe('isThemePackId', () => {
    it('accepts known packs', () => {
        for (const pack of THEME_PACKS) {
            expect(isThemePackId(pack.id)).toBe(true);
        }
    });

    it('rejects unknown values', () => {
        expect(isThemePackId('neon')).toBe(false);
    });
});

describe('isDensityId', () => {
    it('accepts comfortable and compact', () => {
        expect(isDensityId('comfortable')).toBe(true);
        expect(isDensityId('compact')).toBe(true);
    });

    it('rejects unknown values', () => {
        expect(isDensityId('spacious')).toBe(false);
    });
});
