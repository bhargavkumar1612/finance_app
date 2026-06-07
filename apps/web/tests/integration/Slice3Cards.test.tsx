/**
 * Vitest tests: Slice 3 new card components
 * - ImportGuideCard
 * - TransactionDetailCard
 * - AccountCreateConfirmCard
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ImportGuideCard from '@/components/cards/ImportGuideCard';
import TransactionDetailCard from '@/components/cards/TransactionDetailCard';
import AccountCreateConfirmCard from '@/components/cards/AccountCreateConfirmCard';

// ImportGuideCard ─────────────────────────────────────────────────────────────

describe('ImportGuideCard', () => {
    it('renders heading and action link', () => {
        render(
            <ImportGuideCard
                payload={{
                    message: 'Upload your bank statement.',
                    action_url: '/import',
                    action_label: 'Go to Import',
                    supported_formats: ['CSV', 'PDF'],
                }}
            />,
        );
        expect(screen.getByText('Import statement')).toBeTruthy();
        expect(screen.getByText('Upload your bank statement.')).toBeTruthy();
        expect(screen.getByText('Go to Import')).toBeTruthy();
        expect(screen.getByText(/CSV, PDF/)).toBeTruthy();
    });

    it('falls back to default message when none provided', () => {
        render(<ImportGuideCard payload={{}} />);
        expect(screen.getByText(/Upload your bank statement/i)).toBeTruthy();
    });
});

// TransactionDetailCard ───────────────────────────────────────────────────────

describe('TransactionDetailCard', () => {
    const txns = [
        { id: 'abc', date: '2026-06-01', merchant: 'Netflix', category: 'Entertainment', amount: -499 },
        { id: 'def', date: '2026-06-02', merchant: 'Swiggy', category: 'Food', amount: -350 },
    ];

    it('renders transaction rows with merchant and amount', () => {
        render(
            <TransactionDetailCard
                payload={{ transactions: txns, message: 'Found 2 transactions.' }}
            />,
        );
        expect(screen.getAllByText(/Netflix/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Swiggy/i).length).toBeGreaterThan(0);
        expect(screen.getByText('Found 2 transactions.')).toBeTruthy();
    });

    it('shows empty state message when no transactions', () => {
        render(
            <TransactionDetailCard
                payload={{ transactions: [], message: 'No transactions found.' }}
            />,
        );
        expect(screen.getByText('No transactions found.')).toBeTruthy();
    });
});

// AccountCreateConfirmCard ────────────────────────────────────────────────────

describe('AccountCreateConfirmCard', () => {
    const previewPayload = {
        preview: true,
        account_type: 'mutual_fund',
        name: 'HDFC Top 200',
        investment_mode: 'sip',
        emi_amount: 5000,
        summary: 'Create account: mutual fund "HDFC Top 200" · mode=sip · SIP ₹5,000/mo?',
    };

    it('renders preview card with account details', () => {
        render(<AccountCreateConfirmCard payload={previewPayload} />);
        expect(screen.getAllByText(/HDFC Top 200/i).length).toBeGreaterThan(0);
        expect(screen.getByText('Confirm new account')).toBeTruthy();
        expect(screen.getByRole('button', { name: /create account/i })).toBeTruthy();
    });

    it('calls onAccept when Create account clicked', () => {
        const onAccept = vi.fn();
        render(<AccountCreateConfirmCard payload={previewPayload} onAccept={onAccept} />);
        fireEvent.click(screen.getByRole('button', { name: /create account/i }));
        expect(onAccept).toHaveBeenCalledOnce();
    });

    it('calls onReject when Cancel clicked', () => {
        const onReject = vi.fn();
        render(<AccountCreateConfirmCard payload={previewPayload} onReject={onReject} />);
        fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
        expect(onReject).toHaveBeenCalledOnce();
    });

    it('shows committed state after creation', () => {
        render(
            <AccountCreateConfirmCard
                payload={{ ...previewPayload, preview: false, id: 'some-uuid' }}
            />,
        );
        expect(screen.getByText('Account created')).toBeTruthy();
        expect(screen.getByText('Saved to your accounts')).toBeTruthy();
    });
});
