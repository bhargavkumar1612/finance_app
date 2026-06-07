# Regression test plan — Finance Copilot

**Audience:** Regression tester agent (manual browser QA, curl/API checks, or pytest).  
**Goal:** Run A→Z scenarios after every meaningful change; report pass/fail with scenario IDs.

**Related:** [DOMAIN_GLOSSARY.md](./DOMAIN_GLOSSARY.md) (pass/fail rules), [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) (confirm-before-write), [DRIFT_AUDIT.md](./DRIFT_AUDIT.md) (known gaps).

---

## How the regression agent should work

1. **Start stack:** `docker compose up --build` (or confirm already running). Health: `GET http://localhost:8000/health` → `{"status":"ok"}`.
2. **Use a fresh user** when testing auth/setup (`test+regression@local`) or **reset DB** between full runs (`docker compose down -v && docker compose up --build`) for isolation.
3. **Auth header:** All `/v1/*` calls need `X-User-Email: <email>` (UI stores email in `localStorage` as `finance_user`).
4. **Record results** in this format:

   ```text
   REG-X### | PASS | brief note
   REG-X### | FAIL | expected vs actual + screenshot/log snippet
   REG-X### | BLOCK | dependency missing (e.g. import 500)
   REG-X### | SKIP | reason (no LLM, no PDF fixture, etc.)
   ```

5. **Priority:** Run **P0** every time; **P1** before merge; **P2** weekly or before release.
6. **Do not assert exact LLM wording** — check `status`, `ui_type`, `card_payload` shape, and DB/API facts only.
7. **Money is source of truth in PostgreSQL** — after chat/import, verify via `GET /v1/transactions` or UI ledger, not chat prose.

### Automated baseline

```bash
pytest tests/ -q
```

Maps to many scenarios below; run first. Integration tests need Postgres + Redis (docker-compose test profile or running stack).

### Sample fixtures

| Fixture | Path |
|---------|------|
| HDFC 12-month CSV | `data/hdfc_12_months_sample.csv` |
| Minimal import CSV | see `tests/test_import_api.py` `sample_csv_bytes` |

---

## Domain rules (pass/fail cheat sheet)

| Rule | Pass | Fail |
|------|------|------|
| **Spending** | Only `nw_impact=spending` counts in spend analytics | All debits treated as spending |
| **Income** | Salary/credits → `nw_impact=income` | Salary shown as spending |
| **EMI / CC bill pay** | `nw_impact=liability_payment`; excluded from spending | EMI counted as spending |
| **SIP / self-transfer** | `nw_impact=transfer`; neutral NW | SIP counted as spending |
| **Refunds** | `nw_impact=refund` | Refund counted as income spend offset incorrectly |
| **Confirm before write** | Chat expense/income shows preview → user confirms → row in DB | Chat writes without confirm card |
| **Derived accounts** | CC/loan require `parent_account_id` → bank/cash; online wallet parent optional | CC created without parent |
| **Import dedupe** | Same fingerprint on **same account** skipped | Cross-account rows wrongly deduped |
| **Net worth** | Assets − liabilities (hybrid: bank/cash + manual assets − CC outstanding − manual loans) | Empty NW with data present |
| **credit_limit** | Stored on CC; **not** added to NW | Limit inflates NW |

---

## A — Auth and access (P0)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-A001** | Open `http://localhost:3000` logged out | Redirect to `/login` |
| **REG-A002** | Login with valid email `regression@local` | Lands on `/chat`; `finance_user` in localStorage |
| **REG-A003** | Login with invalid email (no `@`) | Client validation error; no API call |
| **REG-A004** | `POST /v1/login` `{ "email": "newuser@local" }` | 200; new user id returned |
| **REG-A005** | After REG-A004, `GET /v1/accounts` with same email header | Default **Cash Wallet** (`cash`) exists |
| **REG-A006** | API call without `X-User-Email` | Uses default `dev@local` or creates user (document actual behavior) |
| **REG-A007** | Logout from sidebar | Clears session; back to login |
| **REG-A008** | `GET /health` | 200 `status: ok` |

---

## B — Backend health and routing (P0)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-B001** | Frontend calls `/v1/accounts` via port 3000 | Proxied to API (not CORS error) |
| **REG-B002** | Open `http://localhost:8000/docs` | Swagger loads; all `/v1` routes listed |
| **REG-B003** | Chat page when API down | Offline banner with docker hint |
| **REG-B004** | Alembic at head on fresh DB | No migration errors in API logs on startup |

---

## C — Chat: confirm-before-write (P0)

