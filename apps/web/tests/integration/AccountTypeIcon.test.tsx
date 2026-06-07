import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AccountTypeIcon from '@/components/icons/AccountTypeIcon';

describe('AccountTypeIcon', () => {
    it('renders badge with type color for bank', () => {
        const { container } = render(<AccountTypeIcon type="bank" />);
        const badge = container.querySelector('span[aria-hidden="true"]');
        expect(badge).toBeTruthy();
        expect(badge).toHaveStyle({ '--type-color': 'var(--type-bank)' });
    });

    it('renders badge for credit card', () => {
        const { container } = render(<AccountTypeIcon type="credit_card" />);
        const badge = container.querySelector('span[aria-hidden="true"]');
        expect(badge).toHaveStyle({ '--type-color': 'var(--type-credit-card)' });
    });

    it('renders home loan icon', () => {
        const { container } = render(<AccountTypeIcon type="loan" loanType="home" />);
        expect(container.querySelector('svg')).toBeTruthy();
    });

    it('renders icon without badge when showBadge is false', () => {
        const { container } = render(<AccountTypeIcon type="bank" showBadge={false} />);
        expect(container.querySelector('span[aria-hidden="true"]')).toBeNull();
    });
});
