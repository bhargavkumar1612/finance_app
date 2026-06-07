'use client';

import { useEffect, useState } from 'react';

export function useIsMobileLayout(breakpointPx = 768): boolean {
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        const mq = window.matchMedia(`(max-width: ${breakpointPx - 1}px)`);
        const update = () => setIsMobile(mq.matches);
        update();
        mq.addEventListener('change', update);
        return () => mq.removeEventListener('change', update);
    }, [breakpointPx]);

    return isMobile;
}
