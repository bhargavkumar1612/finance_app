# Domain glossary — Finance Copilot

Shared language between the project owner, documentation, and code. Agents should read this before using domain terms in features, UI copy, or chat responses.

**Maintained by:** [domain-interview](../.cursor/skills/domain-interview/SKILL.md) sessions — do not guess; ask and record.

**Architecture (separate doc):** [AI_PRINCIPLES.md](./AI_PRINCIPLES.md)

---

## How to use this file

- **Canonical term** = preferred name in code, docs, and UI
- Every entry links to **related code**
- If code and this file disagree, run a domain-interview **audit** — do not silently pick one

---

## Core concepts

### Ledger (agent)

**Definition:** The specialized agent and tools that read/write financial facts from PostgreSQL — balances, transactions, accounts, imports. Source of truth for money; not the LLM.

**Synonyms (avoid in code/UI):** "AI memory", "chat database"

**Canonical in code:** `LedgerAgent`, `app/agents/ledger_agent.py`

**Not the same as:** **Ledger** as a generic accounting ledger book — here it is a code component name.

**Related code:**
- `app/agents/ledger_agent.py`
- `app/core/orchestrator.py`

**Decided on:** 2026-06-06

---

### Confirm before write

**Definition:** Mutations that change money or persistent records require a typed confirmation card (`transaction_confirm` pattern); the model proposes, the user confirms.

**Synonyms (avoid in code/UI):** "auto-save", "trust the AI"

**Canonical in code:** `CardType.transaction_confirm`, confirm flows in orchestrator and chat UI

**Related code:**
- `app/core/schemas.py`
- `app/core/orchestrator.py`
- `frontend/components/cards/TransactionConfirmCard.tsx`

**Decided on:** 2026-06-06

---

## Accounts and transactions

### Primary account

**Definition:** An original account that holds cash — bank accounts and cash reserve. Source accounts that fund or pay derived accounts.

**Synonyms (avoid in code/UI):** "main wallet" (ambiguous)

**Canonical in code:** `Account` with `account_type` `bank` or `cash`

**Cash UI:** Do **not** show institution field for `cash` — name alone is enough (e.g. "Home safe", "Petty cash" goes in `name`).

**Not the same as:** **Derived account** — credit cards, wallets, loans, and investments are not primary.

**Related code:**
- `app/db/models.py` (`Account`)
- `app/api/accounts.py`
- `frontend/app/accounts/page.tsx`

**Decided on:** 2026-06-06 (Round 5 — cash institution hidden in UI)

---

### Derived account

**Definition:** A credit card, online wallet, **loan**, or **investment** account that tracks liability, app-wallet cash, or holdings separately from primary bank/cash. Credit cards, loans, and investments require a linked bank; online wallets may optionally link to a bank.

**Synonyms (avoid in code/UI):** treating all derived accounts as requiring the same parent rules

**Canonical in code:** `Account` with `account_type` in `credit_card`, `wallet`, `loan`, or investment types; `parent_account_id` → primary `bank`/`cash` (required for credit_card, loan, investments; optional for wallet)

**Example:** HDFC credit card paid via `BILLPAY-CREDIT CARD HDFC` from HDFC savings; PhonePe wallet used standalone or topped up from HDFC savings; Parag Parikh MF linked to HDFC with SIP transfers.

**Not the same as:** **Primary account**

**Related code:**
- `app/db/models.py` (`Account.account_type`, `Account.parent_account_id`)
- `app/api/accounts.py`
- `app/services/account_types.py`

**Decided on:** 2026-06-06 (updated Round 5 — investments included)

---

### Account (UI label)

**Definition:** User-facing nav and page title for all account types (primary and derived). Keep **"Accounts"** in sidebar and chat; use type-specific labels in detail views when helpful ("Bank", "Credit card", "Online wallet", "Cash").

**Synonyms (avoid in code/UI):** renaming the nav to "Wallets" only

**Canonical in code:** Sidebar label `Accounts`, API `/v1/accounts`

**Related code:**
- `frontend/components/Sidebar.tsx`
- `app/api/accounts.py`

**Decided on:** 2026-06-06

---

### Online wallet (UI label)

**Definition:** An online wallet for UPI / app balances (PhonePe, Amazon Pay, Flipkart Pay, etc.). Can be tracked standalone or optionally linked to a primary bank for top-ups and payouts.

**Synonyms (avoid in code/UI):** bare "Wallet" in UI (ambiguous with physical wallet)

**Canonical in code:** `Account.account_type` = `wallet`; UI label **"Online wallet"**; provider in `institution` (e.g. PhonePe); `parent_account_id` optional

**Not the same as:** **Primary account** — online wallets are a separate derived type, not bank/cash

**Related code:**
- `app/services/account_types.py` (`DERIVED_TYPES`, `PARENT_LINKABLE_TYPES`)
- `frontend/lib/accountDisplay.ts`
- `frontend/app/accounts/page.tsx`

