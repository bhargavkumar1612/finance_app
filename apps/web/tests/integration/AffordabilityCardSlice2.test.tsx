import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AffordabilityCard from '@/components/cards/AffordabilityCard';
import { renderWithTheme } from '../renderWithTheme';

const BASE_PAYLOAD = {
    safe_emi_estimate: 15000,
    risk_level: 'low',
    net_worth: 500000,
    monthly_spend: 40000,
    message: 'Finances look healthy.',
};

describe('AffordabilityCard — Slice 2 commitments section', () => {
    it('shows commitments section when total_commitments is non-zero', () => {
        renderWithTheme(
            <AffordabilityCard
                payload={{
                    ...BASE_PAYLOAD,
                    total_commitments: 45000,
                    commitments: {
                        loan_emis: 30000,
                        sip_emis: 10000,
                        recurring_bills: 5000,
                        cc_commitments: 0,
                    },
                }}
            />,
        );
        expect(screen.getByText('Monthly commitments')).toBeInTheDocument();
        expect(screen.getByText(/₹45,000/)).toBeInTheDocument();
    });

    it('shows EMI and SIP breakdown line', () => {
        renderWithTheme(
            <AffordabilityCard
                payload={{
                    ...BASE_PAYLOAD,
                    total_commitments: 40000,
                    commitments: {
                        loan_emis: 30000,
                        sip_emis: 10000,
                        recurring_bills: 0,
                        cc_commitments: 0,
                    },
                }}
            />,
        );
        expect(screen.getAllByText(/EMI/).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/SIP/).length).toBeGreaterThan(0);
    });

    it('hides commitments section when total_commitments is 0', () => {
        renderWithTheme(
            <AffordabilityCard
                payload={{
                    ...BASE_PAYLOAD,
                    total_commitments: 0,
                    commitments: {
                        loan_emis: 0,
                        sip_emis: 0,
                        recurring_bills: 0,
                        cc_commitments: 0,
                    },
                }}
            />,
        );
        expect(screen.queryByText('Monthly commitments')).not.toBeInTheDocument();
    });

    it('renders risk badge correctly for high risk', () => {
        renderWithTheme(
            <AffordabilityCard
                payload={{
                    ...BASE_PAYLOAD,
                    safe_emi_estimate: 0,
                    risk_level: 'high',
                    total_commitments: 90000,
                    commitments: { loan_emis: 90000, sip_emis: 0, recurring_bills: 0, cc_commitments: 0 },
                }}
            />,
        );
        expect(screen.getByText('High Risk')).toBeInTheDocument();
    });
});