Applies to **expense** and **income** mutations only.

| ID | Steps | Expected |
|----|-------|----------|
| **REG-C001** | Chat: `add 500 for Swiggy` | `status=confirm`, `ui_type=transaction_confirm`, `preview=true` |
| **REG-C002** | Same session: send `confirm` | `status=success`, `created_id` present; txn in ledger −500, `nw_impact=spending` |
| **REG-C003** | Chat: `add 300 for coffee` → send `cancel` | Message says cancelled; **no** new txn |
| **REG-C004** | Confirm synonyms: `yes`, `ok`, `save it` | Same as REG-C002 (one synonym per run) |
| **REG-C005** | Reject synonyms: `no`, `discard`, `never mind` | Same as REG-C003 |
| **REG-C006** | UI: Confirm/Cancel buttons on card | Sends `confirm` / `cancel` as next message |
| **REG-C007** | Chat: `salary 100000` or income phrase → confirm | Credit txn; `nw_impact=income` |
| **REG-C008** | Send `confirm` with no pending mutation | No accidental insert; normal planner response |
| **REG-C009** | After confirm, card shows committed state | `committed=true` or success message; buttons hidden |

---

## D — Chat: intents and cards (P1)

| ID | Message (examples) | Expected `ui_type` / notes |
|----|-------------------|----------------------------|
| **REG-D001** | `what is my net worth?` | `net_worth_breakdown`; numeric `net_worth` in data |
| **REG-D002** | `where did I spend this month?` | `spending_dashboard` |
| **REG-D003** | `spending last 12 months` | `spending_dashboard`; period respected |
| **REG-D004** | `can I afford 15000 EMI for a car?` | `affordability_result` |
| **REG-D005** | `list my accounts` | `account_list` |
| **REG-D006** | `recurring bills` / `subscriptions` | `recurring_bill_list` or `subscription_list` |
| **REG-D007** | `import statement` | `message_only`; points user to Transactions import |
| **REG-D008** | `tell me a joke` | `message_only`; `next_suggested_actions` present |
| **REG-D009** | `budget vs actual` | `message_only` or coming-soon (YNAB stub) |
| **REG-D010** | Category / cash flow / top expenses / vendor / anomaly phrases | Matching card type; **no 500** even with sparse data |
| **REG-D011** | `debt payoff` / `investment allocation` / `future balance` | Respective card; graceful empty state |
| **REG-D012** | `how are my investments?` | `investment_portfolio_dashboard` (smoke: `e2e/specs/smoke/chat-investments.spec.ts`) |
| **REG-D013** | `show my investment allocation` | `investment_pie_chart` |
| **REG-D014** | `did I pay my SIP this month?` | `sip_schedule_summary` |
| **REG-D015** | `when does my FD mature?` | `fd_maturity_summary` when FD/RD seeded; else `message_only` |
| **REG-D016** | `what's due this month?` | `obligation_list`; 4 sections; `total_monthly_commitments` > 0 |
| **REG-D017** | `loan emi summary` | `obligation_list`; `total_monthly_emi` reflects seeded loan |
| **REG-D018** | `can I afford a new loan?` | `affordability_result`; `commitments` breakdown with `loan_emis` and `sip_emis` |
| **REG-D019** | `add recurring bill Netflix 499` | `status=confirm`, `ui_type=recurring_bill_confirm`, `card_payload.name=Netflix` |
| **REG-D020** | Confirm the recurring bill | `status=success`, `committed=true`; bill appears in `GET /v1/recurring-bills` |
| **REG-D021** | `GET /v1/persona` first time | 200, `body=""`, no error |
| **REG-D022** | `PUT /v1/persona` then `GET` | Body persists; Settings editor shows saved text after reload |
| **REG-D023** | `record SIP 5000` → confirm | `status=confirm`, `transaction_confirm`, `legs` length 2; both txns in DB; SIP paid this month |

**E2E regression (Slice 1 chat + accounts setup):** `e2e/specs/regression/chat-investments.spec.ts` — **REG-C010** portfolio dashboard after MF, **REG-C011** SIP status, **REG-C012** allocation pie.

**E2E regression (Slice 2 obligations hub):** `e2e/specs/regression/chat-obligations.spec.ts` — **REG-C020** obligations card with SIP + loan, **REG-C021** recurring bill confirm flow, **REG-C022** persona settings round-trip.

**E2E regression (Slice 3 transfer):** `e2e/specs/regression/chat-transfer.spec.ts` — **REG-C030** dual-leg SIP transfer confirm.