**Decided on:** 2026-06-06

---

### Bank account details (optional)

**Definition:** Optional metadata on **bank** accounts only — account number, IFSC, branch, and free-text notes (e.g. joint account, salary account).

**Synonyms (avoid in code/UI):** storing IFSC on cash or credit card accounts

**Canonical in code:** `Account.account_number`, `Account.ifsc_code`, `Account.branch`, `Account.account_notes` (all nullable; bank only)

**Related code:**
- `app/services/bank_account_details.py`
- `app/api/accounts.py`
- `frontend/app/accounts/page.tsx`

**Decided on:** 2026-06-06

---

### Opening balance

**Definition:** Optional starting value when onboarding mid-cycle — before imports or manual transactions. Applies to **primary** accounts (`bank`, `cash`) and **investment** accounts (seed holdings value).

**Synonyms (avoid in code/UI):** storing balance on `Account` row without a transaction

**Canonical in code:** Single `Transaction` with `source=opening_balance`, positive amount, `merchant="Opening balance"`, `category="Transfer"`, `nw_impact=transfer`

**Not the same as:** **Income** — opening balance counts toward account balance/holdings and net worth but not spending/income reports

**Related code:**
- `app/services/opening_balance.py`
- `app/services/account_types.py` (`OPENING_BALANCE_TYPES`)
- `app/api/accounts.py`

**Decided on:** 2026-06-06 (updated Round 5 — investments included)

---

### Transfer

**Definition:** Movement of value that does not change net worth — e.g. SIP / investments from bank to investment, or moving cash between own accounts without a new expense or liability event.

**Synonyms (avoid in code/UI):** "spending", "expense"

**Example:** `ACH DR-SBI MF SIP GROWTH` — bank debit that funds investments, not consumption spending.

**Not the same as:** **Spending**

**Related code:**
- `app/agents/ledger_agent.py` (`_compute_monthly_spend` via `app/services/spending.py`)

**Decided on:** 2026-06-06

---

### Recurring bill

**Definition:** Any fixed recurring obligation — rent, EMI, subscription (Netflix, Spotify), utilities on a schedule. One concept; no separate user-facing terms for subscription vs EMI vs bill.

**Synonyms (avoid in code/UI):** splitting into separate product concepts "subscription" vs "EMI" vs "bill" unless needed internally

**Canonical in code:** `RecurringBill`, `/v1/recurring-bills`

**Example:** Rent, home loan EMI, Netflix monthly charge.

**Related code:**
- `app/db/models.py` (`RecurringBill`)
- `app/api/recurring_bills.py`
- `app/services/recurring_suggestions.py`

**Decided on:** 2026-06-06

---

## Spending and analysis

### Spending

**Definition:** An action that **reduces net worth** — not merely a negative bank transaction.

| Activity | Counts as spending? | Net worth effect |
|----------|---------------------|------------------|
| Rent | Yes | Reduces |
| Purchases on credit card / new loan | Yes | Reduces (liability up) |
| EMI / loan payment | No | Increases (liability down) |
| Credit card bill payment (from bank) | No | Increases (liability down) |
| SIP / investments | No (transfer) | Neutral |
| Salary | No (income) | Increases |

**Synonyms (avoid in code/UI):** "all debits", "cash outflow" as synonyms for spending

**Canonical in code:** `_compute_monthly_spend`, `_analyze_category_spending`, `Intent.spending_analysis`

**Related code:**
- `app/agents/ledger_agent.py` (`_compute_monthly_spend`, `_analyze_category_spending`)
- `app/core/schemas.py` (`Intent.spending_analysis`)

**Decided on:** 2026-06-06

---

### Income

**Definition:** Inflows that increase net worth without being transfers — e.g. salary credits.

**Example:** `NEFT CR-SALARY-ACME TECH PVT LTD`

**Not the same as:** **Transfer**, **Spending**

**Related code:**
- `app/db/models.py` (`Transaction.amount` positive = credit)
- Import categorization in `app/ingestion/`

**Decided on:** 2026-06-06

---

### Net worth

**Definition:** Sum of all assets minus sum of all liabilities. Credit **limits** are not net worth; only **outstanding amounts owed** count as liabilities.

**Synonyms (avoid in code/UI):** "account balance total" as a substitute unless assets/liabilities are fully represented

**Canonical in code:** `_compute_net_worth`, `Intent.net_worth_query`, `Asset`, loan `Account`

**Related code:**
- `app/agents/ledger_agent.py` (`_compute_net_worth`)
- `app/db/models.py` (`Asset`, `Account`)
- `app/services/net_worth.py`

**Decided on:** 2026-06-06

---

### Envelope budgeting (YNAB-style)

**Definition:** Later-phase feature: assign income to category envelopes before spending; spend from assigned amounts; budget vs actual with tradeoffs when overspending. In scope — not current MVP UX.

