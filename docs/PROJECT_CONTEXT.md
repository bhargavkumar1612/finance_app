# Project context — Finance Copilot

Owner priorities, mental model, and non-goals. Complements [DOMAIN_GLOSSARY.md](./DOMAIN_GLOSSARY.md) (terms) and [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) (architecture).

**Maintained by:** [domain-interview](../.cursor/skills/domain-interview/SKILL.md) sessions.

**Onboarding status:** Rounds 1–7 complete; **Round 8 (2026-06-07)** — AI chat features (portfolio dashboard, SIP, obligations, persona).

---

## Product mental model

**Audience:** Multi-user — per-user data and isolation; not a single-user-only toy app.

**Core loop:** Deterministic orchestrator, typed responses, Ledger for facts and writes, LLM for language/routing only, confirm before mutating money.

**Financial lens:** Net worth is the anchor. **Spending** means what reduces net worth; liability payments and transfers are not spending. Primary accounts (bank, cash) fund derived accounts (credit cards, wallets, **loans**).

**Derived liability accounts:** Credit cards owe only when used; loans owe from disbursement. Both link to a parent bank account.

---

## Priorities

All three pillars are **heavily used** and must be **high quality** — no "good enough for MVP" split between them.

| Pillar | What "perfect" means (owner intent) |
|--------|-------------------------------------|
| **Tracking** | Reliable imports, transactions, categories, account model (primary + derived) |
| **Planning** | Recurring bills, affordability, loan/CC EMI visibility, budget vs actual; later full YNAB-style envelopes |
| **Copilot chat** | Natural language over accurate ledger data — numbers from tools, not the model |

---

## Roadmap (owner-confirmed)

| Phase | Scope |
|-------|--------|
| **Now (Phase 1)** | Derived loan accounts, Liability merge, loan dashboard metrics, glossary alignment |
| **Phase 2 (in progress)** | Liquid investment account types (MF, FD, RD, stock) — see [INVESTMENT_ACCOUNTS_PLAN.md](./INVESTMENT_ACCOUNTS_PLAN.md) |
| **Phase 2.1 (done)** | Round 5 drift closure — Holdings label, FD card, loan start, CC due day, cash UI |
| **Phase 2.2 (done)** | Investment reference IDs — `folio_number`, `demat_id` |
| **Phase 2.3 (done)** | MF one-time vs SIP; invested/current/P&L |
| **Phase 3 — AI chat (next)** | [AI_CHAT_FEATURES_PRD.md](./AI_CHAT_FEATURES_PRD.md) — Slice 1 investment/SIP chat first |
| **Later** | YNAB-style envelope budgeting (assign income to categories; spend from envelopes) |

---

## Phase 2.3 — Deferred (not in scope for this delivery)

| Item | Status | Notes |
|------|--------|-------|
| CC `due_day` → RecurringBill reminder | Deferred | Obligations hub in chat shows due_day; auto RecurringBill link later |
| Physical Asset UI | Deferred | `Asset` table CRUD for property, gold, etc.; included in portfolio dashboard when rows exist |
| Legacy `/v1/assets` migration | Deferred | Move mf/stock rows to Account types; chat allocation must use Account holdings |
| FD maturity value projection | Deferred | Maturity **date** in chat; projected value formula TBD |
| Chit fund modeling | Deferred | Phase 2 interview |

---

## AI copilot chat (Round 8 — owner confirmed)

**PRD:** [AI_CHAT_FEATURES_PRD.md](./AI_CHAT_FEATURES_PRD.md)

**Implementation order:** Slice 1 (investment/SIP chat) → Slice 2 (obligations hub) → Slice 3 (capture/import). **Financial persona** spans Slices 1–2 (footer suggestions, nudge copy, drill-down filtering).

| Decision | Rule |
|----------|------|
| Portfolio scope | Cash (bank/wallet) + Account holdings + physical `Asset` rows |
| Portfolio UX | Primary visual dashboard + persona-filtered drill-downs; footer suggestions for gaps |
| Rankings | Liquidity stack (glossary); valuable by **current value**; profitable by **P&L % and ₹** |
| Advice | Facts only + NW-increasing suggestions; **no** buy/sell picks |
| SIP status | Last paid, next expected, or **Already paid in {Month}** |
| Record SIP | **Dual-leg** bank debit + MF credit in one confirm |
| Affordability | Subtract **all** commitments (loans, SIPs, recurring bills, CC) |
| Obligations | **One card**, grouped sections (SIP / EMI / bills / CC) |
| Proactive nudges | Chat + Accounts; persona-aware copy |
| Persona | DB-stored; rules + LLM after session; user editable in Settings — [002-financial-persona.md](./decisions/002-financial-persona.md) |

