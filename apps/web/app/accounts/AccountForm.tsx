'use client';

import type { Dispatch, FormEvent, SetStateAction } from 'react';
import type { Account, AccountType, CreateAccountRequest, InvestmentMode, LoanType } from '@/lib/api';
import {
    INVESTMENT_MODE_CONFIG,
    LOAN_DETAIL_CONFIG,
    type AccountTypeConfig,
    accountPlacementHint,
    accountTypeLabel,
    isInvestmentType,
    isLoanType,
    requiresParent,
    showsInstitution,
    showsParentLinkField,
    usesBankDetailFields,
    usesCreditLimitField,
    usesDematField,
    usesFolioField,
    usesMutualFundModeField,
    usesSipScheduleFields,
    usesUanField,
    usesInvestmentFdFields,
    usesInvestmentValuationFields,
    usesOpeningBalanceField,
} from '@/lib/accountDisplay';
import styles from './Accounts.module.css';

export interface AccountFormProps {
    form: CreateAccountRequest;
    setForm: Dispatch<SetStateAction<CreateAccountRequest>>;
    accounts: Account[];
    assetTypeConfig: AccountTypeConfig[];
    liabilityTypeConfig: AccountTypeConfig[];
    isEdit: boolean;
    saving: boolean;
    inline?: boolean;
    onSubmit: (e: FormEvent) => void;
    onCancel: () => void;
}