**Synonyms (avoid in code/UI):** implying full YNAB workflow exists today

**Canonical in code:** `Intent.budget_vs_actual` (partial foundation)

**Not the same as:** **Spending analysis** alone — tracking past spend without proactive assignment

**Related code:**
- `app/agents/ledger_agent.py` (`_budget_vs_actual`)
- `app/core/schemas.py` (`Intent.budget_vs_actual`)

**Decided on:** 2026-06-06

---

## Import and data

### nw_impact (transaction semantics)

**Definition:** Canonical classification of how a transaction affects net worth. Stored on every `Transaction` as `nw_impact`.

**Values:** `spending` | `income` | `transfer` | `liability_payment` | `refund` | `unknown`

| Pattern (HDFC / import) | `nw_impact` | Notes |
|-------------------------|-------------|-------|
| `NEFT CR-SALARY`, salary credits | `income` | Increases NW |
| Merchant refund / reversal credit | `refund` | Increases NW; offsets prior spending in analytics |
| `NEFT DR-RENT`, UPI consumption | `spending` | Reduces NW |
| `ACH DR-* EMI`, loan payment | `liability_payment` | Increases NW (liability down) |
| `ACH DR-* SIP`, investments | `transfer` | Neutral NW |
| `BILLPAY-CREDIT CARD` | `liability_payment` | On primary bank; pays linked CC |
| Internal transfer between own accounts | `transfer` | Keywords: `NEFT DR-SELF`, `IMPS-SELF`, `TRANSFER TO` |
| CC swipe on derived CC account | `spending` | Import to CC account |

**Canonical in code:** `app/services/transaction_semantics.py`, `Transaction.nw_impact`

**Related code:**
- `app/ingestion/normalizer.py`
- `app/services/spending.py`

**Decided on:** 2026-06-06 (Round 2A)

---

### Refund

**Definition:** Credit that returns value from a prior purchase — increases net worth. Classified as `nw_impact=refund`, not salary income.

**Keywords:** `refund`, `reversal`, `rev-`, `cancelled`, `chargeback`

**Not the same as:** **Income** (salary), **Transfer**

**Decided on:** 2026-06-06 (Round 2A)

---

### Import dedupe

**Definition:** Fingerprints include `account_id` so the same narration on bank vs CC account are separate rows. Import review shows `suggested_nw_impact`; user can override before confirm.

**Rule:** Never auto-merge rows across accounts — duplicate detection is per account.

**Related code:**
- `app/ingestion/deduper.py`
- `frontend/components/ImportStatement.tsx`

**Decided on:** 2026-06-06 (Round 2A)

---

### CC outstanding (derived account)

**Definition:** For a linked `credit_card` account, outstanding owed = sum of `spending` amounts on that account minus `liability_payment` credits allocated to that card (from bank BILLPAY or CC-side payments).

**Hybrid net worth:** Primary bank/cash balance (txn sum) + investment holdings + manual `Asset` − CC outstanding − loan outstanding (from loan accounts).

**Related code:**
- `app/services/net_worth.py`
- `Account.parent_account_id`

**Decided on:** 2026-06-06 (Round 2B; Round 3 — manual Liability table merged into loan accounts)

---

### Initial credit used (credit card)

**Definition:** Optional starting liability when onboarding a credit card mid-cycle — the amount already owed before imports or manual transactions. User sets an **as-of date** (e.g. last statement date).

**Synonyms (avoid in code/UI):** storing outstanding on the `Account` row without a transaction; “opening balance” on a liability account

**Canonical in code:** Single seed `Transaction` with `source=initial_credit_used`, negative amount, `merchant="Initial credit used"`, `nw_impact=spending`, user-chosen `transaction_date`. API fields: `initial_credit_used`, `initial_credit_used_date` on create/update (credit_card only).

**Spending reports:** Counts as **spending** (same `nw_impact` as real charges) — owner decision Round 6.

**Not the same as:** **Credit limit** — limit is capacity, not debt. **Loan initial outstanding** — deferred; loans use disbursement transactions.

**Related code:**
- `app/services/initial_credit_used.py`
- `app/services/account_balances.py` (`liability_outstanding`)
- `app/api/accounts.py`
- `frontend/app/accounts/page.tsx` (`#acc-initial-used`, `#acc-initial-used-date`)

**Decided on:** 2026-06-06 (Round 6 — domain interview)

---

### Loan account (derived)

**Definition:** A loan tracked as a derived `Account` (`account_type=loan`) linked to a primary bank. Liability exists from disbursement (not from unused sanctioned amount). Shows sanctioned total, outstanding, amount paid, EMI schedule, and payment history.

**Synonyms (avoid in code/UI):** separate `/v1/liabilities` rows for the same loan (deprecated)

**Canonical in code:** `Account` with `account_type=loan`, `sanctioned_amount`, `emi_amount`, `tenure_months`, `start_date`, `loan_type`, optional `loan_type_description` when `loan_type=other`

