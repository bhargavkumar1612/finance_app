'use client';

import { useTheme } from '@/lib/ThemeContext';
import {
    FONT_FAMILIES,
    FONT_SIZES,
    THEME_DEFAULT_FONTS,
    getFontFamilyMeta,
    type FontFamilyId,
    type FontMode,
    type FontSizeId,
} from '@/lib/themes/fonts';
import { THEME_PACKS, type DensityId, type ThemePackId } from '@/lib/themes/packs';
import MobileAccessQr from '@/components/settings/MobileAccessQr';
import FinancialPersonaEditor from '@/components/settings/FinancialPersonaEditor';
import styles from './Settings.module.css';

const DENSITY_OPTIONS = [
    { id: 'comfortable' as DensityId, label: 'Comfortable', description: 'More spacing for readability' },
    { id: 'compact' as DensityId, label: 'Compact', description: 'Fits more on screen' },
];

const FONT_MODE_OPTIONS = [
    {
        id: 'default' as FontMode,
        label: 'Theme default',
        description: 'Each color theme uses its own curated font',
    },
    {
        id: 'custom' as FontMode,
        label: 'Custom',
        description: 'Pick a font that stays the same across themes',
    },
];

export default function SettingsPage() {
    const {
        themePack,
        density,
        fontMode,
        fontFamily,
        fontSize,
        effectiveFontFamily,
        setThemePack,
        setDensity,
        setFontMode,
        setFontFamily,
        setFontSize,
    } = useTheme();

    const themeDefaultFont = getFontFamilyMeta(THEME_DEFAULT_FONTS[themePack]);
    const activeFont = getFontFamilyMeta(effectiveFontFamily);

    return (
        <div className={styles.page}>
            <header className={styles.header}>
                <h1 className={styles.title}>Settings</h1>
                <p className={styles.subtitle}>Customize appearance, typography, and layout density.</p>
            </header>

            <section className={styles.section}>
                <h2 className={styles.sectionTitle}>Appearance</h2>
                <p className={styles.sectionDesc}>Choose a color theme. Preference is saved on this device.</p>
                <div className={styles.themeGrid}>
                    {THEME_PACKS.map((pack) => (
                        <button
                            key={pack.id}
                            type="button"
                            className={`${styles.themeCard} ${themePack === pack.id ? styles.themeCardActive : ''}`}
                            onClick={() => setThemePack(pack.id as ThemePackId)}
                            aria-pressed={themePack === pack.id}
                        >
                            <div className={styles.swatches}>
                                {pack.preview.map((color) => (
                                    <span
                                        key={color}
                                        className={styles.swatch}
                                        style={{ background: color }}
                                    />
                                ))}
                            </div>
                            <span className={styles.themeLabel}>{pack.label}</span>
                            <span className={styles.themeDesc}>{pack.description}</span>
                            <span className={styles.themeMode}>{pack.mode}</span>
                        </button>
                    ))}
                </div>
            </section>

            <section className={styles.section}>
                <h2 className={styles.sectionTitle}>Typography</h2>
                <p className={styles.sectionDesc}>
                    {fontMode === 'default'
                        ? `Using ${themeDefaultFont.label} — the default font for ${THEME_PACKS.find((p) => p.id === themePack)?.label ?? 'this theme'}.`
                        : `Using ${activeFont.label} across all themes.`}
                </p>

                <div className={styles.fontModeRow}>
                    {FONT_MODE_OPTIONS.map((opt) => (
                        <button
                            key={opt.id}
                            type="button"
                            className={`${styles.fontModeBtn} ${fontMode === opt.id ? styles.fontModeBtnActive : ''}`}
                            onClick={() => setFontMode(opt.id)}
                            aria-pressed={fontMode === opt.id}
                        >
                            <span className={styles.fontModeLabel}>{opt.label}</span>
                            <span className={styles.fontModeDesc}>{opt.description}</span>
                        </button>
                    ))}
                </div>

                {fontMode === 'custom' && (
                    <div className={styles.fontGrid}>
                        {FONT_FAMILIES.map((font) => (
                            <button
                                key={font.id}
                                type="button"
                                className={`${styles.fontCard} ${fontFamily === font.id ? styles.fontCardActive : ''}`}
                                onClick={() => setFontFamily(font.id as FontFamilyId)}
                                aria-pressed={fontFamily === font.id}
                                data-font-preview={font.id}
                            >
                                <span className={styles.fontSample}>{font.sample}</span>
                                <span className={styles.fontLabel}>{font.label}</span>
                                <span className={styles.fontDesc}>{font.description}</span>
                            </button>
                        ))}
                    </div>
                )}

                <h3 className={styles.subsectionTitle}>Text size</h3>
                <div className={styles.fontSizeRow}>
                    {FONT_SIZES.map((opt) => (
                        <button
                            key={opt.id}
                            type="button"
                            className={`${styles.fontSizeBtn} ${fontSize === opt.id ? styles.fontSizeBtnActive : ''}`}
                            onClick={() => setFontSize(opt.id as FontSizeId)}
                            aria-pressed={fontSize === opt.id}
                        >
                            <span className={styles.fontSizeLabel}>{opt.label}</span>
                            <span className={styles.fontSizeDesc}>{opt.description}</span>
                        </button>
                    ))}
                </div>
            </section>

            <section className={styles.section}>
                <h2 className={styles.sectionTitle}>Density</h2>
                <p className={styles.sectionDesc}>Adjust spacing across the app.</p>
                <div className={styles.densityRow}>
                    {DENSITY_OPTIONS.map((opt) => (
                        <button
                            key={opt.id}
                            type="button"
                            className={`${styles.densityBtn} ${density === opt.id ? styles.densityBtnActive : ''}`}
                            onClick={() => setDensity(opt.id)}
                            aria-pressed={density === opt.id}
                        >
                            <span className={styles.densityLabel}>{opt.label}</span>
                            <span className={styles.densityDesc}>{opt.description}</span>
                        </button>
                    ))}
                </div>
            </section>

            <FinancialPersonaEditor />

            <section className={styles.section}>
                <h2 className={styles.sectionTitle}>Open on phone</h2>
                <p className={styles.sectionDesc}>
                    Scan the QR code from another device on the same Wi‑Fi network. Use your computer&apos;s
                    network IP — not localhost.
                </p>
                <MobileAccessQr />
            </section>

            <p className={styles.note}>
                Theme preferences are stored locally in your browser. Sync across devices is not available yet.
            </p>
        </div>
    );
}
