'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import {
    createAccount,
    deleteAccount,
    getAccounts,
    updateAccount,
    type Account,
    type CreateAccountRequest,
} from '@/lib/api';
import AccountTypeIcon from '@/components/icons/AccountTypeIcon';
import {
    ACCOUNT_TYPE_CONFIG,
    ASSET_ACCOUNT_TYPES,
    LIABILITY_ACCOUNT_TYPES,
    UI_GROUP_LABELS,
    type AccountTypeConfig,
    accountBalanceSide,
    accountDisplayLabel,
    computeAccountsSummary,
    creditUtilizationPercent,
    formatAccountMetrics,
    formatBankAccountMeta,
    formatInr,
    formatInvestmentFdMeta,
    formatInvestmentValuationMetrics,
    formatInvestmentReferenceMeta,
    groupAccounts,
    isLoanType,
    requiresParent,
    showsParentLinkField,
    usesBankDetailFields,
    usesCreditLimitField,
    usesDematField,
    usesFolioField,
    usesUanField,
    usesInitialCreditUsedField,
    usesInvestmentFdFields,
    usesInvestmentValuationFields,
    usesMutualFundModeField,
    usesOpeningBalanceField,
    usesSanctionedField,
    usesSipScheduleFields,
    type AccountUiGroup,
} from '@/lib/accountDisplay';
import AccountForm from './AccountForm';
import styles from './Accounts.module.css';

type AccountFormData = CreateAccountRequest;

const emptyForm = (): AccountFormData => ({
    account_type: 'bank',
    name: '',
    institution: '',
    loan_type: undefined,
    loan_type_description: undefined,
    credit_limit: undefined,
    sanctioned_amount: undefined,
    interest_rate: undefined,
    emi_amount: undefined,
    tenure_months: undefined,
    start_date: undefined,
    due_day: undefined,
    currency: 'INR',
    parent_account_id: undefined,
    opening_balance: undefined,
    account_number: undefined,
    ifsc_code: undefined,
    branch: undefined,
    account_notes: undefined,
    folio_number: undefined,
    demat_id: undefined,
    initial_credit_used: undefined,
    initial_credit_used_date: undefined,
    initial_emi_paid_count: undefined,
    invested_amount: undefined,
    current_value: undefined,
    investment_mode: undefined,
    initial_sip_paid_count: undefined,
});

