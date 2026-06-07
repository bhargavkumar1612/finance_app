import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ObligationListCard from '@/components/cards/ObligationListCard';
import RecurringBillConfirmCard from '@/components/cards/RecurringBillConfirmCard';

describe('ObligationListCard', () => {
    it('renders all obligation sections', () => {
        render(
            <ObligationListCard
                payload={{
                    message: '3 sections tracked.',
                    total_monthly_commitments: 45000,
                    sections: {
                        sips: [{ name: 'Nifty SIP', emi_amount: 5000, next_due_on: '2026-06-10' }],
                        loan_emis: [{ name: 'Home Loan', emi_amount: 25000, next_due_on: '2026-06-05' }],
                        recurring_bills: [{ name: 'Rent', amount: 15000, next_due_on: '2026-06-01' }],
                        credit_cards: [],
                    },
                }}
            />
        );
        expect(screen.getByText(/Upcoming obligations/i)).toBeInTheDocument();
        expect(screen.getByText(/Nifty SIP/i)).toBeInTheDocument();
        expect(screen.getByText(/Home Loan/i)).toBeInTheDocument();
        expect(screen.getByText(/Rent/i)).toBeInTheDocument();
        expect(screen.getByText(/₹45,000/)).toBeInTheDocument();
    });
});

describe('RecurringBillConfirmCard', () => {
    it('shows confirm details', () => {
        render(
            <RecurringBillConfirmCard
                payload={{
                    name: 'Netflix',
                    amount: 499,
                    frequency: 'monthly',
                    account_name: 'HDFC',
                    preview: true,
                    summary: 'Add Netflix?',
                }}
            />
        );
        expect(screen.getAllByText(/Netflix/i).length).toBeGreaterThan(0);
        expect(screen.getByText(/499/)).toBeInTheDocument();
        expect(screen.getByText(/HDFC/i)).toBeInTheDocument();
    });
});
