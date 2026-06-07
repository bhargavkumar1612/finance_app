import type { Account, AccountType, InvestmentMode, LoanType } from '@/lib/api';

export interface AccountTypeConfig {
    value: AccountType;
    label: string;
    description: string;
}

export interface LoanDetailConfig {
    value: LoanType;
    label: string;
}

export const ACCOUNT_TYPE_CONFIG: AccountTypeConfig[] = [
    { value: 'bank', label: 'Bank', description: 'Savings or current account' },
    { value: 'cash', label: 'Cash', description: 'Physical cash reserve' },
    { value: 'credit_card', label: 'Credit card', description: 'Credit card linked to a bank account' },
    { value: 'wallet', label: 'Online wallet', description: 'PhonePe, Amazon Pay, Flipkart, etc. — optional bank link' },
    { value: 'loan', label: 'Loan', description: 'Loan linked to a bank account' },
    { value: 'mutual_fund', label: 'Mutual fund', description: 'One-time or SIP holdings linked to a bank account' },
    { value: 'fixed_deposit', label: 'Fixed deposit', description: 'FD linked to a bank account' },
    { value: 'recurring_deposit', label: 'Recurring deposit', description: 'RD linked to a bank account' },
    { value: 'stock', label: 'Stock', description: 'Brokerage / stock holdings linked to a bank account' },
    { value: 'epf', label: 'EPF', description: 'Employee Provident Fund — employer retirement corpus' },
];

export const LOAN_DETAIL_CONFIG: LoanDetailConfig[] = [
    { value: 'home', label: 'Home' },
    { value: 'personal', label: 'Personal' },
    { value: 'vehicle', label: 'Vehicle' },
    { value: 'education', label: 'Education' },
    { value: 'other', label: 'Other' },
];

const CONFIG_BY_TYPE = Object.fromEntries(
    ACCOUNT_TYPE_CONFIG.map((c) => [c.value, c]),
) as Record<AccountType, AccountTypeConfig>;

const LOAN_DETAIL_BY_TYPE = Object.fromEntries(
    LOAN_DETAIL_CONFIG.map((c) => [c.value, c]),
) as Record<LoanType, LoanDetailConfig>;

export function accountTypeLabel(type: string): string {
    return CONFIG_BY_TYPE[type as AccountType]?.label ?? type.replace(/_/g, ' ');
}

export function loanDetailLabel(loanType?: string | null): string {
    if (!loanType) return '';
    return LOAN_DETAIL_BY_TYPE[loanType as LoanType]?.label ?? loanType.replace(/_/g, ' ');
}

export function accountDisplayLabel(
    account: Pick<Account, 'account_type' | 'loan_type' | 'loan_type_description'>,
): string {
    if (account.account_type === 'loan' && account.loan_type) {
        const detail =
            account.loan_type === 'other' && account.loan_type_description
                ? account.loan_type_description
                : loanDetailLabel(account.loan_type);
        return `Loan · ${detail}`;
    }
    return accountTypeLabel(account.account_type);
}

