import { describe, expect, it } from 'vitest';
import {
    initialMobileAccessUrl,
    isLocalDevHost,
    normalizeMobileAccessUrl,
} from '@/lib/mobileAccessUrl';

describe('mobileAccessUrl', () => {
    it('rejects localhost URLs', () => {
        expect(normalizeMobileAccessUrl('http://localhost:3000')).toBeNull();
        expect(normalizeMobileAccessUrl('http://127.0.0.1:3000')).toBeNull();
    });

    it('accepts LAN URLs', () => {
        expect(normalizeMobileAccessUrl('http://192.168.1.2:3000')).toBe('http://192.168.1.2:3000');
        expect(normalizeMobileAccessUrl('192.168.1.2:3000')).toBe('http://192.168.1.2:3000');
    });

    it('strips trailing slash from path root', () => {
        expect(normalizeMobileAccessUrl('http://192.168.1.2:3000/')).toBe('http://192.168.1.2:3000');
    });

    it('detects local dev hosts', () => {
        expect(isLocalDevHost('localhost')).toBe(true);
        expect(isLocalDevHost('192.168.1.2')).toBe(false);
    });

    it('prefills origin when not on localhost', () => {
        expect(initialMobileAccessUrl('http://192.168.1.2:3000', '192.168.1.2')).toBe(
            'http://192.168.1.2:3000',
        );
        expect(initialMobileAccessUrl('http://localhost:3000', 'localhost')).toBe('');
    });

    it('rejects empty and unsupported URLs', () => {
        expect(normalizeMobileAccessUrl('')).toBeNull();
        expect(normalizeMobileAccessUrl('   ')).toBeNull();
        expect(normalizeMobileAccessUrl('ftp://192.168.1.2:3000')).toBeNull();
    });

    it('accepts https LAN URLs', () => {
        expect(normalizeMobileAccessUrl('https://192.168.1.2:3000')).toBe('https://192.168.1.2:3000');
    });

    it('treats 127.0.0.1 as local dev host', () => {
        expect(isLocalDevHost('127.0.0.1')).toBe(true);
    });
});
