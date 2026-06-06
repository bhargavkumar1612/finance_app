'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** Legacy route — import lives on the Transactions page. */
export default function ImportPage() {
    const router = useRouter();
    useEffect(() => {
        router.replace('/transactions?import=1');
    }, [router]);
    return (
        <div style={{ padding: 32, textAlign: 'center' }}>
            <p className="text-muted">Redirecting to Transactions…</p>
        </div>
    );
}