**E2E regression (Slice 3.2–3.4):** `e2e/specs/regression/chat-slice3-ext.spec.ts` — **REG-C031** import guide, **REG-C032** explain transaction, **REG-C033** recategorize confirm, **REG-C034** create SIP account guided.

**LLM off (`LLM_PROVIDER=none`):** REG-D001–D022 must still route via keywords/semantic fallback (`test_planner_llm_none.py`).

---

## E — Chat sessions (P1)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-E001** | Send 2+ messages in chat | Session appears in sidebar list |
| **REG-E002** | Click prior session | Messages reload with `agent_response` JSON |
| **REG-E003** | Rename session | `PATCH /v1/chat/sessions/{id}` title updates |
| **REG-E004** | Delete session | 204; removed from list |
| **REG-E005** | New chat button | Fresh conversation id; machine reset |
| **REG-E006** | `POST /v1/chat` empty body | 422 |

---

## F — Accounts CRUD (P0)

### Primary accounts (bank, cash)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-F001** | Create bank: name, institution HDFC | 200; no `parent_account_id` |
| **REG-F002** | Create cash account | 200 |
| **REG-F003** | Create bank **with** `parent_account_id` | 400 |
| **REG-F004** | List accounts | Shows `transaction_count` per account |
| **REG-F005** | Edit bank name/institution | 200 |
| **REG-F006** | Delete bank with zero txns | 204 |
| **REG-F007** | Delete bank with txns | 409; UI delete disabled when count > 0 |
| **REG-F027** | Create bank with `opening_balance=50000` | 200; `balance=50000`; one txn `source=opening_balance`, `nw_impact=transfer` |
| **REG-F028** | Create cash with opening balance | Same as F027 |
| **REG-F029** | `opening_balance` on credit_card / online wallet / loan | 400 |
| **REG-F030** | Update bank `opening_balance` 50k → 75k | Balance 75k; opening txn updated (not duplicated) |
| **REG-F031** | Update bank `opening_balance=0` | Opening txn removed; balance 0 if no other txns |
| **REG-F032** | Net worth after bank + opening balance | `net_worth` includes opening balance |

### Derived accounts (credit_card, online wallet)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-F010** | Create CC **without** parent | 400: parent required |
| **REG-F011** | Create CC with parent = bank from REG-F001, `credit_limit` 800000 | 200 |
| **REG-F012** | UI: CC form without linked bank selected | Client error before submit |
| **REG-F013** | UI: no bank/cash exists yet | Hint: create bank/cash first |
| **REG-F014** | Create online wallet **without** parent, institution PhonePe | 200; `parent_account_id` null |
| **REG-F014b** | Create online wallet with optional parent bank | 200; see REG-F033–F035 |
| **REG-F015** | Parent = another CC | 400 |
| **REG-F016** | `credit_limit` on non-CC type | 400 |
| **REG-F017** | Negative `credit_limit` | 400 |
| **REG-F018** | Update CC: change limit, change linked bank | 200; validation enforced |
| **REG-F019** | Create loan **without** parent | 400: parent required |
| **REG-F023** | Create loan with parent, `sanctioned_amount`, `emi_amount`, `tenure_months` | 200; metrics fields populated |
| **REG-F024** | Loan `loan_type=other` without description | 400 |
| **REG-F025** | Loan disbursement + EMI on loan account | outstanding, amount_paid, emi counts correct |
| **REG-F026** | POST `/v1/liabilities` | 410 deprecated — use loan accounts |

