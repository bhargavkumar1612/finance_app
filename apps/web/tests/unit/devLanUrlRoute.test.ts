import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { GET } from '@/app/api/dev/lan-url/route';

describe('GET /api/dev/lan-url', () => {
    beforeEach(() => {
        vi.unstubAllEnvs();
    });

    afterEach(() => {
        vi.unstubAllEnvs();
    });

    it('returns null when DEV_LAN_URL is unset', async () => {
        delete process.env.DEV_LAN_URL;
        const response = await GET();
        expect(await response.json()).toEqual({ url: null });
    });

    it('returns normalized URL when DEV_LAN_URL is set', async () => {
        vi.stubEnv('DEV_LAN_URL', 'http://192.168.1.2:3000/');
        const response = await GET();
        expect(await response.json()).toEqual({ url: 'http://192.168.1.2:3000' });
    });
});