**Start date:** **Required** on the loan form when `emi_amount` and `tenure_months` are set. Used for reference and future schedule features; EMI counts today remain transaction-based.

**loan_type values:** `home` | `personal` | `vehicle` | `education` | `other` (with free-text description)

**Liability timing:** Loan outstanding is zero until disbursement, **or** set via **initial EMIs paid** (sanctioned − EMI × paid months).

**Disbursement:** Bank credit + loan-account spending (dual-sided). Bank side may classify as `transfer` or `income` by narration.

**EMI payments:** Record on the loan account as `liability_payment` (positive amount). Bank-side EMI debits remain `liability_payment` on bank; mirror to loan account when tracking schedule.

**Initial EMIs paid:** Optional `initial_emi_paid_count` on loan create/edit (`#acc-initial-emi-paid`). Seeds full sanctioned disbursement plus pre-paid EMIs; **outstanding = sanctioned − (EMI × paid months)**. Requires `sanctioned_amount`; requires `emi_amount` when count &gt; 0.

**Related code:**
- `app/services/account_balances.py`
- `app/services/loan_schedule.py`
- `app/services/initial_loan_state.py`
- `app/api/accounts.py`

**Decided on:** 2026-06-06 (Round 3; Round 5 — start_date required with EMI + tenure)

---

### Investment account (derived)

**Definition:** A liquid investment tracked as a derived `Account` linked to a primary bank. Value = sum of transactions on the investment account (including optional `opening_balance` seed txn). Purchases from bank are `nw_impact=transfer` (not spending).

**Types:** `mutual_fund` | `fixed_deposit` | `recurring_deposit` | `stock`. **SIP** uses `mutual_fund` with `investment_mode=sip` (not a separate account type).

**Synonyms (avoid in code/UI):** legacy `/v1/assets` rows for mf/stock (kept for backward compatibility only)

**Canonical in code:** `Account` with `account_type` in investment types; **required** `parent_account_id` → primary `bank`/`cash`; optional `opening_balance` on create/edit; optional stored `invested_amount` (cost basis) and `current_value` (market value) with computed `pnl_amount` / `pnl_percent`; optional `folio_number` (MF, RD) or `demat_id` (stock) for reference only; FD/RD reuse `start_date`, `tenure_months`, `interest_rate`; **MF SIP** uses `investment_mode` (`one_time` | `sip`), reuses `emi_amount` (monthly SIP), `due_day`, `start_date`, optional `tenure_months`, and tracks installments via transfer transactions + `payment_history`

**UI label:** Show **Invested ₹X · Current ₹Y · P&L ±Z%** — investments are not spendable cash. Net-worth and hero totals use **current value** when set.

**Net worth:** Investment **current values** roll into `investment_holdings` (separate from cash/wallet in breakdown).

**Not the same as:** **Physical asset** (`property`, `gold`) — those stay on the `Asset` table with manual `current_value`.

**Related code:**
- `app/services/account_types.py` (`INVESTMENT_TYPES`, `OPENING_BALANCE_TYPES`)
- `app/services/opening_balance.py`
- `app/services/net_worth.py`
- `app/services/transaction_semantics.py`
- `frontend/lib/accountDisplay.ts`

**Decided on:** 2026-06-06 (Phase 2; Round 5 — folio/demat fields; 2026-06-07 — invested/current/P&L)

---

### EPF account (standalone asset)

**Definition:** Employee Provident Fund — employer-managed retirement corpus tracked as a standalone `Account` (`account_type=epf`). No linked bank required. Value = transaction sum + optional `opening_balance` seed (same as other holdings).

**Canonical in code:** `Account.account_type` = `epf`; optional `institution` (employer name); optional `folio_number` stores **UAN**; optional `opening_balance`; appears under **Assets → Investments** in UI.

**UI label:** **Invested / Current / P&L** (not spendable cash). Reference line shows masked **UAN**.

**Net worth:** EPF balance rolls into `investment_holdings`.

**Not the same as:** Liquid investment accounts (MF/FD/stock) — EPF does not require `parent_account_id`.

**Related code:**
- `app/services/account_types.py` (`RETIREMENT_TYPES`, `HOLDINGS_TYPES`)
- `frontend/lib/accountDisplay.ts` (`usesUanField`, `isInvestmentType`)

**Decided on:** 2026-06-06

---

### Derived account linking (Round 2B, updated Round 3)

**Rules:**
- `credit_card`, **`loan`**, and **liquid investment accounts** (`mutual_fund`, `fixed_deposit`, `recurring_deposit`, `stock`) **require** `parent_account_id` pointing to a `bank` or `cash` account.
- **`epf`** is standalone — no `parent_account_id` required.
- **`wallet` (online wallet)** may be standalone; `parent_account_id` is **optional** when the user wants to track bank affiliation (e.g. PhonePe linked to HDFC).
- **One parent per derived account** when linked (many derived accounts may share one bank).
- CC statement imports target the derived CC account; bank BILLPAY targets the primary bank.
- Loan EMIs and disbursements are affiliated with the linked bank account when set.