### UI (`/accounts`)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-F020** | Add → save → appears in table | Name, type, institution visible |
| **REG-F021** | Edit inline/modal | Updates persist after refresh |
| **REG-F022** | CC row shows linked bank name | e.g. `linked to HDFC Savings` |
| **REG-F033** | UI type dropdown | Shows **"Online wallet"** (not "Wallet") |
| **REG-F034** | Create online wallet with optional parent bank, institution PhonePe | 200; `account_type=wallet`; linked parent shown when set |
| **REG-F035** | UI: online wallet card | Shows provider; linked bank when set; balance from txns |
| **REG-F036** | UI: bank form opening balance field | Create with `#acc-opening-balance`; card shows balance |
| **REG-F040** | Create mutual_fund **without** parent | 400: parent required |
| **REG-F041** | Create mutual_fund with parent + `opening_balance` | 200; balance from opening txn; `nw_impact=transfer` |
| **REG-F042** | Create fixed_deposit with start/tenure/rate + opening balance | 200; FD fields stored; balance on card |
| **REG-F043** | Bank details (IFSC) on mutual_fund | 400 |
| **REG-F044** | Net worth includes `investment_holdings` | Chat net worth ≥ MF opening balance |
| **REG-F045** | UI: investment type dropdown | MF, FD, RD, stock visible; parent required hint |
| **REG-F046** | Create CC with `due_day=15` | 200; card shows Statement due day 15 |
| **REG-F047** | Loan EMI + tenure without `start_date` | Client/API 400 |
| **REG-F048** | Loan with EMI + tenure + `start_date` | 200 |
| **REG-F049** | UI: investment card shows **Invested / Current / P&L** | MF/FD cards; not plain Balance |
| **REG-F060** | UI: investment P&L when current ≠ invested | Card shows profit % in green |
| **REG-F050** | UI: FD card shows maturity date | Computed from start + tenure |
| **REG-F051** | Create MF with `folio_number` | 200; card shows masked folio |
| **REG-F052** | Create stock with `demat_id` | 200; card shows masked demat |
| **REG-F053** | UI: accounts hero strip | Net worth, assets, liabilities visible in `#accounts-hero` |
| **REG-F054** | UI: grouped account layout | Bank under Cash & wallets; CC under Credit cards |
| **REG-F055** | UI: type optgroups + placement hint | Assets/Liabilities groups; hint updates on type change |
| **REG-F056** | Create CC with `initial_credit_used` + date | 200; `credit_used` matches; seed txn `source=initial_credit_used`, `nw_impact=spending` |
| **REG-F057** | Update CC with `opening_balance: null` in body | 200; no 500 (frontend edit regression) |
| **REG-F058** | Create EPF without parent + `opening_balance` + UAN | 200; balance seeded; no parent required |
| **REG-F059** | EPF rejects `demat_id`; accepts `folio_number` (UAN) | 400 / 200 |

---

## G — Transactions API (P0)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-G001** | `POST /v1/transactions` debit −500, today, valid account | 200; `nw_impact` auto-set (usually `spending`) |
| **REG-G002** | `POST` credit +50000 salary narration | `nw_impact=income` |
| **REG-G003** | `POST` amount 0 | 400 |
| **REG-G004** | `POST` future date | 400 |
| **REG-G005** | `POST` unknown `account_id` | 404 |
| **REG-G006** | `GET /v1/transactions?limit=10` | Includes `account_name`, `account_type`, `nw_impact` |
| **REG-G007** | `PUT` update merchant/category | 200; `nw_impact` recomputed |
| **REG-G008** | `DELETE` one txn | 204 |
| **REG-G009** | `POST /v1/transactions/bulk-delete` | `{ deleted, not_found }` correct |
| **REG-G010** | `POST /v1/transactions/delete-all` | All user txns gone |

---

## H — Transactions UI (`/transactions`) (P1)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-H001** | Page loads with txns | Table: date, merchant, amount, account, category |
| **REG-H002** | Filter: Spending (`nw_impact`) | Only spending rows |
| **REG-H003** | Filter: Income | Only income (+ refund if applicable) |
| **REG-H004** | Filter: account, category, date range, search | Results narrow correctly |
| **REG-H005** | Delete single row | Row removed |
| **REG-H006** | Bulk select + delete | Selected rows removed |
| **REG-H007** | Delete all (with confirm) | Empty ledger |
| **REG-H008** | Empty state | Prompt to import |

---

## I — Import: parse and review (P0)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-I001** | Upload `data/hdfc_12_months_sample.csv` on Transactions → Import | 200; rows with date, merchant, amount, **NW impact**, fingerprint |
| **REG-I002** | Upload minimal CSV (see tests) with `bank_hint=hdfc` | Parsed; salary → income suggestion; Swiggy → spending |
| **REG-I003** | Empty file | 400 |
| **REG-I004** | No accounts in DB, import without `account_id` | 400 create account first |
| **REG-I005** | Upload `.pdf` (text-based if available) | Rows or empty with no crash |
| **REG-I006** | Scanned PDF | Empty rows; UI message acceptable |

**Known blocker to verify:** `POST /v1/import` must not return 500 `NameError: parse_and_normalize`. If it does, mark REG-I001 **BLOCK** and file bug (`import_api.py` missing import).

---