---

## Phase 2 — Investment and physical assets

**Status:** Liquid investment **Account** types implemented (2026-06-06). Physical assets and chit remain deferred.

**Hybrid model** (owner agreed):

| Type | Model | Parent bank | Net worth |
|------|-------|-------------|-----------|
| mutual_fund, sip | Account (derived) | required | transfer from bank; value from txns / opening balance |
| fixed_deposit, recurring_deposit | Account (derived) | required | transfer; FD/RD planning fields on Account |
| stock | Account (derived) | required | transfer |
| gold (paper/ETF) | Account (derived) | required | transfer (not built yet) |
| property, vehicle, physical gold | Asset | n/a | manual `current_value` + `valuation_date` |
| chit | TBD | TBD | interview before build |

**Liquid investments:** derived Account types with transactions (`nw_impact=transfer` from bank).

**Illiquid physical:** extend Asset table with richer types and optional description; no txn ledger required for MVP.

---

## Non-goals

Explicitly **not** building:

- Tax filing
- Stock trading
- Shared family budgets (multi-user ≠ shared household view)
- Bank sync API (live bank connections)

**In scope later (not a non-goal):** YNAB-style envelope budgeting — see [Envelope budgeting (YNAB-style)](./DOMAIN_GLOSSARY.md) in glossary.

---

## Preferences

### Documentation vs code language

- Glossary terms in `DOMAIN_GLOSSARY.md` are canonical for naming in new code and UI.
- Do not duplicate architecture rules here — see `AI_PRINCIPLES.md`.
- When code drift is noted in the glossary (e.g. spending sum), fix code in a focused change — do not silently change the glossary to match wrong code.

### Interview cadence

- **Onboarding** round 1 done.
- **Feature deep-dives** before major work.
- **Audit** when drift is noticed between glossary, UI, and ledger math.
- **Round 5 (2026-06-06):** Account field model — see glossary entries for holdings label, FD/RD card, loan start date, CC due day, folio/demat, cash UI.
- **Round 6 (2026-06-06):** CC **initial credit used** + as-of date on add/edit; seed txn with `nw_impact=spending` (counts in spend reports).
- **Round 7 (2026-06-07):** Look and feel — theme packs, Lucide icons, Settings page, density toggle.
- **Round 8 (2026-06-07):** AI chat — portfolio dashboard, SIP status, obligations hub, persona; see [AI_CHAT_FEATURES_PRD.md](./AI_CHAT_FEATURES_PRD.md).

---

## Look and feel (Round 7 — owner confirmed)

| Decision | Rule |
|----------|------|
| Default theme | **Paper** (light) |
| Theme packs | Full palettes: paper, midnight, coral, slate |
| Icons | **Lucide React** everywhere — no emoji for nav, accounts, or cards |
| Account visuals | Fixed color + icon per account type |
| Money colors | Green = asset/NW up; red = liability; blue = neutral |
| Aesthetic | CRED + Jupiter energy, content-first, high legibility, mobile + web |
| Settings | Sidebar nav + `/settings` page; theme + density controls |
| User menu | Signed-in block opens menu with Settings + Log out |
| Persistence | `localStorage` per device (no server sync yet) |

**Reference apps:** CRED, Jupiter — bold but readable, not flashy.

---

## Account fields (Round 5 — owner confirmed)

| Decision | Rule |
|----------|------|
| Investment card label | **Invested / Current / P&L** (not Balance; deprecated: “Holdings ₹X”) |
| FD/RD card | Show start, tenure, rate + **computed maturity date** |
| Loan start date | **Required** when EMI + tenure are set |
| CC due day | Save on Account; link to recurring-bill reminders later |
| Investment refs | `folio_number` (MF, RD); `demat_id` (stock) — optional, reference only |
| Cash form | Hide institution field |
| Opening balance | bank + cash + investments |

**Implementation:** See field audit plan — migration needed for `folio_number`, `demat_id`; API must allow `due_day` on `credit_card` (today cleared for non-loan types).

---

## Open questions

| Topic | Status |
|-------|--------|
| Variable EMI / amortization from interest rate | Phase 1 uses user-entered `emi_amount`; calculator deferred |
| Bank EMI import → auto-mirror to loan account | Manual loan-account txn for now; `linked_account_id` on Transaction TBD |
| CC due day → recurring bill auto-link | Obligations hub shows due_day; auto RecurringBill deferred |
| CC due_day on credit_card in API clear rules | Code drift — `_clear_incompatible_fields` clears due_day for non-loan today |
| Persona LLM update frequency | After each chat session (Round 8); batch digest TBD |
| CC “commitment” amount for affordability | Minimum vs full statement — use outstanding or user-set recurring when no min tracked |