**Decided on:** 2026-06-06 (Round 2B; Round 3 — loan; Round 5 — investments)

**Definition:** For `fixed_deposit` and `recurring_deposit`, save `start_date`, `tenure_months`, and `interest_rate` on the Account. The card shows these planning fields plus a **computed maturity date** (start + tenure months). Principal/value still comes from transaction sum + optional opening balance.

**Synonyms (avoid in code/UI):** storing maturity date as a separate DB column when it can be derived

**Canonical in code:** `Account.start_date`, `Account.tenure_months`, `Account.interest_rate`; maturity computed in UI/display layer

**Not the same as:** **Loan EMI schedule** — FD/RD maturity is informational; no auto-generated EMI txns from these fields alone

**Related code:**
- `app/api/accounts.py`
- `frontend/lib/accountDisplay.ts`
- `frontend/app/accounts/page.tsx`

**Decided on:** 2026-06-06 (Round 5)

---

### Investment reference IDs (folio / demat)

**Definition:** Optional reference metadata on investment accounts — not used in balance math. **folio_number** on `mutual_fund` and `recurring_deposit`; **demat_id** on `stock`. Reference only; no units, NAV, or holdings breakdown yet.

**Synonyms (avoid in code/UI):** mixing folio and demat into one ambiguous "account number" field

**Canonical in code:** `Account.folio_number` (MF, RD); `Account.demat_id` (stock) — new columns; validated type-gated like bank details

**Related code:**
- `app/db/models.py`
- `app/api/accounts.py`
- `frontend/app/accounts/page.tsx`

**Decided on:** 2026-06-06 (Round 5)

---

### Credit card statement due day

**Definition:** Optional day-of-month (1–31) for when the credit card bill is due. Saved on the `Account` row (`due_day`). Intended to link to **recurring bill** reminders in a later slice — not auto-created on save.

**Synonyms (avoid in code/UI):** reusing loan EMI due day semantics on CC without labeling it as statement due

**Canonical in code:** `Account.due_day` on `credit_card` only (cleared on other types)

**Related code:**
- `app/api/accounts.py`
- `app/db/models.py` (`RecurringBill` — future link)

**Decided on:** 2026-06-06 (Round 2B; Round 3 — loan; Round 5 — investments)

---

## Chat and copilot

### Copilot advice boundary

**Definition:** Chat shows **facts from Ledger only** (invested/current/P&L, allocation %, “Fund X is down 12%”) plus **deterministic suggestions that can increase net worth**. No buy/sell picks, no specific fund recommendations, no tax filing advice.

**Allowed suggestion types:** increase SIP when surplus allows; pay high-interest debt first; update stale `current_value`; log missing salary/SIP/EMI; move idle bank cash to FD/RD (informational); 80C/tax-saving nudge (rules-only).

**Synonyms (avoid in code/UI):** “investment advice”, “you should buy X”

**Related code:**
- `app/agents/insight_agent.py`
- `app/services/missing_data.py`
- `app/agents/ledger_agent.py` (`compute_affordability`)

**Decided on:** 2026-06-07 (Round 8 — AI chat interview)

---

### Portfolio dashboard (chat)

**Definition:** Primary investment answer in chat — a **one-time visual dashboard** card with hero totals, rankings, and charts. Scope includes **all wealth the user tracks**: cash (bank + online wallet), **Account holdings** (MF, FD, RD, stock, EPF), and **physical `Asset`** rows (property, gold — value only, usually no P&L).

**Rankings (deterministic, from Ledger):**

| Ranking | Sort key |
|---------|----------|
| Most liquid → least | Fixed liquidity stack (see **Liquidity rank**) |
| Most valuable | **Current value** (`current_value` or txn balance fallback) |
| Most profitable | **Both** P&L **%** and P&L **₹** — separate top lists / bar charts |

**Missing `current_value`:** Fall back to txn balance; label **“as per ledger”** in UI copy.

**UX pattern:** **Primary dashboard + drill-down intents** — e.g. “show allocation pie”, “show P&L bars”. Hide chart sections the user has **no stake in** (zero accounts / zero value); use **Financial persona** to prioritize which drill-downs to suggest. Card **footer** always shows net-worth-increasing **suggested actions** (add account type user lacks, update values, log SIP, etc.).

**Synonyms (avoid in code/UI):** LLM-estimated portfolio value

**Canonical in code:** `Intent.portfolio_summary`, Ledger tool in `portfolio_summary.py`; `CardType.investment_portfolio_dashboard`; drill-downs `investment_pnl_bars`, `investment_pie_chart`