## J — Import: confirm and dedupe (P0)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-J001** | Parse CSV → confirm selected rows | `inserted` ≥ 1; `errors` empty |
| **REG-J002** | Re-upload **same** CSV to **same** account | Rows marked duplicate; deselected in UI |
| **REG-J003** | Confirm only non-duplicate rows | Duplicates skipped |
| **REG-J004** | Same narration/amount to **different** account | **Not** duplicate |
| **REG-J005** | Delete imported txn → re-import same row | Can insert again (fingerprint cleared) |
| **REG-J006** | Delete all txns → re-import | Inserts succeed |
| **REG-J007** | CSV with EMI / BILLPAY / SIP rows | `suggested_nw_impact`: liability_payment / transfer |
| **REG-J008** | Confirm with `nw_impact` override in API body | Stored value respected (API-level test) |

---

## K — Transaction semantics (`nw_impact`) (P0)

Run via import, manual API, or unit tests (`tests/test_transaction_semantics.py`).

| ID | Input pattern | Expected `nw_impact` |
|----|---------------|----------------------|
| **REG-K001** | Rent / Swiggy / UPI purchase | `spending` |
| **REG-K002** | SALARY / salary credit | `income` |
| **REG-K003** | EMI / loan debit | `liability_payment` |
| **REG-K004** | BILLPAY-CREDIT CARD | `liability_payment` |
| **REG-K005** | SIP / mutual fund transfer | `transfer` |
| **REG-K006** | REFUND / reversal | `refund` |
| **REG-K007** | CC account: purchase (debit on CC) | `spending` |
| **REG-K008** | CC account: payment (credit on CC) | `liability_payment` |

---

## L — Spending analytics (P1)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-L001** | Seed: spending + EMI + SIP + salary | Chat spending total **excludes** EMI and SIP |
| **REG-L002** | `this_month` vs `last_12_months` | Different totals when data spans months |
| **REG-L003** | Frontend spending filter | Matches API `nw_impact=spending` only |
| **REG-L004** | Category breakdown | Sums match filtered txns (manual spot check) |

---

## M — Net worth (hybrid) (P0)

| ID | Setup | Expected |
|----|-------|----------|
| **REG-M001** | Salary +50k on bank | NW increases |
| **REG-M002** | CC spend −10k on derived CC | NW decreases; CC outstanding in breakdown |
| **REG-M003** | BILLPAY +10k on CC (liability_payment) | Outstanding decreases; **not** double-counted as spend |
| **REG-M004** | `POST /v1/assets` property 50L | NW includes manual asset |
| **REG-M005** | `POST /v1/liabilities` home_loan outstanding 20L | NW subtracts loan |
| **REG-M006** | Chat `net worth` after above | Card fields: `cash_and_primary`, `credit_card_outstanding`, `manual_assets`, `loan_liabilities` |
| **REG-M007** | CC `credit_limit` set | Does **not** increase NW |

---

## N — Assets API (P2, no UI)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-N001** | `POST /v1/assets` type `mf`, value > 0 | 200 |
| **REG-N002** | Invalid `asset_type` | 400 |
| **REG-N003** | `GET /v1/assets` | Lists user assets |

Types: `property` | `mf` | `stock` | `gold` | `other`

---

## O — Liabilities API (P2, no UI)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-O001** | `POST /v1/liabilities` home_loan, outstanding ≥ 0 | 200 |
| **REG-O002** | Optional `emi`, `interest_rate`, `due_day` 1–31 | Stored |
| **REG-O003** | Invalid type | 400 |
| **REG-O004** | Affordability chat uses liability EMI | Safe EMI reflects existing EMIs |

Types: `home_loan` | `personal_loan` | `cc` | `other`

---

## P — Recurring bills (P2, API + chat)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-P001** | `GET /v1/recurring-bills/suggestions` | 200 list (may be empty) |
| **REG-P002** | `POST /v1/recurring-bills` monthly rent −20000 | 200 |
| **REG-P003** | Missing `due_day` (monthly) | 400 |
| **REG-P004** | `POST .../confirm` with date | Creates txn `source=recurring` |
| **REG-P005** | Confirm same bill twice same month | 409 duplicate |
| **REG-P006** | Delete account with linked recurring bill | 409 |
| **REG-P007** | Chat `list recurring bills` | Card lists bills |

---

## Q — Affordability (P1)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-Q001** | No income data | Low/unknown income message; no crash |
| **REG-Q002** | 3 months salary + spending | `safe_emi_estimate` numeric; `risk_level` set |
| **REG-Q003** | Ask for EMI higher than safe | Warning / high risk in card |

---

## R — Recurring suggestions service (P2)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-R001** | Import 12-month HDFC sample | `GET /recurring-bills/suggestions` may propose patterns |
| **REG-R002** | Accept suggestion → create bill | Bill appears in list |

---

