import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TransactionConfirmCard from '@/components/cards/TransactionConfirmCard';

describe('TransactionConfirmCard — dual-leg transfer', () => {
    it('renders two legs for record_transfer preview', () => {
        render(
            <TransactionConfirmCard
                payload={{
                    preview: true,
                    committed: false,
                    summary: 'Record SIP transfer ₹5,000 from HDFC Bank to HDFC MF?',
                    legs: [
                        {
                            account_name: 'HDFC Bank',
                            amount: -5000,
                            nw_impact: 'transfer',
                            merchant: 'SIP — HDFC MF',
                            transaction_date: '2026-06-07',
                        },
                        {
                            account_name: 'HDFC MF',
                            amount: 5000,
                            nw_impact: 'transfer',
                            merchant: 'SIP — HDFC MF',
                            transaction_date: '2026-06-07',
                        },
                    ],
                }}
            />,
        );
        expect(screen.getByText('Confirm transfer')).toBeInTheDocument();
        expect(screen.getByText('HDFC Bank')).toBeInTheDocument();
        expect(screen.getByText('HDFC MF')).toBeInTheDocument();
        expect(screen.getAllByText(/transfer/i).length).toBeGreaterThan(0);
        expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
    });

    it('still renders single-leg expense confirm', () => {
        render(
            <TransactionConfirmCard
                payload={{
                    preview: true,
                    amount: 500,
                    merchant: 'Swiggy',
                    category: 'Food',
                    nw_impact: 'spending',
                    transaction_date: '2026-06-07',
                }}
            />,
        );
        expect(screen.getByText('Confirm transaction')).toBeInTheDocument();
        expect(screen.getByText(/₹500/)).toBeInTheDocument();
        expect(screen.getByText('Swiggy')).toBeInTheDocument();
    });
});
