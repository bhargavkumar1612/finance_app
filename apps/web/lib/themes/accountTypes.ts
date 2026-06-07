import type { AccountType, LoanType } from '@/lib/api';
import type { LucideIcon } from 'lucide-react';
import {
    Banknote,
    Building2,
    Car,
    CreditCard,
    FileText,
    GraduationCap,
    Home,
    Landmark,
    LineChart,
    RefreshCw,
    Shield,
    Smartphone,
    TrendingUp,
    Wallet,
} from 'lucide-react';

export interface AccountTypeVisual {
    icon: LucideIcon;
    colorVar: string;
    label: string;
}

const BASE: Record<AccountType, AccountTypeVisual> = {
    bank: { icon: Landmark, colorVar: 'var(--type-bank)', label: 'Bank' },
    cash: { icon: Banknote, colorVar: 'var(--type-cash)', label: 'Cash' },
    credit_card: { icon: CreditCard, colorVar: 'var(--type-credit-card)', label: 'Credit card' },
    wallet: { icon: Smartphone, colorVar: 'var(--type-wallet)', label: 'Online wallet' },
    loan: { icon: FileText, colorVar: 'var(--type-loan)', label: 'Loan' },
    mutual_fund: { icon: TrendingUp, colorVar: 'var(--type-investment)', label: 'Mutual fund' },
    fixed_deposit: { icon: Building2, colorVar: 'var(--type-fd)', label: 'Fixed deposit' },
    recurring_deposit: { icon: RefreshCw, colorVar: 'var(--type-rd)', label: 'Recurring deposit' },
    stock: { icon: LineChart, colorVar: 'var(--type-stock)', label: 'Stock' },
    epf: { icon: Shield, colorVar: 'var(--type-investment)', label: 'EPF' },
};

const LOAN_ICONS: Partial<Record<LoanType, LucideIcon>> = {
    home: Home,
    personal: FileText,
    vehicle: Car,
    education: GraduationCap,
    other: FileText,
};

export function getAccountTypeVisual(
    type: string,
    loanType?: string | null,
): AccountTypeVisual {
    if (type === 'loan' && loanType) {
        const loanIcon = LOAN_ICONS[loanType as LoanType] ?? FileText;
        return { ...BASE.loan, icon: loanIcon };
    }
    return BASE[type as AccountType] ?? { icon: Wallet, colorVar: 'var(--neutral)', label: type };
}