## S — Sidebar and navigation (P1)

**Automated:** `e2e/specs/regression/navigation-sidebar.spec.ts` (full desktop + mobile matrix).

| ID | Steps | Expected |
|----|-------|----------|
| **REG-S001** | Chat / Accounts / Transactions / Settings links | Each page loads |
| **REG-S002** | `/` | Redirects to `/chat` |
| **REG-S003** | `/import` | Redirects to `/transactions?import=1` |
| **REG-S004** | API docs link | Opens localhost:8000/docs |
| **REG-S005** | Settings nav link | `/settings` loads Appearance + Typography + Density sections |
| **REG-S006** | Select Midnight theme | `aria-pressed`, `html[data-theme="midnight"]`, persists reload |
| **REG-S007** | Select Compact density | `aria-pressed`, `html[data-density="compact"]`, persists reload |
| **REG-S008** | Cycle all theme packs | Each pack sets matching `html[data-theme]` and `localStorage fc_prefs` |
| **REG-S009** | User menu → Settings | Menu opens; Settings navigates to `/settings` |
| **REG-S010** | Theme default vs custom font | Default font follows theme; custom font persists across theme changes |
| **REG-S011** | Text size Large | `html[data-font-size="large"]`, persists reload |
| **REG-S012** | Settings → Open on phone | LAN URL input; QR + Copy link after valid network URL |

**Storage key:** `fc_prefs` in `localStorage` — `{ themePack, density, fontMode, fontFamily, fontSize }`. Defaults: `paper`, `comfortable`, `default`, `geist`, `medium`.

**Automated:** `e2e/specs/regression/navigation-sidebar.spec.ts` (S001–S006, A007), `e2e/specs/regression/settings-look-and-feel.spec.ts` (S007–S011).

---

## ML — Mobile layout and responsive panes (P1)

Breakpoint: **768px**. Below this width the app nav and chat session list are off-canvas drawers (closed by default). Desktop keeps both panes always visible.

| ID | Steps | Expected |
|----|-------|----------|
| **REG-ML001** | Load `/accounts` on mobile viewport | App nav closed; hero visible; no horizontal page overflow |
| **REG-ML002** | `#app-nav-toggle` + backdrop | Drawer opens and closes |
| **REG-ML003** | Navigate Chat → Accounts → Transactions via sidebar | Each page loads; drawer auto-closes after each link |
| **REG-ML004** | `#chat-sessions-toggle` on `/chat` | Sessions drawer opens/closes; New Chat closes drawer |
| **REG-ML005** | Log out from app nav on mobile | Session cleared; login page |
| **REG-ML006** | Visit `/` and `/import` | Redirect to `/chat` and `/transactions?import=1` |
| **REG-ML007** | Settings via mobile nav | `/settings` loads |
| **REG-ML008** | Compact density on mobile | `data-density="compact"` persists reload |

**Automated:** `e2e/specs/regression/mobile-layout.spec.ts` (`mobile-chrome` project only; ML001–ML008).

**E2E matrix:** All Playwright specs run on `desktop-chromium` and `mobile-chrome` projects. Helpers: `openAppNav`, `navigateViaSidebar`, `openChatSessions` in `e2e/fixtures/helpers.ts`.

---

## T — LLM provider modes (P1)

| ID | Env | Expected |
|----|-----|----------|
| **REG-T001** | `LLM_PROVIDER=none` | Chat works; keyword routing; no external API calls |
| **REG-T002** | OpenRouter configured | Richer planner; failures fall back gracefully |
| **REG-T003** | Invalid provider | App starts; chat returns safe fallback |

See [LLM_SETUP.md](./LLM_SETUP.md).

---

## U — UI cards render (P1)

For each `ui_type` in `CardRenderer.tsx`, trigger once and confirm **no React error boundary**, sensible empty state:

`transaction_confirm`, `spending_dashboard`, `net_worth_breakdown`, `affordability_result`, `message_only`, `account_list`, `recurring_bill_list`, `subscription_list`, `category_drilldown`, `cash_flow_summary`, `top_expenses_list`, `future_balance_projection`, `debt_payoff_plan`, `investment_pie_chart`, `vendor_history`, `anomaly_alert`, `monthly_summary`, `budget_comparison`.

| ID | Check |
|----|-------|
| **REG-U001** | All card types above render or fallback to message |
| **REG-U002** | Unknown `ui_type` from API | Falls back to `MessageOnlyCard` |

---

