import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockGetAccounts = vi.fn();
const mockGetProactiveHints = vi.fn();

vi.mock('@/lib/api', () => ({
    getAccounts: (...args: unknown[]) => mockGetAccounts(...args),
    getProactiveHints: (...args: unknown[]) => mockGetProactiveHints(...args),
    createAccount: vi.fn(),
    updateAccount: vi.fn(),
    deleteAccount: vi.fn(),
}));

import AccountsPage from '@/app/accounts/page';

describe('Accounts proactive hints', () => {
    beforeEach(() => {
        mockGetAccounts.mockResolvedValue([]);
        mockGetProactiveHints.mockResolvedValue({ hints: ['Log SIP payment for Test SIP'] });
    });

    it('shows proactive hints banner from /v1/hints', async () => {
        render(<AccountsPage />);
        await waitFor(() => {
            expect(screen.getByText('Suggested for you')).toBeInTheDocument();
        });
        expect(screen.getByText('Log SIP payment for Test SIP')).toBeInTheDocument();
    });

    it('dismisses a hint', async () => {
        render(<AccountsPage />);
        await waitFor(() => screen.getByText('Log SIP payment for Test SIP'));
        screen.getByRole('button', { name: /Dismiss: Log SIP payment/i }).click();
        await waitFor(() => {
            expect(screen.queryByText('Log SIP payment for Test SIP')).not.toBeInTheDocument();
        });
    });
});
