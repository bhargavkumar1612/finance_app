import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import InvestmentPortfolioDashboardCard from '@/components/cards/InvestmentPortfolioDashboardCard';
import InvestmentPieChartCard from '@/components/cards/InvestmentPieChartCard';
import InvestmentPnlBarsCard from '@/components/cards/InvestmentPnlBarsCard';
import SipScheduleSummaryCard from '@/components/cards/SipScheduleSummaryCard';
import FdMaturityCard from '@/components/cards/FdMaturityCard';
import CardRenderer from '@/components/cards/CardRenderer';
import { renderWithTheme } from '../renderWithTheme';

describe('InvestmentPortfolioDashboardCard', () => {
    it('renders hero totals and footer suggestions', () => {
        renderWithTheme(
            <InvestmentPortfolioDashboardCard
                payload={{
                    totals: { current: 125000, invested: 100000, pnl_amount: 25000, pnl_percent: 25 },
                    pie_by_type: [{ name: 'Mutual Fund', value: 125000 }],
                    by_liquidity: [{ label: 'Mutual Fund', current_value: 125000 }],
                    by_value: [{ name: 'Index Fund', type: 'mutual_fund', current_value: 125000 }],
                    footer_suggestions: [{ label: 'Add a fixed deposit', reason: 'Park idle cash' }],
                    message: 'Portfolio current value ₹1,25,000.',
                }}
            />,
        );
        expect(screen.getByText('Investment portfolio')).toBeInTheDocument();
        expect(screen.getAllByText(/₹1,25,000/).length).toBeGreaterThan(0);
        expect(screen.getByText(/Add a fixed deposit/)).toBeInTheDocument();
    });

    it('shows empty state when no holdings', () => {
        renderWithTheme(<InvestmentPortfolioDashboardCard payload={{ totals: { current: 0 } }} />);
        expect(screen.getByText(/No investments tracked yet/)).toBeInTheDocument();
    });
});

describe('InvestmentPnlBarsCard', () => {
    it('renders P&L bar sections', () => {
        renderWithTheme(
            <InvestmentPnlBarsCard
                payload={{
                    by_pnl_percent: [{ name: 'Winner', pnl_percent: 30 }],
                    by_pnl_amount: [{ name: 'Winner', pnl_amount: 30000 }],
                    message: 'Top performers',
                }}
            />,
        );
        expect(screen.getByText('P&L drill-down')).toBeInTheDocument();
        expect(screen.getByText('Top by %')).toBeInTheDocument();
        expect(screen.getByText('Top by ₹')).toBeInTheDocument();
    });
});

describe('SipScheduleSummaryCard', () => {
    it('renders SIP status with glossary copy', () => {
        renderWithTheme(
            <SipScheduleSummaryCard
                payload={{
                    sips: [
                        {
                            name: 'Nifty SIP',
                            emi_amount: 5000,
                            status_label: 'Already paid in June',
                            last_paid_on: '2026-06-05',
                            next_expected_on: '2026-07-05',
                            sip_paid_count: 3,
                            sip_pending_count: 9,
                        },
                    ],
                    message: '1 SIP fund(s) tracked.',
                }}
            />,
        );
        expect(screen.getByText('SIP status')).toBeInTheDocument();
        expect(screen.getByText('Nifty SIP')).toBeInTheDocument();
        expect(screen.getByText(/Already paid in June/)).toBeInTheDocument();
    });
});

describe('InvestmentPieChartCard', () => {
    it('renders conic pie with allocation data', () => {
        renderWithTheme(
            <InvestmentPieChartCard
                payload={{
                    total_invested: 100000,
                    allocation: { 'Mutual Fund': 100 },
                    pie_data: [{ name: 'Mutual Fund', value: 100000 }],
                    message: 'Portfolio allocation.',
                }}
            />,
        );
        expect(screen.getByText('Investment allocation')).toBeInTheDocument();
        expect(screen.getByText('By type')).toBeInTheDocument();
    });
});

describe('FdMaturityCard', () => {
    it('renders maturity dates for FD/RD accounts', () => {
        renderWithTheme(
            <FdMaturityCard
                payload={{
                    deposits: [
                        { name: 'HDFC FD', type: 'fixed_deposit', maturity_date: '2027-01-01' },
                    ],
                    message: 'HDFC FD: matures 2027-01-01',
                }}
            />,
        );
        expect(screen.getByText('FD / RD maturity')).toBeInTheDocument();
        expect(screen.getByText(/Matures 2027-01-01/)).toBeInTheDocument();
    });
});

describe('CardRenderer Slice 1', () => {
    it('maps investment_portfolio_dashboard ui_type', () => {
        renderWithTheme(
            <CardRenderer
                response={{
                    status: 'success',
                    ui_type: 'investment_portfolio_dashboard',
                    card_payload: {
                        totals: { current: 50000, invested: 40000, pnl_amount: 10000, pnl_percent: 25 },
                        pie_by_type: [{ name: 'MF', value: 50000 }],
                    },
                }}
            />,
        );
        expect(screen.getByText('Investment portfolio')).toBeInTheDocument();
    });
});