export default function AccountsPage() {
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState<AccountFormData>(emptyForm);
    const [saving, setSaving] = useState(false);
    const [editing, setEditing] = useState<Account | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<Account | null>(null);
    const [deleting, setDeleting] = useState(false);

    const load = useCallback(async () => {
        setError(null);
        setLoading(true);
        try {
            setAccounts(await getAccounts());
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to load accounts');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const grouped = useMemo(() => groupAccounts(accounts), [accounts]);
    const summary = useMemo(() => computeAccountsSummary(accounts), [accounts]);

    const assetTypeConfig = useMemo(
        () => ACCOUNT_TYPE_CONFIG.filter((t) => ASSET_ACCOUNT_TYPES.includes(t.value)),
        [],
    );
    const liabilityTypeConfig = useMemo(
        () => ACCOUNT_TYPE_CONFIG.filter((t) => LIABILITY_ACCOUNT_TYPES.includes(t.value)),
        [],
    );

    const resetForm = () => {
        setForm(emptyForm());
        setEditing(null);
        setShowForm(false);
    };

    const openEdit = (acc: Account) => {
        setEditing(acc);
        setForm({
            account_type: acc.account_type,
            name: acc.name,
            institution: acc.institution ?? '',
            loan_type: acc.loan_type ?? undefined,
            loan_type_description: acc.loan_type_description ?? undefined,
            credit_limit: acc.credit_limit ?? undefined,
            sanctioned_amount: acc.sanctioned_amount ?? undefined,
            interest_rate: acc.interest_rate ?? undefined,
            emi_amount: acc.emi_amount ?? undefined,
            tenure_months: acc.tenure_months ?? undefined,
            start_date: acc.start_date ?? undefined,
            due_day: acc.due_day ?? undefined,
            currency: acc.currency ?? 'INR',
            parent_account_id: acc.parent_account_id ?? undefined,
            opening_balance: acc.opening_balance ?? undefined,
            account_number: acc.account_number ?? undefined,
            ifsc_code: acc.ifsc_code ?? undefined,
            branch: acc.branch ?? undefined,
            account_notes: acc.account_notes ?? undefined,
            folio_number: acc.folio_number ?? undefined,
            demat_id: acc.demat_id ?? undefined,
            initial_credit_used: acc.initial_credit_used ?? undefined,
            initial_credit_used_date: acc.initial_credit_used_date ?? undefined,
            initial_emi_paid_count: acc.initial_emi_paid_count ?? undefined,
            invested_amount: acc.invested_amount ?? undefined,
            current_value: acc.current_value ?? undefined,
            investment_mode: acc.investment_mode ?? undefined,
            initial_sip_paid_count: acc.initial_sip_paid_count ?? undefined,
        });
        setShowForm(false);
        requestAnimationFrame(() => {
            document.getElementById(`account-edit-${acc.id}`)?.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
            });
        });
    };

    const buildPayload = (): CreateAccountRequest => {
        const payload: CreateAccountRequest = {
            account_type: form.account_type,
            name: form.name.trim(),
            institution: form.institution?.trim() || undefined,
            currency: form.currency || 'INR',
        };
        if (showsParentLinkField(form.account_type) && form.parent_account_id) {
            payload.parent_account_id = form.parent_account_id;
        }
        if (isLoanType(form.account_type)) {
            if (form.loan_type) payload.loan_type = form.loan_type;
            if (form.loan_type === 'other' && form.loan_type_description?.trim()) {
                payload.loan_type_description = form.loan_type_description.trim();
            }
            if (form.sanctioned_amount != null && form.sanctioned_amount > 0) {
                payload.sanctioned_amount = form.sanctioned_amount;
            }
            if (form.emi_amount != null && form.emi_amount > 0) payload.emi_amount = form.emi_amount;
            if (form.interest_rate != null) payload.interest_rate = form.interest_rate;
            if (form.tenure_months != null) payload.tenure_months = form.tenure_months;
            if (form.start_date) payload.start_date = form.start_date;
            if (form.due_day != null) payload.due_day = form.due_day;
        }
        if (usesInvestmentFdFields(form.account_type)) {
            if (form.interest_rate != null) payload.interest_rate = form.interest_rate;
            if (form.tenure_months != null) payload.tenure_months = form.tenure_months;
            if (form.start_date) payload.start_date = form.start_date;
        }
        if (usesCreditLimitField(form.account_type) && form.credit_limit != null && form.credit_limit > 0) {
            payload.credit_limit = form.credit_limit;
        }
        if (usesCreditLimitField(form.account_type) && form.due_day != null) {
            payload.due_day = form.due_day;
        }
        if (usesOpeningBalanceField(form.account_type) && form.opening_balance != null && form.opening_balance >= 0) {
            payload.opening_balance = form.opening_balance;
        }
        if (usesInvestmentValuationFields(form.account_type)) {
            if (form.invested_amount != null && form.invested_amount >= 0) {
                payload.invested_amount = form.invested_amount;
            }
            if (form.current_value != null && form.current_value >= 0) {
                payload.current_value = form.current_value;
            }
        }
        if (usesBankDetailFields(form.account_type)) {
            if (form.account_number?.trim()) payload.account_number = form.account_number.trim();
            if (form.ifsc_code?.trim()) payload.ifsc_code = form.ifsc_code.trim();
            if (form.branch?.trim()) payload.branch = form.branch.trim();
            if (form.account_notes?.trim()) payload.account_notes = form.account_notes.trim();
        }
        if ((usesFolioField(form.account_type) || usesUanField(form.account_type)) && form.folio_number?.trim()) {
            payload.folio_number = form.folio_number.trim();
        }
        if (usesDematField(form.account_type) && form.demat_id?.trim()) {
            payload.demat_id = form.demat_id.trim();
        }
        if (usesMutualFundModeField(form.account_type)) {
            payload.investment_mode = form.investment_mode ?? 'one_time';
        }
        if (usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time')) {
            if (form.emi_amount != null && form.emi_amount > 0) payload.emi_amount = form.emi_amount;
            if (form.due_day != null) payload.due_day = form.due_day;
            if (form.start_date) payload.start_date = form.start_date;
            if (form.tenure_months != null) payload.tenure_months = form.tenure_months;
            if (form.initial_sip_paid_count != null && form.initial_sip_paid_count >= 0) {
                payload.initial_sip_paid_count = form.initial_sip_paid_count;
            }
        }
        if (usesInitialCreditUsedField(form.account_type) && form.initial_credit_used != null && form.initial_credit_used > 0) {
            payload.initial_credit_used = form.initial_credit_used;
            if (form.initial_credit_used_date) {
                payload.initial_credit_used_date = form.initial_credit_used_date;
            }
        }
        if (
            isLoanType(form.account_type) &&
            form.initial_emi_paid_count != null &&
            form.initial_emi_paid_count >= 0
        ) {
            payload.initial_emi_paid_count = form.initial_emi_paid_count;
        }
        return payload;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) {
            setError('Name is required');
            return;
        }
        if (requiresParent(form.account_type) && !form.parent_account_id) {
            setError('Select a linked bank account for credit card, loan, or investment accounts');
            return;
        }
        if (isLoanType(form.account_type) && form.loan_type === 'other' && !form.loan_type_description?.trim()) {
            setError('Describe the loan type when "Other" is selected');
            return;
        }
        if (
            isLoanType(form.account_type) &&
            form.emi_amount != null &&
            form.emi_amount > 0 &&
            form.tenure_months != null &&
            form.tenure_months > 0 &&
            !form.start_date
        ) {
            setError('Start date is required when EMI and tenure are set');
            return;
        }
        if (
            usesInitialCreditUsedField(form.account_type) &&
            form.initial_credit_used != null &&
            form.initial_credit_used > 0 &&
            !form.initial_credit_used_date
        ) {
            setError('As-of date is required when initial credit used is set');
            return;
        }
        if (
            isLoanType(form.account_type) &&
            form.initial_emi_paid_count != null &&
            form.initial_emi_paid_count > 0 &&
            (!form.sanctioned_amount || form.sanctioned_amount <= 0)
        ) {
            setError('Sanctioned amount is required when EMIs already paid is set');
            return;
        }
        if (
            isLoanType(form.account_type) &&
            form.initial_emi_paid_count != null &&
            form.initial_emi_paid_count > 0 &&
            (!form.emi_amount || form.emi_amount <= 0)
        ) {
            setError('Monthly EMI is required when EMIs already paid is set');
            return;
        }
        if (
            isLoanType(form.account_type) &&
            form.initial_emi_paid_count != null &&
            form.tenure_months != null &&
            form.initial_emi_paid_count > form.tenure_months
        ) {
            setError('EMIs already paid cannot exceed tenure');
            return;
        }
        if (
            usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time') &&
            (!form.emi_amount || form.emi_amount <= 0)
        ) {
            setError('Monthly SIP amount is required for SIP mutual funds');
            return;
        }
        if (
            usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time') &&
            !form.due_day
        ) {
            setError('SIP debit day is required');
            return;
        }
        if (
            usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time') &&
            !form.start_date
        ) {
            setError('SIP start date is required');
            return;
        }
        if (
            usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time') &&
            form.initial_sip_paid_count != null &&
            form.tenure_months != null &&
            form.initial_sip_paid_count > form.tenure_months
        ) {
            setError('Installments already paid cannot exceed planned tenure');
            return;
        }
        setSaving(true);
        setError(null);
        try {
            const payload = buildPayload();
            if (editing) {
                await updateAccount(editing.id, {
                    ...payload,
                    credit_limit: usesCreditLimitField(form.account_type) ? form.credit_limit ?? null : null,
                    sanctioned_amount: usesSanctionedField(form.account_type)
                        ? form.sanctioned_amount ?? null
                        : null,
                    loan_type: isLoanType(form.account_type) ? form.loan_type ?? null : null,
                    loan_type_description: isLoanType(form.account_type) ? form.loan_type_description ?? null : null,
                    emi_amount:
                        isLoanType(form.account_type) ||
                        usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time')
                            ? form.emi_amount ?? null
                            : null,
                    interest_rate:
                        isLoanType(form.account_type) || usesInvestmentFdFields(form.account_type)
                            ? form.interest_rate ?? null
                            : null,
                    tenure_months:
                        isLoanType(form.account_type) ||
                        usesInvestmentFdFields(form.account_type) ||
                        usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time')
                            ? form.tenure_months ?? null
                            : null,
                    start_date:
                        isLoanType(form.account_type) ||
                        usesInvestmentFdFields(form.account_type) ||
                        usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time')
                            ? form.start_date ?? null
                            : null,
                    due_day:
                        isLoanType(form.account_type) ||
                        usesCreditLimitField(form.account_type) ||
                        usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time')
                            ? form.due_day ?? null
                            : null,
                    ...(usesMutualFundModeField(form.account_type)
                        ? { investment_mode: form.investment_mode ?? 'one_time' }
                        : {}),
                    parent_account_id: showsParentLinkField(form.account_type)
                        ? form.parent_account_id ?? null
                        : null,
                    ...(usesOpeningBalanceField(form.account_type)
                        ? { opening_balance: form.opening_balance ?? null }
                        : {}),
                    ...(usesInvestmentValuationFields(form.account_type)
                        ? {
                              invested_amount: form.invested_amount ?? null,
                              current_value: form.current_value ?? null,
                          }
                        : {}),
                    account_number: usesBankDetailFields(form.account_type)
                        ? form.account_number?.trim() || null
                        : null,
                    ifsc_code: usesBankDetailFields(form.account_type)
                        ? form.ifsc_code?.trim() || null
                        : null,
                    branch: usesBankDetailFields(form.account_type)
                        ? form.branch?.trim() || null
                        : null,
                    account_notes: usesBankDetailFields(form.account_type)
                        ? form.account_notes?.trim() || null
                        : null,
                    folio_number:
                        usesFolioField(form.account_type) || usesUanField(form.account_type)
                            ? form.folio_number?.trim() || null
                            : null,
                    demat_id: usesDematField(form.account_type)
                        ? form.demat_id?.trim() || null
                        : null,
                    ...(usesInitialCreditUsedField(form.account_type)
                        ? {
                              initial_credit_used: form.initial_credit_used ?? null,
                              initial_credit_used_date: form.initial_credit_used_date ?? null,
                          }
                        : {}),
                    ...(isLoanType(form.account_type)
                        ? { initial_emi_paid_count: form.initial_emi_paid_count ?? null }
                        : {}),
                    ...(usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time')
                        ? { initial_sip_paid_count: form.initial_sip_paid_count ?? null }
                        : {}),
                });
            } else {
                await createAccount(payload);
            }
            resetForm();
            await load();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Save failed');
        } finally {
            setSaving(false);
        }
    };

    const inlineEditProps = {
        editingId: editing?.id ?? null,
        form,
        setForm,
        assetTypeConfig,
        liabilityTypeConfig,
        saving,
        onSubmit: handleSubmit,
        onCancelEdit: resetForm,
    };

    const runDelete = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        setError(null);
        try {
            await deleteAccount(deleteTarget.id);
            setDeleteTarget(null);
            await load();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Delete failed');
            setDeleteTarget(null);
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <h1 className={styles.title}>Accounts</h1>
                <p className={styles.subtitle}>
                    What you own and what you owe — updated from transactions
                </p>
            </div>

            {!loading && (
                <div
                    id="accounts-hero"
                    className={`card fade-up ${styles.hero} ${summary.netWorth > 0 ? styles.heroPositive : ''}`}
                >
                    <p className={styles.heroLabel}>Net worth</p>
                    <p
                        className={styles.heroTotal}
                        aria-label={`Net worth ${formatInr(summary.netWorth)}`}
                    >
                        {formatInr(summary.netWorth)}
                    </p>
                    <div className={styles.heroMeta}>
                        <span className={styles.heroMetaItem}>
                            <span className={styles.heroMetaLabel}>Assets</span>
                            <span className={styles.heroAssets}>{formatInr(summary.assetsTotal)}</span>
                        </span>
                        <span className={styles.heroMetaItem}>
                            <span className={styles.heroMetaLabel}>Liabilities</span>
                            <span className={styles.heroLiabilities}>{formatInr(summary.liabilitiesTotal)}</span>
                        </span>
                        <span className={styles.heroMetaItem}>
                            <span className={styles.heroMetaLabel}>
                                {accounts.length} account{accounts.length === 1 ? '' : 's'}
                            </span>
                        </span>
                    </div>
                </div>
            )}

            <div className={styles.toolbar}>
                <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                        if (editing || showForm) {
                            resetForm();
                        } else {
                            setForm(emptyForm());
                            setShowForm(true);
                        }
                    }}
                >
                    {editing ? 'Cancel edit' : showForm ? 'Cancel' : 'Add account'}
                </button>
            </div>

            {error && <p className={styles.error}>{error}</p>}

            {showForm && !editing && (
                <AccountForm
                    form={form}
                    setForm={setForm}
                    accounts={accounts}
                    assetTypeConfig={assetTypeConfig}
                    liabilityTypeConfig={liabilityTypeConfig}
                    isEdit={false}
                    saving={saving}
                    onSubmit={handleSubmit}
                    onCancel={resetForm}
                />
            )}


            {loading ? (
                <div className="spinner" />
            ) : (
                <div className={styles.sectionStack}>
                    <section
                        id="accounts-section-assets"
                        className={`${styles.balanceSection} ${styles.sectionAssets} fade-up`}
                        aria-labelledby="accounts-assets-heading"
                    >
                        <div className={styles.sectionHeader}>
                            <h2 id="accounts-assets-heading" className={styles.sectionTitle}>
                                Assets
                            </h2>
                            <span className={styles.sectionTotal}>{formatInr(summary.assetsTotal)}</span>
                        </div>
                        {accounts.length === 0 ? (
                            <div className={`card ${styles.emptySection}`}>
                                <p className={styles.emptySectionText}>
                                    No accounts yet. Add a bank, wallet, or investment account to get started.
                                </p>
                                <button
                                    type="button"
                                    className="btn btn-primary"
                                    onClick={() => {
                                        setEditing(null);
                                        setForm(emptyForm());
                                        setShowForm(true);
                                    }}
                                >
                                    Add account
                                </button>
                            </div>
                        ) : (
                            <div className={styles.subGroupStack}>
                                <AccountSubGroup
                                    groupId="accounts-group-cash-wallets"
                                    group="cash_wallets"
                                    accounts={grouped.assets.cash_wallets}
                                    allAccounts={accounts}
                                    total={summary.byGroup.cash_wallets}
                                    onEdit={openEdit}
                                    onDelete={setDeleteTarget}
                                    {...inlineEditProps}
                                />
                                <AccountSubGroup
                                    groupId="accounts-group-investments"
                                    group="investments"
                                    accounts={grouped.assets.investments}
                                    allAccounts={accounts}
                                    total={summary.byGroup.investments}
                                    onEdit={openEdit}
                                    onDelete={setDeleteTarget}
                                    {...inlineEditProps}
                                />
                            </div>
                        )}
                    </section>

                    <section
                        id="accounts-section-liabilities"
                        className={`${styles.balanceSection} ${styles.sectionLiabilities} fade-up`}
                        style={{ animationDelay: '0.05s' }}
                        aria-labelledby="accounts-liabilities-heading"
                    >
                        <div className={styles.sectionHeader}>
                            <h2 id="accounts-liabilities-heading" className={styles.sectionTitle}>
                                Liabilities
                            </h2>
                            <span className={styles.sectionTotal}>{formatInr(summary.liabilitiesTotal)}</span>
                        </div>
                        <div className={styles.subGroupStack}>
                            <AccountSubGroup
                                groupId="accounts-group-credit-cards"
                                group="credit_cards"
                                accounts={grouped.liabilities.credit_cards}
                                allAccounts={accounts}
                                total={summary.byGroup.credit_cards}
                                onEdit={openEdit}
                                onDelete={setDeleteTarget}
                                {...inlineEditProps}
                            />
                            <AccountSubGroup
                                groupId="accounts-group-loans"
                                group="loans"
                                accounts={grouped.liabilities.loans}
                                allAccounts={accounts}
                                total={summary.byGroup.loans}
                                onEdit={openEdit}
                                onDelete={setDeleteTarget}
                                {...inlineEditProps}
                            />
                        </div>
                    </section>
                </div>
            )}

            {deleteTarget && (
                <div className={styles.modalBackdrop} role="dialog" aria-modal="true">
                    <div className={styles.modal}>
                        <h2 className={styles.modalTitle}>Delete account?</h2>
                        <p className={styles.modalText}>
                            Remove “{deleteTarget.name}”?
                            {(deleteTarget.transaction_count ?? 0) > 0
                                ? ' This account has transactions — delete those first.'
                                : ' This cannot be undone.'}
                        </p>
                        <div className={styles.modalActions}>
                            <button type="button" className="btn btn-ghost" onClick={() => setDeleteTarget(null)} disabled={deleting}>
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="btn btn-primary"
                                style={{ background: 'var(--danger, #dc2626)' }}
                                disabled={deleting || (deleteTarget.transaction_count ?? 0) > 0}
                                onClick={runDelete}
                            >
                                {deleting ? 'Deleting…' : 'Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

interface AccountSubGroupProps {
    groupId: string;
    group: AccountUiGroup;
    accounts: Account[];
    allAccounts: Account[];
    total: number;
    onEdit: (acc: Account) => void;
    onDelete: (acc: Account) => void;
    editingId: string | null;
    form: AccountFormData;
    setForm: React.Dispatch<React.SetStateAction<AccountFormData>>;
    assetTypeConfig: AccountTypeConfig[];
    liabilityTypeConfig: AccountTypeConfig[];
    saving: boolean;
    onSubmit: (e: FormEvent) => void;
    onCancelEdit: () => void;
}

function AccountSubGroup({
    groupId,
    group,
    accounts,
    allAccounts,
    total,
    onEdit,
    onDelete,
    editingId,
    form,
    setForm,
    assetTypeConfig,
    liabilityTypeConfig,
    saving,
    onSubmit,
    onCancelEdit,
}: AccountSubGroupProps) {
    const emptyMessages: Record<AccountUiGroup, string> = {
        cash_wallets: 'No cash or wallet accounts yet',
        investments: 'No investment accounts yet',
        credit_cards: 'No credit cards yet',
        loans: 'No loans yet',
    };

    return (
        <div id={groupId} className={styles.subGroup}>
            <div className={styles.subGroupHeader}>
                <h3 className={styles.subGroupTitle}>{UI_GROUP_LABELS[group]}</h3>
                <span
                    className={`${styles.subGroupTotal} ${total > 0 ? styles.subGroupTotalActive : ''}`}
                >
                    {formatInr(total)}
                </span>
            </div>
            {accounts.length === 0 ? (
                <p className={styles.subGroupEmpty}>{emptyMessages[group]}</p>
            ) : (
                <div className={styles.accountList}>
                    {accounts.map((acc) =>
                        acc.id === editingId ? (
                            <div
                                key={acc.id}
                                id={`account-edit-${acc.id}`}
                                className={styles.inlineFormWrap}
                            >
                                <AccountForm
                                    inline
                                    form={form}
                                    setForm={setForm}
                                    accounts={allAccounts}
                                    assetTypeConfig={assetTypeConfig}
                                    liabilityTypeConfig={liabilityTypeConfig}
                                    isEdit
                                    saving={saving}
                                    onSubmit={onSubmit}
                                    onCancel={onCancelEdit}
                                />
                            </div>
                        ) : (
                            <AccountCard
                                key={acc.id}
                                acc={acc}
                                allAccounts={allAccounts}
                                onEdit={onEdit}
                                onDelete={onDelete}
                            />
                        ),
                    )}
                </div>
            )}
        </div>
    );
}

interface AccountCardProps {
    acc: Account;
    allAccounts: Account[];
    onEdit: (acc: Account) => void;
    onDelete: (acc: Account) => void;
}

function AccountCard({ acc, allAccounts, onEdit, onDelete }: AccountCardProps) {
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const investmentMetrics = formatInvestmentValuationMetrics(acc);
    const metrics = formatAccountMetrics(acc).filter(
        (line) => !investmentMetrics.some((item) => item.text === line),
    );
    const bankMeta = formatBankAccountMeta(acc);
    const fdMeta = formatInvestmentFdMeta(acc);
    const refMeta = formatInvestmentReferenceMeta(acc);
    const parentName = acc.parent_account_id
        ? allAccounts.find((a) => a.id === acc.parent_account_id)?.name
        : null;
    const side = accountBalanceSide(acc.account_type);
    const utilization = creditUtilizationPercent(acc);

    useEffect(() => {
        if (!menuOpen) return;
        const onDocClick = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', onDocClick);
        return () => document.removeEventListener('mousedown', onDocClick);
    }, [menuOpen]);

    return (
        <div
            className={`${styles.accountCardWrap} card ${side === 'asset' ? styles.accountCardAsset : styles.accountCardLiability}`}
        >
            <div className={styles.cardRow}>
                <div className={styles.cardMain}>
                    <div className={styles.cardTitleRow}>
                        <AccountTypeIcon
                            type={acc.account_type}
                            loanType={acc.loan_type}
                            className={styles.typeSymbol}
                        />
                        <h3 className={styles.cardTitle}>{acc.name}</h3>
                        <span className={styles.typeBadge}>{accountDisplayLabel(acc)}</span>
                    </div>
                    <p className={styles.cardMeta}>
                        {[acc.institution, parentName ? `linked to ${parentName}` : null,
                            typeof acc.transaction_count === 'number'
                                ? `${acc.transaction_count} transaction${acc.transaction_count === 1 ? '' : 's'}`
                                : null,
                        ].filter(Boolean).join(' · ')}
                    </p>
                    {bankMeta.map((line) => (
                        <p key={line} className={styles.cardBankMeta}>{line}</p>
                    ))}
                    {fdMeta.map((line) => (
                        <p key={line} className={styles.cardMetrics}>{line}</p>
                    ))}
                    {refMeta.map((line) => (
                        <p key={line} className={styles.cardBankMeta}>{line}</p>
                    ))}
                    {investmentMetrics.map((line) => (
                        <p
                            key={line.text}
                            className={`${styles.cardMetrics} ${
                                line.variant === 'profit'
                                    ? styles.metricProfit
                                    : line.variant === 'loss'
                                      ? styles.metricLoss
                                      : ''
                            }`}
                        >
                            {line.text}
                        </p>
                    ))}
                    {metrics.map((line) => (
                        <p key={line} className={styles.cardMetrics}>{line}</p>
                    ))}
                    {utilization != null && (
                        <div className={styles.utilizationWrap}>
                            <div
                                className={styles.utilizationTrack}
                                role="progressbar"
                                aria-valuenow={utilization}
                                aria-valuemin={0}
                                aria-valuemax={100}
                                aria-label={`Credit utilization ${utilization} percent`}
                            >
                                <div
                                    className={`${styles.utilizationFill} ${utilization >= 80 ? styles.utilizationFillHigh : ''}`}
                                    style={{ width: `${utilization}%` }}
                                />
                            </div>
                            <p className={styles.utilizationLabel}>{utilization}% of limit used</p>
                        </div>
                    )}
                    {acc.payment_history && acc.payment_history.length > 0 && (
                        <details className={styles.paymentHistory}>
                            <summary>
                                {acc.investment_mode === 'sip' ? 'SIP history' : 'Payment history'} (
                                {acc.payment_history.length})
                            </summary>
                            <ul>
                                {acc.payment_history.map((p) => (
                                    <li key={`${p.date}-${p.amount}`}>
                                        {p.date} — {formatInr(p.amount)}
                                    </li>
                                ))}
                            </ul>
                        </details>
                    )}
                </div>
                <div className={styles.cardMenuWrap} ref={menuRef}>
                    <button
                        type="button"
                        className={styles.cardMenuBtn}
                        aria-label={`Actions for ${acc.name}`}
                        aria-expanded={menuOpen}
                        aria-haspopup="menu"
                        onClick={() => setMenuOpen((open) => !open)}
                    >
                        ⋮
                    </button>
                    {menuOpen && (
                        <div className={styles.cardMenu} role="menu">
                            <button
                                type="button"
                                className={styles.cardMenuItem}
                                role="menuitem"
                                onClick={() => {
                                    setMenuOpen(false);
                                    onEdit(acc);
                                }}
                            >
                                Edit
                            </button>
                            <button
                                type="button"
                                className={`${styles.cardMenuItem} ${styles.cardMenuDanger}`}
                                role="menuitem"
                                onClick={() => {
                                    setMenuOpen(false);
                                    onDelete(acc);
                                }}
                            >
                                Delete
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
