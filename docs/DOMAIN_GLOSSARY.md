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

**Not the same as:** **Derived account** — credit cards and online wallets are not primary.

**Related code:**
- `app/db/models.py` (`Account`)
- `app/api/accounts.py`
- `frontend/app/accounts/page.tsx`

**Decided on:** 2026-06-06

---

### Derived account

**Definition:** A credit card or online wallet (e.g. Paytm) that is always connected to a primary bank account and refilled or paid from that bank. Not a standalone source of cash.

**Synonyms (avoid in code/UI):** treating wallets as independent cash pools unrelated to a bank

**Canonical in code:** `Account` with `account_type` `credit_card` or `wallet`, `parent_account_id` → primary `bank`/`cash`

**Example:** HDFC credit card paid via `BILLPAY-CREDIT CARD HDFC` from HDFC savings.

**Not the same as:** **Primary account**

**Related code:**
- `app/db/models.py` (`Account.account_type`)
- `app/api/accounts.py`

**Decided on:** 2026-06-06

---

### Account (UI label)

**Definition:** User-facing nav and page title for all account types (primary and derived). Keep **"Accounts"** in sidebar and chat; use type-specific labels in detail views when helpful ("Bank", "Credit card", "Wallet", "Cash").

**Synonyms (avoid in code/UI):** renaming the nav to "Wallets" only

**Canonical in code:** Sidebar label `Accounts`, API `/v1/accounts`

**Related code:**
- `frontend/components/Sidebar.tsx`
- `app/api/accounts.py`

**Decided on:** 2026-06-06

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

**Canonical in code:** `_compute_net_worth`, `Intent.net_worth_query`, `Asset`, `Liability`

**Related code:**
- `app/agents/ledger_agent.py` (`_compute_net_worth`)
- `app/db/models.py` (`Asset`, `Liability`)

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

**Hybrid net worth:** Primary bank/cash balance (txn sum) + manual `Asset` − CC outstanding − manual `Liability`.

**Related code:**
- `app/services/net_worth.py`
- `Account.parent_account_id`

**Decided on:** 2026-06-06 (Round 2B)

---

### Derived account linking (Round 2B)

**Rules:**
- `credit_card` and `wallet` **require** `parent_account_id` pointing to a `bank` or `cash` account.
- **One parent per derived account** (many derived accounts may share one bank).
- CC statement imports target the derived CC account; bank BILLPAY targets the primary bank.

**Decided on:** 2026-06-06 (Round 2B)

---

## Chat and intents

| User phrase | Intent |
|-------------|--------|
| "where did my money go", "spending breakdown", "pie chart" | `spending_analysis` |
| "what's my net worth", "how much am I worth" | `net_worth_query` |
| "add expense", "I spent", "paid for" | `add_expense` (confirm before write) |
| "salary", "got paid", "record income" | `add_income` |
| "can I afford", "safe EMI" | `affordability_check` |
| "recurring bills", "subscriptions", "rent due" | `list_recurring_bills` |
| "import statement" | `import_statement` |

**Decided on:** 2026-06-06 (Round 4 — recorded during implementation)
