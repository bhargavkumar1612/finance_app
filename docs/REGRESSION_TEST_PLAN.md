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
| **Derived accounts** | CC/wallet require `parent_account_id` → bank/cash | CC created without parent |
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

**LLM off (`LLM_PROVIDER=none`):** REG-D001–D011 must still route via keywords/semantic fallback.

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

### Derived accounts (credit_card, wallet)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-F010** | Create CC **without** parent | 400: parent required |
| **REG-F011** | Create CC with parent = bank from REG-F001, `credit_limit` 800000 | 200 |
| **REG-F012** | UI: CC form without linked bank selected | Client error before submit |
| **REG-F013** | UI: no bank/cash exists yet | Hint: create bank/cash first |
| **REG-F014** | Create wallet with parent bank | 200 |
| **REG-F015** | Parent = another CC | 400 |
| **REG-F016** | `credit_limit` on non-CC type | 400 |
| **REG-F017** | Negative `credit_limit` | 400 |
| **REG-F018** | Update CC: change limit, change linked bank | 200; validation enforced |

### UI (`/accounts`)

| ID | Steps | Expected |
|----|-------|----------|
| **REG-F020** | Add → save → appears in table | Name, type, institution visible |
| **REG-F021** | Edit inline/modal | Updates persist after refresh |
| **REG-F022** | CC row shows linked bank name | e.g. `linked to HDFC Savings` |

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

| ID | Steps | Expected |
|----|-------|----------|
| **REG-S001** | Chat / Accounts / Transactions links | Each page loads |
| **REG-S002** | `/` | Redirects to `/chat` |
| **REG-S003** | `/import` | Redirects to `/transactions?import=1` |
| **REG-S004** | API docs link | Opens localhost:8000/docs |

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

---

## Coverage map: pytest ↔ scenarios

| Test file | Scenarios partially covered |
|-----------|----------------------------|
| `test_health.py` | REG-A008, REG-B001 |
| `test_accounts_api.py` | REG-F001, F006, F016–F017; **missing** parent_account_id (F010–F015) |
| `test_transactions_api.py` | REG-G001, G006, G008–G010 |
| `test_chat_api.py` | REG-C001–C002, D001–D002, D008, E001–E004 |
| `test_import_api.py` | REG-I002, J001, J002, I003 |
| `test_transaction_semantics.py` | REG-K001–K008 (unit) |
| `test_net_worth.py` | REG-M001 (partial) |
| `test_spend_period.py` | REG-L002 (unit bounds) |
| `test_llm_client.py` | REG-T001–T003 (unit) |

**No automated tests yet:** REG-N*, REG-O*, REG-P*, REG-F010–F015, REG-C003–C009, REG-H*, REG-W*, frontend E2E.

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
3. P0 UI: F020–F022, C006, H001, I001, J002, S*
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