export function formatInr(amount: number): string {
    return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

export interface MetricLine {
    text: string;
    variant?: 'profit' | 'loss';
}

export function formatInvestmentValuationMetrics(
    account: Pick<
        Account,
        'account_type' | 'invested_amount' | 'current_value' | 'pnl_amount' | 'pnl_percent'
    >,
): MetricLine[] {
    if (!isInvestmentType(account.account_type)) {
        return [];
    }
    const lines: MetricLine[] = [];
    if (account.invested_amount != null) {
        lines.push({ text: `Invested ${formatInr(account.invested_amount)}` });
    }
    if (account.current_value != null) {
        lines.push({ text: `Current ${formatInr(account.current_value)}` });
    }
    if (account.pnl_amount != null && account.pnl_percent != null) {
        const amountPrefix = account.pnl_amount >= 0 ? '+' : '-';
        const percentPrefix = account.pnl_percent >= 0 ? '+' : '';
        lines.push({
            text: `P&L ${amountPrefix}${formatInr(Math.abs(account.pnl_amount))} (${percentPrefix}${account.pnl_percent.toFixed(1)}%)`,
            variant: account.pnl_amount > 0 ? 'profit' : account.pnl_amount < 0 ? 'loss' : undefined,
        });
    }
    return lines;
}

export function formatAccountMetrics(
    account: Pick<
        Account,
        | 'account_type'
        | 'balance'
        | 'invested_amount'
        | 'current_value'
        | 'pnl_amount'
        | 'pnl_percent'
        | 'credit_used'
        | 'credit_remaining'
        | 'credit_limit'
        | 'sanctioned_amount'
        | 'outstanding'
        | 'amount_paid'
        | 'emi_amount'
        | 'emi_paid_count'
        | 'emi_pending_count'
        | 'due_day'
        | 'investment_mode'
        | 'sip_paid_count'
        | 'sip_pending_count'
    >,
): string[] {
    const lines: string[] = [];

    if (isInvestmentType(account.account_type)) {
        lines.push(...formatInvestmentValuationMetrics(account).map((line) => line.text));
    } else if (account.balance != null) {
        lines.push(`Balance ${formatInr(account.balance)}`);
    }

    if (account.credit_used != null) {
        const parts = [`Used ${formatInr(account.credit_used)}`];
        if (account.credit_remaining != null) {
            parts.push(`Remaining ${formatInr(account.credit_remaining)}`);
        }
        if (account.credit_limit != null) {
            parts.push(`Limit ${formatInr(account.credit_limit)}`);
        }
        lines.push(parts.join(' · '));
    }

    if (account.account_type === 'credit_card' && account.due_day != null) {
        lines.push(`Statement due day ${account.due_day}`);
    }

    if (usesSipScheduleFields(account.account_type, account.investment_mode)) {
        const sipParts: string[] = ['SIP'];
        if (account.emi_amount != null) {
            sipParts.push(`${formatInr(account.emi_amount)}/mo`);
        }
        if (account.due_day != null) {
            sipParts.push(`debit day ${account.due_day}`);
        }
        lines.push(sipParts.join(' · '));
        if (account.emi_amount != null) {
            const countParts: string[] = [];
            if (account.sip_paid_count != null) {
                countParts.push(`${account.sip_paid_count} paid`);
            }
            if (account.sip_pending_count != null) {
                countParts.push(`${account.sip_pending_count} pending`);
            }
            if (countParts.length) {
                lines.push(`Installments ${countParts.join(' · ')}`);
            }
        }
    }

    if (account.account_type === 'loan' || account.outstanding != null) {
        const parts: string[] = [];
        if (account.sanctioned_amount != null) {
            parts.push(`Sanctioned ${formatInr(account.sanctioned_amount)}`);
        }
        if (account.outstanding != null) {
            parts.push(`Outstanding ${formatInr(account.outstanding)}`);
        }
        if (account.amount_paid != null && account.amount_paid > 0) {
            parts.push(`Paid ${formatInr(account.amount_paid)}`);
        }
        if (parts.length) {
            lines.push(parts.join(' · '));
        }
        if (account.emi_amount != null) {
            const emiParts = [`EMI ${formatInr(account.emi_amount)}/mo`];
            if (account.emi_paid_count != null) {
                emiParts.push(`${account.emi_paid_count} paid`);
            }
            if (account.emi_pending_count != null) {
                emiParts.push(`${account.emi_pending_count} pending`);
            }
            lines.push(emiParts.join(' · '));
        }
    }

    return lines;
}

export function isMutualFundType(type: string): boolean {
    return type === 'mutual_fund';
}

export function usesMutualFundModeField(type: string): boolean {
    return isMutualFundType(type);
}

export function usesSipScheduleFields(type: string, mode?: InvestmentMode | null): boolean {
    return isMutualFundType(type) && mode === 'sip';
}

export const INVESTMENT_MODE_CONFIG: { value: InvestmentMode; label: string; description: string }[] = [
    { value: 'one_time', label: 'One-time', description: 'Single lump-sum investment' },
    { value: 'sip', label: 'SIP', description: 'Monthly systematic investment plan' },
];

export function isLoanType(type: string): boolean {
    return type === 'loan';
}

export function isInvestmentType(type: string): boolean {
    return (
        type === 'mutual_fund' ||
        type === 'fixed_deposit' ||
        type === 'recurring_deposit' ||
        type === 'stock' ||
        type === 'epf'
    );
}

export function usesInvestmentFdFields(type: string): boolean {
    return type === 'fixed_deposit' || type === 'recurring_deposit';
}

export function usesFolioField(type: string): boolean {
    return type === 'mutual_fund' || type === 'recurring_deposit';
}

export function usesUanField(type: string): boolean {
    return type === 'epf';
}

export function usesDematField(type: string): boolean {
    return type === 'stock';
}

export function formatInvestmentReferenceMeta(
    account: Pick<Account, 'account_type' | 'folio_number' | 'demat_id'>,
): string[] {
    const lines: string[] = [];
    if (account.folio_number) {
        const num = account.folio_number;
        const masked = num.length > 4 ? `••••${num.slice(-4)}` : num;
        const prefix = account.account_type === 'epf' ? 'UAN' : 'Folio';
        lines.push(`${prefix} ${masked}`);
    }
    if (account.demat_id) {
        const num = account.demat_id;
        const masked = num.length > 4 ? `••••${num.slice(-4)}` : num;
        lines.push(`Demat ${masked}`);
    }
    return lines;
}

export function usesCreditLimitField(type: string): boolean {
    return type === 'credit_card';
}

export function usesInitialCreditUsedField(type: string): boolean {
    return type === 'credit_card';
}

export function usesSanctionedField(type: string): boolean {
    return isLoanType(type);
}

export function usesOpeningBalanceField(type: string): boolean {
    return type === 'bank' || type === 'cash' || isInvestmentType(type);
}

export function usesInvestmentValuationFields(type: string): boolean {
    return isInvestmentType(type);
}

export function usesBankDetailFields(type: string): boolean {
    return type === 'bank';
}

export function showsInstitution(type: string): boolean {
    return type !== 'cash';
}

export function computeFdMaturityDate(startDate: string, tenureMonths: number): string | null {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(startDate);
    if (!match || tenureMonths < 1) {
        return null;
    }
    const year = Number(match[1]);
    const month = Number(match[2]) - 1;
    const day = Number(match[3]);
    const totalMonths = month + tenureMonths;
    const maturityYear = year + Math.floor(totalMonths / 12);
    const maturityMonth = totalMonths % 12;
    const lastDay = new Date(maturityYear, maturityMonth + 1, 0).getDate();
    const maturityDay = Math.min(day, lastDay);
    return `${maturityYear}-${String(maturityMonth + 1).padStart(2, '0')}-${String(maturityDay).padStart(2, '0')}`;
}

export function formatInvestmentFdMeta(
    account: Pick<Account, 'account_type' | 'start_date' | 'tenure_months' | 'interest_rate'>,
): string[] {
    if (!usesInvestmentFdFields(account.account_type)) {
        return [];
    }
    const parts: string[] = [];
    if (account.start_date) {
        parts.push(`Start ${account.start_date}`);
    }
    if (account.tenure_months != null) {
        parts.push(`${account.tenure_months} mo`);
    }
    if (account.interest_rate != null) {
        parts.push(`${account.interest_rate}%`);
    }
    if (account.start_date && account.tenure_months != null) {
        const maturity = computeFdMaturityDate(account.start_date, account.tenure_months);
        if (maturity) {
            parts.push(`Matures ${maturity}`);
        }
    }
    return parts.length ? [parts.join(' · ')] : [];
}

export function formatBankAccountMeta(
    account: Pick<Account, 'account_number' | 'ifsc_code' | 'branch' | 'account_notes'>,
): string[] {
    const lines: string[] = [];
    if (account.account_number) {
        const num = account.account_number;
        const masked = num.length > 4 ? `••••${num.slice(-4)}` : num;
        lines.push(`A/c ${masked}`);
    }
    if (account.ifsc_code) lines.push(`IFSC ${account.ifsc_code}`);
    if (account.branch) lines.push(account.branch);
    if (account.account_notes) lines.push(account.account_notes);
    return lines;
}

export function requiresParent(type: string): boolean {
    if (type === 'epf') return false;
    return type === 'credit_card' || type === 'loan' || isInvestmentType(type);
}

export function showsParentLinkField(type: string): boolean {
    if (type === 'epf') return false;
    return type === 'credit_card' || type === 'wallet' || type === 'loan' || isInvestmentType(type);
}

export function showsBalance(type: string): boolean {
    return type === 'bank' || type === 'cash' || type === 'wallet' || isInvestmentType(type);
}

export type AccountBalanceSide = 'asset' | 'liability';
export type AccountUiGroup = 'cash_wallets' | 'investments' | 'credit_cards' | 'loans';

export const CASH_WALLET_TYPES: AccountType[] = ['bank', 'cash', 'wallet'];
export const INVESTMENT_ACCOUNT_TYPES: AccountType[] = [
    'mutual_fund',
    'fixed_deposit',
    'recurring_deposit',
    'stock',
    'epf',
];
export const ASSET_ACCOUNT_TYPES: AccountType[] = [...CASH_WALLET_TYPES, ...INVESTMENT_ACCOUNT_TYPES];
export const LIABILITY_ACCOUNT_TYPES: AccountType[] = ['credit_card', 'loan'];

export const UI_GROUP_LABELS: Record<AccountUiGroup, string> = {
    cash_wallets: 'Cash & wallets',
    investments: 'Investments',
    credit_cards: 'Credit cards',
    loans: 'Loans',
};

export const SIDE_LABELS: Record<AccountBalanceSide, string> = {
    asset: 'Assets',
    liability: 'Liabilities',
};

const UI_GROUP_ORDER: AccountUiGroup[] = ['cash_wallets', 'investments', 'credit_cards', 'loans'];

export function accountBalanceSide(type: string): AccountBalanceSide {
    if (type === 'credit_card' || type === 'loan') {
        return 'liability';
    }
    return 'asset';
}

export function accountUiGroup(type: string): AccountUiGroup {
    if (type === 'credit_card') return 'credit_cards';
    if (type === 'loan') return 'loans';
    if (isInvestmentType(type)) return 'investments';
    return 'cash_wallets';
}

export function accountPlacementHint(type: string): string {
    const side = SIDE_LABELS[accountBalanceSide(type)];
    const group = UI_GROUP_LABELS[accountUiGroup(type)];
    return `Appears under ${side} → ${group}`;
}

export function accountContributionAmount(
    account: Pick<Account, 'account_type' | 'balance' | 'current_value' | 'credit_used' | 'outstanding'>,
): number {
    if (account.account_type === 'credit_card') {
        return account.credit_used ?? 0;
    }
    if (account.account_type === 'loan') {
        return account.outstanding ?? 0;
    }
    if (isInvestmentType(account.account_type)) {
        return account.current_value ?? account.balance ?? 0;
    }
    return account.balance ?? 0;
}

export interface GroupedAccounts {
    assets: {
        cash_wallets: Account[];
        investments: Account[];
    };
    liabilities: {
        credit_cards: Account[];
        loans: Account[];
    };
}

export interface AccountsSummary {
    assetsTotal: number;
    liabilitiesTotal: number;
    netWorth: number;
    byGroup: Record<AccountUiGroup, number>;
}

export function groupAccounts(accounts: Account[]): GroupedAccounts {
    const grouped: GroupedAccounts = {
        assets: { cash_wallets: [], investments: [] },
        liabilities: { credit_cards: [], loans: [] },
    };
    for (const acc of accounts) {
        const group = accountUiGroup(acc.account_type);
        if (group === 'cash_wallets') {
            grouped.assets.cash_wallets.push(acc);
        } else if (group === 'investments') {
            grouped.assets.investments.push(acc);
        } else if (group === 'credit_cards') {
            grouped.liabilities.credit_cards.push(acc);
        } else {
            grouped.liabilities.loans.push(acc);
        }
    }
    return grouped;
}

export function computeAccountsSummary(accounts: Account[]): AccountsSummary {
    const byGroup = Object.fromEntries(
        UI_GROUP_ORDER.map((g) => [g, 0]),
    ) as Record<AccountUiGroup, number>;
    let assetsTotal = 0;
    let liabilitiesTotal = 0;
    for (const acc of accounts) {
        const amount = accountContributionAmount(acc);
        const group = accountUiGroup(acc.account_type);
        byGroup[group] += amount;
        if (accountBalanceSide(acc.account_type) === 'asset') {
            assetsTotal += amount;
        } else {
            liabilitiesTotal += amount;
        }
    }
    return {
        assetsTotal,
        liabilitiesTotal,
        netWorth: assetsTotal - liabilitiesTotal,
        byGroup,
    };
}

export function creditUtilizationPercent(
    account: Pick<Account, 'credit_used' | 'credit_limit'>,
): number | null {
    if (account.credit_limit == null || account.credit_limit <= 0) {
        return null;
    }
    const used = account.credit_used ?? 0;
    return Math.min(100, Math.round((used / account.credit_limit) * 100));
}