**Related code:**
- `app/services/investment_valuation.py`
- `app/services/net_worth.py`
- `app/services/account_grouping.py`
- `apps/web/components/cards/SpendingDashboardCard.tsx` (visual template)
- `apps/web/components/cards/InvestmentPieChartCard.tsx`

**Decided on:** 2026-06-07 (Round 8)

---

### Liquidity rank (portfolio ordering)

**Definition:** Canonical **most liquid → least liquid** order for portfolio dashboard sorting. Encoded in application code — not user-editable.

| Rank | Bucket |
|------|--------|
| 1 | `bank`, `cash`, `wallet` (spendable cash) |
| 2 | `stock` |
| 3 | `mutual_fund` |
| 4 | `recurring_deposit` |
| 5 | `fixed_deposit` |
| 6 | `epf` |
| 7 | Physical **`Asset`** (property, gold, etc.) |

**Related code:**
- `app/services/account_types.py`
- Portfolio Ledger tool *(planned)*

**Decided on:** 2026-06-07 (Round 8)

---

### SIP status (chat)

**Definition:** Chat answer for SIP mutual funds — per fund and aggregate. Fields shown:

- **Last paid on** — date of most recent qualifying transfer installment
- **Next expected on** — computed from `due_day` / schedule when not yet paid this month
- **Already paid in {Month}** — when a qualifying installment exists in the **current calendar month**

Qualifying installment = positive `nw_impact=transfer` txn on the MF account matching SIP logic in `compute_sip_schedule`.

**Synonyms (avoid in code/UI):** inferring payment from bank debit alone without MF account txn

**Canonical in code:** `Intent.sip_status_query`, `compute_sip_schedule`, `CardType.sip_schedule_summary`

**Related code:**
- `app/services/mf_sip_schedule.py`
- `app/services/mf_investment_mode.py`

**Decided on:** 2026-06-07 (Round 8)

---

### Record transfer (chat)

**Definition:** Confirm-before-write flow for SIP / investment funding — **dual-leg cycle** in one confirmation: **bank debit** (`nw_impact=transfer`, negative on parent bank) + **MF/holdings credit** (`nw_impact=transfer`, positive on investment account). Requires linked `parent_account_id` when investment account has a parent bank.

**Synonyms (avoid in code/UI):** recording SIP as `add_expense` / spending

**Canonical in code:** `Intent.record_transfer`, `CardType.transaction_confirm`

**Related code:**
- `app/services/transaction_semantics.py`
- `app/agents/ledger_agent.py`
- `frontend/components/cards/TransactionConfirmCard.tsx`

**Decided on:** 2026-06-07 (Round 8)

---

### Affordability (committed obligations)

**Definition:** Safe EMI / surplus calculation **must subtract all committed outflows** before answering “can I afford X?”:

- All **loan** `emi_amount` values
- All **SIP** `emi_amount` on `mutual_fund` + `investment_mode=sip`
- All active **`RecurringBill`** amounts
- **Credit card** payment commitments (minimum or statement due when tracked)

Numbers remain deterministic — never from LLM.

**Related code:**
- `app/agents/ledger_agent.py` (`compute_affordability`)
- `app/db/models.py` (`RecurringBill`, `Account`)

**Decided on:** 2026-06-07 (Round 8)

---

### Obligations hub (chat)

**Definition:** Single chat card for “what’s due this month?” with **grouped sections**: SIPs | Loan EMIs | Recurring bills | Credit card due days. CC `due_day` shows even without a linked `RecurringBill` (informational). Sorted by date within each section.

**Canonical in code:** `Intent.upcoming_obligations`, `CardType.obligation_list`

**Related code:**
- `app/services/mf_sip_schedule.py`
- `app/services/loan_schedule.py`
- `app/api/recurring_bills.py`
- `app/db/models.py` (`Account.due_day`)

**Decided on:** 2026-06-07 (Round 8)

---

### Financial persona

**Definition:** Per-user **derived profile** stored server-side (markdown or structured fields in DB) — **not shown raw** by default. Built from **rules** (salary pattern, missing-data flags, account mix) plus **LLM summary after each chat session**. User may **view and edit** in Settings. Used for **proactive nudge copy** on Accounts + chat (expand to other surfaces later) and to **tailor which portfolio drill-downs / footer suggestions** to show — hide areas user has no stake in; suggest onboarding actions they lack.

**Persona fields (all in scope):** income pattern (salary day, avg surplus); spending personality (category skew); investment style (SIP-regular vs lump-sum); risk/tone preference; goals mentioned in chat.

**Privacy:** Stored per user in PostgreSQL; fed to Insight/orchestrator context — not logged in plain text to external systems beyond configured LLM provider.

**Synonyms (avoid in code/UI):** “AI memory” replacing Ledger facts

**Canonical in code:** `UserFinancialPersona` — see [decisions/002-financial-persona.md](./decisions/002-financial-persona.md)

