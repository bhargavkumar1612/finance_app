import { describe, expect, it } from 'vitest';
import {
    Banknote,
    Building2,
    Car,
    CreditCard,
    FileText,
    Home,
    Landmark,
    LineChart,
    RefreshCw,
    Smartphone,
    TrendingUp,
    Wallet,
} from 'lucide-react';
import { getAccountTypeVisual } from '@/lib/themes/accountTypes';

describe('getAccountTypeVisual', () => {
    it('maps bank to Landmark', () => {
        const visual = getAccountTypeVisual('bank');
        expect(visual.icon).toBe(Landmark);
        expect(visual.colorVar).toBe('var(--type-bank)');
    });

    it('maps cash to Banknote', () => {
        expect(getAccountTypeVisual('cash').icon).toBe(Banknote);
    });

    it('maps credit_card to CreditCard', () => {
        expect(getAccountTypeVisual('credit_card').icon).toBe(CreditCard);
        expect(getAccountTypeVisual('credit_card').colorVar).toBe('var(--type-credit-card)');
    });

    it('maps wallet to Smartphone', () => {
        expect(getAccountTypeVisual('wallet').icon).toBe(Smartphone);
    });

    it('maps mutual_fund to TrendingUp', () => {
        expect(getAccountTypeVisual('mutual_fund').icon).toBe(TrendingUp);
    });

    it('maps fixed_deposit to Building2', () => {
        expect(getAccountTypeVisual('fixed_deposit').icon).toBe(Building2);
    });

    it('maps recurring_deposit to RefreshCw', () => {
        expect(getAccountTypeVisual('recurring_deposit').icon).toBe(RefreshCw);
    });

    it('maps stock to LineChart', () => {
        expect(getAccountTypeVisual('stock').icon).toBe(LineChart);
    });

    it('uses loan subtype icons', () => {
        expect(getAccountTypeVisual('loan', 'home').icon).toBe(Home);
        expect(getAccountTypeVisual('loan', 'vehicle').icon).toBe(Car);
        expect(getAccountTypeVisual('loan', 'personal').icon).toBe(FileText);
    });

    it('falls back for unknown types', () => {
        const visual = getAccountTypeVisual('unknown_type');
        expect(visual.icon).toBe(Wallet);
        expect(visual.colorVar).toBe('var(--neutral)');
    });
});
