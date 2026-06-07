import type { Metadata } from 'next';
import Script from 'next/script';
import {
    DM_Sans,
    Geist,
    Geist_Mono,
    Inter,
    JetBrains_Mono,
    Lora,
    Source_Serif_4,
} from 'next/font/google';
import './globals.css';
import ClientLayout from './ClientLayout';
import { DEFAULT_THEME_PREFS, THEME_STORAGE_KEY } from '@/lib/themes/packs';
import { THEME_DEFAULT_FONTS } from '@/lib/themes/fonts';

const geistSans = Geist({
    variable: '--font-geist-sans',
    subsets: ['latin'],
});

const geistMono = Geist_Mono({
    variable: '--font-geist-mono',
    subsets: ['latin'],
});

const inter = Inter({
    variable: '--font-inter',
    subsets: ['latin'],
});

const dmSans = DM_Sans({
    variable: '--font-dm-sans',
    subsets: ['latin'],
});

const lora = Lora({
    variable: '--font-lora',
    subsets: ['latin'],
});

const sourceSerif = Source_Serif_4({
    variable: '--font-source-serif',
    subsets: ['latin'],
});

const jetbrainsMono = JetBrains_Mono({
    variable: '--font-jetbrains-mono',
    subsets: ['latin'],
});

const fontVariables = [
    geistSans.variable,
    geistMono.variable,
    inter.variable,
    dmSans.variable,
    lora.variable,
    sourceSerif.variable,
    jetbrainsMono.variable,
].join(' ');

export const metadata: Metadata = {
    title: 'Finance Copilot',
    description: 'AI-powered personal finance chat (India-focused)',
};

export const viewport = {
    width: 'device-width',
    initialScale: 1,
};

const themeFlashScript = `(function(){try{var k='${THEME_STORAGE_KEY}';var d=${JSON.stringify(DEFAULT_THEME_PREFS)};var tf=${JSON.stringify(THEME_DEFAULT_FONTS)};var r=localStorage.getItem(k);if(r){var p=JSON.parse(r);if(p.themePack)d.themePack=p.themePack;if(p.density)d.density=p.density;if(p.fontMode)d.fontMode=p.fontMode;if(p.fontFamily)d.fontFamily=p.fontFamily;if(p.fontSize)d.fontSize=p.fontSize;}var eff=d.fontMode==='custom'?d.fontFamily:(tf[d.themePack]||d.fontFamily);document.documentElement.dataset.theme=d.themePack;document.documentElement.dataset.density=d.density;document.documentElement.dataset.font=eff;document.documentElement.dataset.fontSize=d.fontSize;document.documentElement.dataset.fontMode=d.fontMode;}catch(e){document.documentElement.dataset.theme='paper';document.documentElement.dataset.density='comfortable';document.documentElement.dataset.font='dm-sans';document.documentElement.dataset.fontSize='medium';document.documentElement.dataset.fontMode='default';}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html
            lang="en"
            suppressHydrationWarning
            className={fontVariables}
            data-theme={DEFAULT_THEME_PREFS.themePack}
            data-density={DEFAULT_THEME_PREFS.density}
            data-font="dm-sans"
            data-font-size={DEFAULT_THEME_PREFS.fontSize}
            data-font-mode={DEFAULT_THEME_PREFS.fontMode}
        >
            <head>
                <Script id="theme-flash" strategy="beforeInteractive">
                    {themeFlashScript}
                </Script>
            </head>
            <body>
                <ClientLayout>
                    {children}
                </ClientLayout>
            </body>
        </html>
    );
}