**Related code:**
- `app/core/orchestrator.py`
- `app/agents/insight_agent.py`
- `apps/web/app/settings/page.tsx` (editor live)

**Decided on:** 2026-06-07 (Round 8)

---

### Proactive nudges

**Definition:** Rule-based hints (missing salary, missed SIP, stale investment values, etc.) surfaced **proactively** — not only when user asks. Surfaces: **chat** (session/open) and **Accounts** page; may expand to home/dashboard. Copy personalized via **Financial persona** where available.

**Related code:**
- `app/services/missing_data.py`
- `app/api/hints.py` (`GET /v1/hints`)
- `apps/web/app/accounts/page.tsx`
- `apps/web/app/chat/page.tsx`

**Decided on:** 2026-06-07 (Round 8)

---

### Chat intents (phrase map)

| User phrase | Intent |
|-------------|--------|
| "where did my money go", "spending breakdown", "pie chart" | `spending_analysis` |
| "what's my net worth", "how much am I worth" | `net_worth_query` |
| "how are my investments", "MF P&L", "portfolio", "allocation" | `portfolio_summary` |
| "show allocation", "investment pie" | `investment_allocation` |
| "show P&L", "best performers", "profit on funds" | `portfolio_pnl_drilldown` |
| "did I pay SIP", "SIPs due", "installments left" | `sip_status_query` |
| "when does FD mature", "RD ending" | `fd_maturity_query` → `fd_maturity_summary` card |
| "EMIs left", "loan payoff", "total EMI" | `loan_emi_summary` / `debt_payoff_planner` |
| "what's due this month", "upcoming bills" | `upcoming_obligations` |
| "add expense", "I spent", "paid for" | `add_expense` (confirm before write) |
| "record SIP", "transfer to MF", "fund my SIP" | `record_transfer` |
| "salary", "got paid", "record income" | `add_income` |
| "can I afford", "safe EMI" | `affordability_check` |
| "recurring bills", "subscriptions", "rent due" | `list_recurring_bills` |
| "import statement", "upload CSV" | `import_statement` → `import_guide` card |
| "explain this charge", "what did I spend at X" | `explain_transaction` → `transaction_detail` card |
| "recategorize X to Y", "change category of X to Y" | `recategorize_transaction` → confirm → update |
| "add SIP account", "create MF account", "add EPF" | `create_account_guided` → `account_create_confirm` card |
| "cash flow", "top expenses", "unusual spending" | Phase 4 analytics intents |

**Decided on:** 2026-06-06 (Round 4); expanded 2026-06-07 (Round 8, S3.2–3.4)

---

## Look and feel (UI)

### Theme pack

**Definition:** A full visual palette — background, surfaces, accent, semantic colors, chart colors, and account-type colors together. User selects one pack on the Settings page; choice persists in `localStorage` (`fc_prefs`).

**Values:** `paper` (light default) | `midnight` | `coral` | `slate`

**Synonyms (avoid in code/UI):** "dark mode toggle only" when referring to full packs

**Canonical in code:** `data-theme` on `<html>`, [`apps/web/app/themes.css`](apps/web/app/themes.css), [`apps/web/lib/themes/packs.ts`](apps/web/lib/themes/packs.ts)

**Related code:**
- `apps/web/lib/ThemeContext.tsx`
- `apps/web/app/settings/page.tsx`

**Decided on:** 2026-06-07 (Round 7)

---

### Density

**Definition:** Layout spacing preset — **comfortable** (default) or **compact**. Affects card padding, nav item height, page padding, and base font size.

**Canonical in code:** `data-density` on `<html>`, overrides in [`apps/web/app/themes.css`](apps/web/app/themes.css)

**Related code:**
- `apps/web/lib/ThemeContext.tsx`
- `apps/web/app/settings/page.tsx`

**Decided on:** 2026-06-07 (Round 7)

---

### Typography (font family and size)

**Definition:** User-controlled text appearance. **Theme default** mode applies a curated font per theme pack; **Custom** mode keeps the user's chosen font across theme changes. Text size is independent (`small` | `medium` | `large`).

**Theme default fonts:**

| Theme pack | Default font |
|------------|--------------|
| `paper` | DM Sans |
| `midnight` | Geist |
| `coral` | Lora |
| `slate` | Inter |

**Custom font catalog:** Geist, Inter, DM Sans, Lora, Source Serif, JetBrains Mono

**Canonical in code:** `data-font`, `data-font-size`, `data-font-mode` on `<html>`, [`apps/web/lib/themes/fonts.ts`](apps/web/lib/themes/fonts.ts)

**Related code:**
- `apps/web/lib/ThemeContext.tsx`
- `apps/web/app/settings/page.tsx`
- `apps/web/app/themes.css` (font size scale)

**Decided on:** 2026-06-07 (Round 7 typography)

---

### Semantic amount colors

**Definition:** UI color rules for money display — not bank debit/credit semantics.