export default function AccountForm({
    form,
    setForm,
    accounts,
    assetTypeConfig,
    liabilityTypeConfig,
    isEdit,
    saving,
    inline,
    onSubmit,
    onCancel,
}: AccountFormProps) {
    return (
        <form
            className={`card ${styles.formCard} ${inline ? styles.inlineFormCard : ''}`}
            onSubmit={onSubmit}
        >
            <h2 className={styles.formTitle}>{isEdit ? 'Edit account' : 'New account'}</h2>
            <div className={styles.formGrid}>
                <div>
                    <label className={styles.label} htmlFor="acc-type">Type</label>
                    <select
                        id="acc-type"
                        className={styles.select}
                        value={form.account_type}
                        onChange={(e) =>
                            setForm((f) => ({
                                ...f,
                                account_type: e.target.value as AccountType,
                            }))
                        }
                    >
                        <optgroup label="Assets">
                            {assetTypeConfig.map((t) => (
                                <option key={t.value} value={t.value}>
                                    {t.label}
                                </option>
                            ))}
                        </optgroup>
                        <optgroup label="Liabilities">
                            {liabilityTypeConfig.map((t) => (
                                <option key={t.value} value={t.value}>
                                    {t.label}
                                </option>
                            ))}
                        </optgroup>
                    </select>
                    <p className={styles.fieldHint} id="acc-type-hint">
                        {accountPlacementHint(form.account_type)}
                    </p>
                </div>
                <div>
                    <label className={styles.label} htmlFor="acc-name">Name</label>
                    <input
                        id="acc-name"
                        className={styles.input}
                        value={form.name}
                        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                        placeholder="HDFC Savings"
                        required
                    />
                </div>
                {showsInstitution(form.account_type) && (
                    <div>
                        <label className={styles.label} htmlFor="acc-inst">
                            {form.account_type === 'wallet'
                                ? 'Provider (optional)'
                                : form.account_type === 'epf'
                                  ? 'Employer (optional)'
                                  : 'Institution (optional)'}
                        </label>
                        <input
                            id="acc-inst"
                            className={styles.input}
                            value={form.institution ?? ''}
                            onChange={(e) => setForm((f) => ({ ...f, institution: e.target.value }))}
                            placeholder={
                                form.account_type === 'wallet'
                                    ? 'PhonePe, Amazon Pay, Flipkart'
                                    : form.account_type === 'epf'
                                      ? 'Acme Corp, TCS, Infosys'
                                    : isInvestmentType(form.account_type)
                                      ? 'AMC, broker, or bank name'
                                      : 'HDFC Bank'
                            }
                        />
                    </div>
                )}
                {usesOpeningBalanceField(form.account_type) && (
                    <div>
                        <label className={styles.label} htmlFor="acc-opening-balance">
                            Opening balance (optional)
                        </label>
                        <input
                            id="acc-opening-balance"
                            type="number"
                            min={0}
                            step="0.01"
                            className={styles.input}
                            value={form.opening_balance ?? ''}
                            onChange={(e) =>
                                setForm((f) => ({
                                    ...f,
                                    opening_balance: e.target.value ? Number(e.target.value) : undefined,
                                }))
                            }
                            placeholder="50000"
                        />
                        <p className={styles.fieldHint}>
                            {usesInvestmentValuationFields(form.account_type)
                                ? 'Seeds transaction history; invested and current default to this when unset'
                                : 'Starting balance before imports or transactions'}
                        </p>
                    </div>
                )}
                {usesInvestmentValuationFields(form.account_type) && (
                    <>
                        <div>
                            <label className={styles.label} htmlFor="acc-invested">
                                Invested amount (optional)
                            </label>
                            <input
                                id="acc-invested"
                                type="number"
                                min={0}
                                step="0.01"
                                className={styles.input}
                                value={form.invested_amount ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        invested_amount: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="100000"
                            />
                            <p className={styles.fieldHint}>Total cost basis or contributions</p>
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-current">
                                Current value (optional)
                            </label>
                            <input
                                id="acc-current"
                                type="number"
                                min={0}
                                step="0.01"
                                className={styles.input}
                                value={form.current_value ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        current_value: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="125000"
                            />
                            <p className={styles.fieldHint}>Latest market or statement value</p>
                        </div>
                    </>
                )}
                {usesMutualFundModeField(form.account_type) && (
                    <div>
                        <label className={styles.label} htmlFor="acc-mf-mode">Investment type</label>
                        <select
                            id="acc-mf-mode"
                            className={styles.select}
                            value={form.investment_mode ?? 'one_time'}
                            onChange={(e) =>
                                setForm((f) => ({
                                    ...f,
                                    investment_mode: e.target.value as InvestmentMode,
                                }))
                            }
                        >
                            {INVESTMENT_MODE_CONFIG.map((mode) => (
                                <option key={mode.value} value={mode.value}>
                                    {mode.label}
                                </option>
                            ))}
                        </select>
                        <p className={styles.fieldHint}>
                            {INVESTMENT_MODE_CONFIG.find((m) => m.value === (form.investment_mode ?? 'one_time'))
                                ?.description}
                        </p>
                    </div>
                )}
                {usesSipScheduleFields(form.account_type, form.investment_mode ?? 'one_time') && (
                    <>
                        <div>
                            <label className={styles.label} htmlFor="acc-sip-amount">
                                Monthly SIP amount (₹)
                            </label>
                            <input
                                id="acc-sip-amount"
                                type="number"
                                min={0}
                                step="0.01"
                                className={styles.input}
                                value={form.emi_amount ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        emi_amount: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="5000"
                                required
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-sip-day">
                                SIP debit day (1–31)
                            </label>
                            <input
                                id="acc-sip-day"
                                type="number"
                                min={1}
                                max={31}
                                className={styles.input}
                                value={form.due_day ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        due_day: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="10"
                                required
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-sip-start">SIP start date</label>
                            <input
                                id="acc-sip-start"
                                type="date"
                                className={styles.input}
                                value={form.start_date ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({ ...f, start_date: e.target.value || undefined }))
                                }
                                required
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-sip-tenure">
                                Planned tenure (months, optional)
                            </label>
                            <input
                                id="acc-sip-tenure"
                                type="number"
                                min={1}
                                className={styles.input}
                                value={form.tenure_months ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        tenure_months: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="120"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-initial-sip-paid">
                                Installments already paid (optional)
                            </label>
                            <input
                                id="acc-initial-sip-paid"
                                type="number"
                                min={0}
                                className={styles.input}
                                value={form.initial_sip_paid_count ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        initial_sip_paid_count: e.target.value
                                            ? Number(e.target.value)
                                            : undefined,
                                    }))
                                }
                                placeholder="0"
                            />
                            <p className={styles.fieldHint}>
                                Use when you started the SIP before tracking here
                            </p>
                        </div>
                    </>
                )}
                {usesUanField(form.account_type) && (
                    <div>
                        <label className={styles.label} htmlFor="acc-folio">UAN (optional)</label>
                        <input
                            id="acc-folio"
                            className={styles.input}
                            value={form.folio_number ?? ''}
                            onChange={(e) => setForm((f) => ({ ...f, folio_number: e.target.value }))}
                            placeholder="101234567890"
                        />
                    </div>
                )}
                {usesFolioField(form.account_type) && (
                    <div>
                        <label className={styles.label} htmlFor="acc-folio">Folio number (optional)</label>
                        <input
                            id="acc-folio"
                            className={styles.input}
                            value={form.folio_number ?? ''}
                            onChange={(e) => setForm((f) => ({ ...f, folio_number: e.target.value }))}
                            placeholder="1234567890"
                        />
                    </div>
                )}
                {usesDematField(form.account_type) && (
                    <div>
                        <label className={styles.label} htmlFor="acc-demat">Demat ID (optional)</label>
                        <input
                            id="acc-demat"
                            className={styles.input}
                            value={form.demat_id ?? ''}
                            onChange={(e) => setForm((f) => ({ ...f, demat_id: e.target.value }))}
                            placeholder="IN3001234567890"
                        />
                    </div>
                )}
                {usesBankDetailFields(form.account_type) && (
                    <>
                        <div>
                            <label className={styles.label} htmlFor="acc-number">Account number (optional)</label>
                            <input
                                id="acc-number"
                                className={styles.input}
                                value={form.account_number ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({ ...f, account_number: e.target.value }))
                                }
                                placeholder="123456789012"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-ifsc">IFSC code (optional)</label>
                            <input
                                id="acc-ifsc"
                                className={styles.input}
                                value={form.ifsc_code ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({ ...f, ifsc_code: e.target.value.toUpperCase() }))
                                }
                                placeholder="HDFC0001234"
                                maxLength={11}
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-branch">Branch (optional)</label>
                            <input
                                id="acc-branch"
                                className={styles.input}
                                value={form.branch ?? ''}
                                onChange={(e) => setForm((f) => ({ ...f, branch: e.target.value }))}
                                placeholder="Koramangala, Bangalore"
                            />
                        </div>
                        <div className={styles.formGridFull}>
                            <label className={styles.label} htmlFor="acc-notes">Notes (optional)</label>
                            <input
                                id="acc-notes"
                                className={styles.input}
                                value={form.account_notes ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({ ...f, account_notes: e.target.value }))
                                }
                                placeholder="Joint account, salary account, etc."
                            />
                        </div>
                    </>
                )}
                {showsParentLinkField(form.account_type) && (
                    <div>
                        <label className={styles.label} htmlFor="acc-parent">
                            {requiresParent(form.account_type)
                                ? 'Linked bank account'
                                : 'Linked bank account (optional)'}
                        </label>
                        <select
                            id="acc-parent"
                            className={styles.select}
                            value={form.parent_account_id ?? ''}
                            onChange={(e) =>
                                setForm((f) => ({
                                    ...f,
                                    parent_account_id: e.target.value || undefined,
                                }))
                            }
                            required={requiresParent(form.account_type)}
                        >
                            <option value="">Select primary account…</option>
                            {accounts
                                .filter((a) => a.account_type === 'bank' || a.account_type === 'cash')
                                .map((a) => (
                                    <option key={a.id} value={a.id}>
                                        {a.name} ({accountTypeLabel(a.account_type)})
                                    </option>
                                ))}
                        </select>
                    </div>
                )}
                {isLoanType(form.account_type) && (
                    <>
                        <div>
                            <label className={styles.label} htmlFor="acc-loan-type">Loan type</label>
                            <select
                                id="acc-loan-type"
                                className={styles.select}
                                value={form.loan_type ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        loan_type: (e.target.value || undefined) as LoanType | undefined,
                                    }))
                                }
                            >
                                <option value="">Not specified</option>
                                {LOAN_DETAIL_CONFIG.map((t) => (
                                    <option key={t.value} value={t.value}>{t.label}</option>
                                ))}
                            </select>
                        </div>
                        {form.loan_type === 'other' && (
                            <div className={styles.formGridFull}>
                                <label className={styles.label} htmlFor="acc-loan-desc">Description</label>
                                <input
                                    id="acc-loan-desc"
                                    className={styles.input}
                                    value={form.loan_type_description ?? ''}
                                    onChange={(e) =>
                                        setForm((f) => ({ ...f, loan_type_description: e.target.value }))
                                    }
                                    placeholder="e.g. Gold loan from Muthoot"
                                    required
                                />
                            </div>
                        )}
                        <div>
                            <label className={styles.label} htmlFor="acc-sanctioned">Sanctioned amount (₹)</label>
                            <input
                                id="acc-sanctioned"
                                type="number"
                                min={0}
                                className={styles.input}
                                value={form.sanctioned_amount ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        sanctioned_amount: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="5000000"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-emi">Monthly EMI (₹)</label>
                            <input
                                id="acc-emi"
                                type="number"
                                min={0}
                                className={styles.input}
                                value={form.emi_amount ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        emi_amount: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="40000"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-tenure">Tenure (months)</label>
                            <input
                                id="acc-tenure"
                                type="number"
                                min={1}
                                className={styles.input}
                                value={form.tenure_months ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        tenure_months: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="240"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-loan-start">
                                Start date
                                {form.emi_amount != null &&
                                form.emi_amount > 0 &&
                                form.tenure_months != null &&
                                form.tenure_months > 0
                                    ? ' (required)'
                                    : ' (optional)'}
                            </label>
                            <input
                                id="acc-loan-start"
                                type="date"
                                className={styles.input}
                                value={form.start_date ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({ ...f, start_date: e.target.value || undefined }))
                                }
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-rate">Interest rate % (optional)</label>
                            <input
                                id="acc-rate"
                                type="number"
                                min={0}
                                step={0.01}
                                className={styles.input}
                                value={form.interest_rate ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        interest_rate: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="8.5"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-due">EMI due day (1–31)</label>
                            <input
                                id="acc-due"
                                type="number"
                                min={1}
                                max={31}
                                className={styles.input}
                                value={form.due_day ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        due_day: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="5"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-initial-emi-paid">
                                EMIs already paid (optional)
                            </label>
                            <input
                                id="acc-initial-emi-paid"
                                type="number"
                                min={0}
                                className={styles.input}
                                value={form.initial_emi_paid_count ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        initial_emi_paid_count: e.target.value
                                            ? Number(e.target.value)
                                            : undefined,
                                    }))
                                }
                                placeholder="12"
                            />
                            <p className={styles.fieldHint}>
                                Outstanding = sanctioned − (EMI × paid months). Requires sanctioned amount.
                            </p>
                        </div>
                    </>
                )}
                {usesInvestmentFdFields(form.account_type) && (
                    <>
                        <div>
                            <label className={styles.label} htmlFor="acc-fd-start">Start date</label>
                            <input
                                id="acc-fd-start"
                                type="date"
                                className={styles.input}
                                value={form.start_date ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({ ...f, start_date: e.target.value || undefined }))
                                }
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-fd-tenure">Tenure (months)</label>
                            <input
                                id="acc-fd-tenure"
                                type="number"
                                min={1}
                                className={styles.input}
                                value={form.tenure_months ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        tenure_months: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="12"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-fd-rate">Interest rate (%)</label>
                            <input
                                id="acc-fd-rate"
                                type="number"
                                min={0}
                                step={0.01}
                                className={styles.input}
                                value={form.interest_rate ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        interest_rate: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="7.25"
                            />
                        </div>
                    </>
                )}
                {usesCreditLimitField(form.account_type) && (
                    <>
                        <div>
                            <label className={styles.label} htmlFor="acc-limit">Credit limit (₹)</label>
                            <input
                                id="acc-limit"
                                type="number"
                                min={0}
                                className={styles.input}
                                value={form.credit_limit ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        credit_limit: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="500000"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-cc-due">Statement due day (1–31)</label>
                            <input
                                id="acc-cc-due"
                                type="number"
                                min={1}
                                max={31}
                                className={styles.input}
                                value={form.due_day ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        due_day: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="15"
                            />
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-initial-used">
                                Initial credit used (optional)
                            </label>
                            <input
                                id="acc-initial-used"
                                type="number"
                                min={0}
                                step="0.01"
                                className={styles.input}
                                value={form.initial_credit_used ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        initial_credit_used: e.target.value ? Number(e.target.value) : undefined,
                                    }))
                                }
                                placeholder="25000"
                            />
                            <p className={styles.fieldHint}>
                                Amount already owed when you start tracking this card
                            </p>
                        </div>
                        <div>
                            <label className={styles.label} htmlFor="acc-initial-used-date">
                                As-of date
                                {form.initial_credit_used != null && form.initial_credit_used > 0
                                    ? ' (required)'
                                    : ' (optional)'}
                            </label>
                            <input
                                id="acc-initial-used-date"
                                type="date"
                                className={styles.input}
                                value={form.initial_credit_used_date ?? ''}
                                onChange={(e) =>
                                    setForm((f) => ({
                                        ...f,
                                        initial_credit_used_date: e.target.value || undefined,
                                    }))
                                }
                            />
                        </div>
                    </>
                )}
            </div>
            <div className={styles.formActions}>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create account'}
                </button>
                <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
            </div>
        </form>
    );
}
