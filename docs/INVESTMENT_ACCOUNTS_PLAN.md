# Investment accounts (Phase 2) — implementation plan

**Status:** Implemented (2026-06-06); Phase 2.1 drift closure (2026-06-07)

## Phase 2.1 — Drift closure (Round 5)

| ID | Change |
|----|--------|
| D1 | Investment card label: **Holdings ₹X** |
| D2 | FD/RD card: start, tenure, rate + computed maturity |
| D3 | Loan `start_date` required when EMI + tenure set |
| D4 | Cash: hide institution field in UI |
| D5 | CC `due_day` persists (statement due day) |
| D6 | API OpenAPI descriptions aligned with glossary |
| D7 | Accounts page subtitle mentions investments |

Tests: REG-F046–F048; integration tests in `test_accounts_api.py`.

## Canonical decisions

| Topic | Rule |
|-------|------|
| **Liquid investments** | Derived `Account` types: `mutual_fund`, `fixed_deposit`, `recurring_deposit`, `stock` |
| **SIP** | `mutual_fund` with `investment_mode=sip`; monthly amount in `emi_amount`, debit day in `due_day`, `start_date`, optional `tenure_months`; installments tracked from positive transfer txns |
| **Parent bank** | Required for all investment types |
| **Value** | Sum of transactions on the investment account; optional `opening_balance` txn to seed holdings |
| **Net worth** | Investment balances count toward assets (separate from cash/wallet) |
| **FD / RD planning** | Reuse `start_date`, `tenure_months`, `interest_rate` on Account |
| **Physical / illiquid** | Stay on `Asset` table (`property`, `gold`, etc.) — separate UI later |
| **Legacy `/v1/assets` mf/stock** | Kept for backward compatibility; new holdings use Account types |

## Delivery slices

1. `account_types` + balances + net worth + opening balance
2. Accounts API + ledger/planner tools
3. Frontend accounts form + cards
4. Integration + E2E tests

## Phase 2.2 — Investment reference IDs

| Field | Types |
|-------|-------|
| `folio_number` | mutual_fund, recurring_deposit |
| `demat_id` | stock |

Migration `009_investment_reference_ids.py`; service `investment_account_details.py`. Tests: REG-F051–F052.

## Phase 2.3 — Mutual fund one-time vs SIP

| Field | SIP mode |
|-------|----------|
| `investment_mode` | `one_time` (default) or `sip` |
| `emi_amount` | Monthly SIP amount |
| `due_day` | SIP debit day (1–31) |
| `start_date` | SIP start date |
| `tenure_months` | Optional planned installments |
| `initial_sip_paid_count` | Installments paid before tracking |

Installments = positive `transfer` transactions on the MF account (excludes opening balance seed). Card shows paid/pending counts and expandable SIP history.

Migration `011_account_investment_mode.py`; services `mf_investment_mode.py`, `mf_sip_schedule.py`, `initial_sip_state.py`. Tests: REG-F061; integration in `test_accounts_api.py`.
