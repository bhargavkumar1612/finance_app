import type { Transaction } from '@/lib/api';

export type TransactionFilterField =
    | 'merchant'
    | 'category'
    | 'subcategory'
    | 'source'
    | 'account'
    | 'amount'
    | 'date'
    | 'raw_description'
    | 'currency';

export type AmountKind = 'all' | 'spending' | 'income';

export type NwImpactFilter = 'all' | 'spending' | 'income' | 'transfer' | 'liability_payment' | 'refund';

export interface TransactionFilters {
    search: string;
    accountId: string;
    category: string;
    source: string;
    dateFrom: string;
    dateTo: string;
    amountKind: AmountKind;
    nwImpact: NwImpactFilter;
    field: TransactionFilterField;
    fieldValue: string;
}

export const EMPTY_FILTERS: TransactionFilters = {
    search: '',
    accountId: '',
    category: '',
    source: '',
    dateFrom: '',
    dateTo: '',
    amountKind: 'all',
    nwImpact: 'all',
    field: 'merchant',
    fieldValue: '',
};

function norm(s: string | undefined | null): string {
    return (s ?? '').toLowerCase();
}

function txnSearchBlob(tx: Transaction): string {
    return [
        tx.transaction_date,
        tx.merchant,
        tx.category,
        tx.subcategory,
        tx.source,
        tx.raw_description,
        tx.currency,
        tx.account_name,
        tx.account_type,
        tx.nw_impact,
        String(tx.amount),
    ]
        .map(norm)
        .join(' ');
}

function fieldText(tx: Transaction, field: TransactionFilterField): string {
    switch (field) {
        case 'merchant':
            return norm(tx.merchant);
        case 'category':
            return norm(tx.category);
        case 'subcategory':
            return norm(tx.subcategory);
        case 'source':
            return norm(tx.source);
        case 'account':
            return `${norm(tx.account_name)} ${norm(tx.account_type)}`;
        case 'amount':
            return String(tx.amount);
        case 'date':
            return norm(tx.transaction_date);
        case 'raw_description':
            return norm(tx.raw_description);
        case 'currency':
            return norm(tx.currency);
        default:
            return '';
    }
}

export function filterTransactions(
    txns: Transaction[],
    filters: TransactionFilters
): Transaction[] {
    const q = filters.search.trim().toLowerCase();
    const fieldVal = filters.fieldValue.trim().toLowerCase();

    return txns.filter((tx) => {
        if (q && !txnSearchBlob(tx).includes(q)) return false;
        if (filters.accountId && tx.account_id !== filters.accountId) return false;
        if (filters.category && norm(tx.category) !== filters.category.toLowerCase()) return false;
        if (filters.source && norm(tx.source) !== filters.source.toLowerCase()) return false;
        if (filters.dateFrom && tx.transaction_date < filters.dateFrom) return false;
        if (filters.dateTo && tx.transaction_date > filters.dateTo) return false;
        if (filters.nwImpact !== 'all' && tx.nw_impact !== filters.nwImpact) return false;
        if (filters.amountKind === 'spending' && tx.nw_impact !== 'spending') return false;
        if (filters.amountKind === 'income' && !['income', 'refund'].includes(tx.nw_impact ?? '')) return false;
        if (fieldVal && !fieldText(tx, filters.field).includes(fieldVal)) return false;
        return true;
    });
}

export function hasActiveFilters(filters: TransactionFilters): boolean {
    return (
        !!filters.search.trim() ||
        !!filters.accountId ||
        !!filters.category ||
        !!filters.source ||
        !!filters.dateFrom ||
        !!filters.dateTo ||
        filters.amountKind !== 'all' ||
        filters.nwImpact !== 'all' ||
        !!filters.fieldValue.trim()
    );
}

export function uniqueCategories(txns: Transaction[]): string[] {
    const set = new Set<string>();
    for (const tx of txns) {
        const c = tx.category?.trim();
        if (c) set.add(c);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
}

export function uniqueSources(txns: Transaction[]): string[] {
    const set = new Set<string>();
    for (const tx of txns) {
        if (tx.source) set.add(tx.source);
    }
    return [...set].sort();
}