## V — Validation and error handling (P1)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-V001** | Invalid UUID in path | 400/404 as appropriate |
| **REG-V002** | Chat orchestrator internal error | 200 with `status=error` or message_only fallback, not 500 |
| **REG-V003** | Import confirm invalid account | 404 |
| **REG-V004** | XSS in merchant name | Escaped in UI (no script execution) |

---

## W — Multi-user isolation (P2)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-W001** | User A creates account | User B header does not see it |
| **REG-W002** | User A txns | Not visible to User B |

---

## X — Data integrity after mutations (P0)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-X001** | Chat confirm expense | Exactly one new txn; amount sign correct |
| **REG-X002** | Cancel after preview | Zero new txns |
| **REG-X003** | Import confirm count | `inserted` matches selected rows |
| **REG-X004** | Bulk delete | DB count matches UI |

---

## Y — YNAB / budget (P2, expected stub)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-Y001** | Chat budget vs actual | Coming soon / message_only; no fake numbers |

---

## Z — Zero-state and onboarding (P0)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-Z001** | Fresh user: net worth | Zero or empty breakdown; no crash |
| **REG-Z002** | Fresh user: spending dashboard | Empty chart/message |
| **REG-Z003** | Fresh user: import | Prompt to create account if none |
| **REG-Z004** | Fresh user: chat hints | Default chips visible (expense, net worth, spending, affordability) |
| **REG-Z005** | First bank → first CC → import | Full happy path end-to-end |

---

## End-to-end golden paths (run every release)

### Golden path 1 — New user ledger

1. REG-A002 → REG-F001 → REG-C001 → REG-C002 → REG-G006 verifies txn

### Golden path 2 — Credit card + semantics

1. REG-F001 → REG-F011 → REG-K007 spend on CC → REG-K008 BILLPAY → REG-M002 → REG-M003

### Golden path 3 — Import HDFC sample

1. REG-F001 → REG-I001 → REG-J001 → REG-J002 dedupe → REG-L001 spending check

### Golden path 4 — Chat analytics

1. Seed data → REG-D001 → REG-D002 → REG-D004

### Golden path 6 — Investment accounts

1. REG-F001 → REG-F040 (API reject) → REG-F041 → REG-F044 → REG-F042 (UI FD fields)

---

## Coverage map: pytest ↔ scenarios

