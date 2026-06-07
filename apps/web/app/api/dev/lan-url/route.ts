import { normalizeMobileAccessUrl } from '@/lib/mobileAccessUrl';

export async function GET() {
    const configured = process.env.DEV_LAN_URL?.trim();
    if (!configured) {
        return Response.json({ url: null });
    }
    return Response.json({ url: normalizeMobileAccessUrl(configured) });
}