| Meaning | Color token | CSS class |
|---------|-------------|-----------|
| Asset / net worth up | `--success` (green) | `.amount-asset` |
| Liability / owed | `--danger` (red) | `.amount-liability` |
| Neutral (transfers, etc.) | `--neutral` (blue) | `.amount-neutral` |

**Synonyms (avoid in code/UI):** hard-coded `#10b981` / `#ef4444` in components

**Related code:**
- `apps/web/app/globals.css`
- Chat cards, accounts page, transactions

**Decided on:** 2026-06-07 (Round 7)

---

### Account type icon

**Definition:** Fixed Lucide icon + color per `AccountType` (and loan subtype). Rendered via `AccountTypeIcon` — no emoji.

**Synonyms (avoid in code/UI):** emoji symbols, `accountTypeSymbol()`

**Canonical in code:** `AccountTypeIcon`, [`apps/web/lib/themes/accountTypes.ts`](apps/web/lib/themes/accountTypes.ts)

**Related code:**
- `apps/web/app/accounts/page.tsx`
- `apps/web/components/cards/AccountListCard.tsx`

**Decided on:** 2026-06-07 (Round 7)

---

## Identity and access

### Username (login identifier)

**Definition:** Unique string the user chooses at registration — **not required** to be a valid email address. Used for login and displayed in the user menu. Replaces the legacy dev-only "email-only" login.

**Synonyms (avoid in code/UI):** "email" on login/register forms (deprecated for auth UX)

**Canonical in code:** `User.username` (migrate from `User.email`); API fields `username`; UI label **Username**

**Example:** `bhargav`, `family-hdfc`, `priya-main`

**Not the same as:** Email delivery — no automated email in v1

**Related code:**
- `app/db/models.py` (`User`)
- `app/api/auth.py` *(to be replaced)*
- `apps/web/app/login/page.tsx`
- `apps/web/lib/AuthContext.tsx`

**Decided on:** 2026-06-07 (Round 9)

---

### User status

**Definition:** Gate for whether a registered user may use the app.

| Status | Meaning |
|--------|---------|
| `pending` | Registered; awaiting super admin approval — **cannot log in** |
| `approved` | May log in with username + password |
| `rejected` | Signup denied; same username blocked for **24h** cool-off (super admin may override) |
| `disabled` | Login blocked; **data retained** until hard delete |

**Synonyms (avoid in code/UI):** "active/inactive" without mapping to these four values

**Canonical in code:** `User.status` enum

**Related code:**
- `app/db/models.py` (`User`)
- `docs/decisions/003-auth-super-admin.md`

**Decided on:** 2026-06-07 (Round 9)

---

### Super admin

**Definition:** Bootstrap account (created via one-time script/migration) with full user-management powers: view user count, approve/reject signups, handle forgot-password queue, disable or hard-delete users, set new passwords offline.

**Synonyms (avoid in code/UI):** "admin user" without role check

**Canonical in code:** `User.role` = `super_admin`; Admin UI at `/admin`; API prefix `/v1/admin/*`

**Not the same as:** Normal **approved** user — no access to other users' data

**Related code:**
- `app/api/auth.py` *(admin routes)*
- `apps/web/app/admin/` *(planned)*

**Decided on:** 2026-06-07 (Round 9)

---

### Signup approval queue

**Definition:** List of **`pending`** registrations waiting for super admin **approve** or **reject**. Approved users may log in; rejected usernames enter 24h cool-off unless super admin overrides.

**Synonyms (avoid in code/UI):** open self-registration

**Canonical in code:** `User.status=pending`; Admin UI section "Pending signups"

**Related code:**
- `docs/decisions/003-auth-super-admin.md`
- `apps/web/app/admin/` *(planned)*

**Decided on:** 2026-06-07 (Round 9)

---

### Password reset queue

**Definition:** Forgot-password requests from approved users. Super admin sets a **new password** in Admin UI and shares it **offline** — no email automation.

**Synonyms (avoid in code/UI):** "send reset link", "magic link"

**Canonical in code:** `PasswordResetRequest` or equivalent; Admin UI section "Password resets"

**Related code:**
- `docs/decisions/003-auth-super-admin.md`
- `apps/web/app/admin/` *(planned)*

**Decided on:** 2026-06-07 (Round 9)

---

### Session token

**Definition:** Long-lived bearer token issued on successful login (approved user only). Stored in browser **`localStorage`**; sent as `Authorization: Bearer …` on API calls. Replaces `X-User-Email` header trust.

**Synonyms (avoid in code/UI):** trusting `X-User-Email`, `dev@local` fallback in production

**Canonical in code:** `get_current_user` validates token; `localStorage` key e.g. `finance_auth_token`

**Related code:**
- `app/api/auth.py`
- `apps/web/lib/api.ts` (`authHeaders`)
- `apps/web/lib/AuthContext.tsx`

**Decided on:** 2026-06-07 (Round 9)