| Test file | Scenarios partially covered |
|-----------|----------------------------|
| `test_health.py` | REG-A008, REG-B001 |
| `test_accounts_api.py` | REG-F001, F006, F010–F019, F023–F031, F029, F040–F043, F046–F048, F051–F052, loan metrics, opening balance |
| `test_transactions_api.py` | REG-G001, G006, G008–G010 |
| `test_chat_api.py` | REG-C001–C002, D001–D002, D008, E001–E004 |
| `test_import_api.py` | REG-I002, J001, J002, I003 |
| `test_transaction_semantics.py` | REG-K001–K008 (unit) |
| `test_net_worth.py` | REG-M001 (partial), REG-F032, REG-F044 |
| `test_spend_period.py` | REG-L002 (unit bounds) |
| `test_investment_account_details.py` | REG-F051–F052 (unit validation) |
| `test_account_grouping.py` | REG-F053–F055 (grouping math) |
| `apps/web/tests/unit/*.test.ts` | Theme prefs parse, account type visuals, chart colors (unit) |
| `apps/web/tests/integration/*.test.tsx` | ThemeProvider, Settings page, AccountTypeIcon, UserMenu |
| `e2e/specs/regression/accounts-opening-balance.spec.ts` | REG-F027, REG-F036 (UI) |
| `e2e/specs/regression/accounts-online-wallet.spec.ts` | REG-F033, REG-F034 |
| `e2e/specs/regression/accounts-credit-card.spec.ts` | REG-F001, REG-F011, REG-F012, REG-F046 |
| `e2e/specs/regression/accounts-investments.spec.ts` | REG-F041, REG-F042, REG-F045, REG-F049–F052, REG-F060 (UI) |
| `e2e/specs/regression/accounts-layout.spec.ts` | REG-F053–F055 (Assets/Liabilities layout) |
| `e2e/specs/regression/accounts-loan-start.spec.ts` | REG-F047, REG-F048 (UI) |
| `e2e/specs/regression/mobile-layout.spec.ts` | REG-ML001–REG-ML008 (mobile viewport) |
| `e2e/specs/regression/navigation-sidebar.spec.ts` | REG-S001–S006, REG-A007 |
| `e2e/specs/regression/accounts-epf.spec.ts` | REG-F058 (UI) |
| `e2e/specs/regression/settings-look-and-feel.spec.ts` | REG-S007–S012, REG-ML008 |
| `apps/web/tests/unit/mobileAccessUrl.test.ts` | LAN URL normalization (unit) |
| `apps/web/tests/integration/MobileAccessQr.test.tsx` | QR render, copy link, localhost manual URL |
| `test_chat_slice1.py` | REG-D012–D015, Slice 1 investment/SIP intents end-to-end |
| `test_planner_slice1.py` | Slice 1 keyword routing unit |
| `test_portfolio_summary.py` | Portfolio math, persona rules, footer suggestions |
| `test_chat_slice2.py` | REG-D016–D020 core paths |
| `test_planner_slice2.py` | Slice 2 keyword routing unit |
| `test_obligations_service.py` | `_bill_next_due` pure function, weekly formula |
| `test_planner_llm_none.py` | REG-D012–D015, REG-D016–D019 with `LLM_PROVIDER=none` |
| `test_persona_api.py` | REG-D021–D022 persona round-trip |
| `apps/web/tests/integration/InvestmentCards.test.tsx` | Slice 1 card components |
| `apps/web/tests/integration/ObligationCards.test.tsx` | ObligationListCard, RecurringBillConfirmCard |
| `apps/web/tests/integration/AffordabilityCardSlice2.test.tsx` | AffordabilityCard commitments section |
| `apps/web/tests/integration/SettingsPage.test.tsx` | FinancialPersonaEditor render, save, dirty state |
| `e2e/specs/regression/chat-investments.spec.ts` | REG-C010–C012 Slice 1 chat UI |
| `e2e/specs/regression/chat-obligations.spec.ts` | REG-C020–C022 Slice 2 chat UI |
| `test_chat_slice3.py` | REG-D023 record_transfer dual-leg confirm |
| `test_planner_slice3.py` | Slice 3 keyword routing unit |
| `test_transfer_propose.py` | Transfer validation unit |
| `test_persona_hook.py` | S2.6 post-session persona hook unit |
| `apps/web/tests/integration/TransactionConfirmCard.test.tsx` | Dual-leg transfer card render |
| `e2e/specs/regression/chat-transfer.spec.ts` | REG-C030 Slice 3 chat UI |
| `e2e/specs/regression/chat-slice3-ext.spec.ts` | REG-C031–C034 Slice 3.2–3.4 chat UI |
| `apps/api/tests/integration/test_chat_slice3_ext.py` | S3.2–3.4 backend integration |
| `apps/api/tests/integration/test_planner_llm_none.py` | Slice 3 LLM=none routing |
| `apps/api/tests/unit/test_planner_slice3.py` | S3 planner keyword detectors |
| `apps/web/tests/integration/Slice3Cards.test.tsx` | ImportGuideCard, TransactionDetailCard, AccountCreateConfirmCard Vitest |

**No automated tests yet:** REG-N*, REG-O*, REG-P*, REG-F010–F015, REG-C003–C009, REG-H*, REG-W*, some REG-F033–F036 UI-only.

---

## Known gaps (do not fail regression — document as SKIP/LIMITATION)

| Gap | Scenarios affected |
|-----|-------------------|
| No UI for assets / liabilities / recurring bills | REG-N*, REG-O*, REG-P* API-only |
| Import UI: no account picker (uses default/first) | REG-I001 note |
| Import UI: NW impact display-only (no edit) | REG-J008 UI skip |
| `budget_vs_actual` stub | REG-Y001 |
| Auth is email header only (no OAuth) | REG-W* limited |
| PDF scanned statements | REG-I006 |
| Exact LLM phrasing | All chat scenarios |

Track fixes in [DRIFT_AUDIT.md](./DRIFT_AUDIT.md).

---

## Suggested execution order (agent)

1. `pytest tests/ -q`
2. P0 API: REG-A*, F*, G*, I*, J*, K*, C*, M*, X*, Z*
3. P0 UI: F020–F022, C006, H001, I001, J002, S*, ML*
4. P1: D*, E*, H*, L*, Q*, T*, U*
5. P2: N*, O*, P*, R*, W*, Y*

Total scenarios: **~120** IDs above. Expand by splitting variants (periods, account types) as needed.

---

## Report template

```markdown
# Regression run — YYYY-MM-DD

**Commit/branch:** …
**Environment:** docker compose / local
**Tester:** agent|human

## Summary
- PASS: n
- FAIL: n
- BLOCK: n
- SKIP: n

## Failures
- REG-…: …

## Blockers
- REG-…: …

## Notes
- …
```
