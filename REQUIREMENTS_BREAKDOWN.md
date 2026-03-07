# Finance Copilot — Requirements Breakdown

**Summary:** AI-powered personal finance chat (India-focused) with guided UI. Manages assets, liabilities, income, spending. Import-first (CSV + PDF + PhonePe), deterministic ledger, planner–executor multi-agent architecture.

---

## 1. Requirements Summary

| Area | Decision |
|------|----------|
| **Product** | Personal finance copilot (single user, extensible) |
| **Scope** | Assets, liabilities, income, expenses + derived metrics |
| **Region** | India (UPI, FY, Section 80C, etc. later) |
| **Import** | Bank CSV/PDF + PhonePe CSV; manual entry secondary |
| **Platform** | Web only |
| **Architecture** | 4 layers: UI → Orchestrator → Agents → Tools/DB |
| **Orchestration** | Planner–Executor (not router, not swarm) |
| **Agents** | Planner, Ledger (deterministic), Insight, UI Guide |
| **Backend** | FastAPI, PostgreSQL, Redis, Celery |
| **Frontend** | React/Next, XState, dynamic card renderer |
| **Rule** | Math and ledger truth live outside the LLM |

---

## 2. Task Breakdown

### Phase 0 — Foundation (Days 1–3)

| # | Task | Notes |
|---|------|--------|
| 0.1 | **DB schema** — users, accounts, transactions, assets, liabilities | Debit = negative, credit = positive; `source`, `confidence` on transactions |
| 0.2 | **Project layout** — FastAPI app with `/agents`, `/services`, `/db`, `/api`, `/core` | Add `/ingestion` with csv_parsers, pdf_parsers, normalizer, deduper |
| 0.3 | **Core data contracts** — Planner output schema, Agent response schema, normalized transaction schema | Strict JSON schemas; no free-form agent → UI |
| 0.4 | **Manual expense entry API** — create transaction (amount, date, category, merchant) with validation | No LLM; pure CRUD + validation |
| 0.5 | **Basic chat API** — single endpoint: user message → placeholder/echo response | Prep for orchestrator |

### Phase 1 — Orchestration & Ledger (Days 4–9)

| # | Task | Notes |
|---|------|--------|
| 1.1 | **Orchestrator** — receives message, calls Planner, routes to Ledger/Insight, returns structured response | State in Redis (conversation_id, current_step, filled_slots) |
| 1.2 | **Planner agent** — intent classification (add_expense, import_statement, net_worth_query, spending_analysis, affordability_check) + step list | Output: intent, steps[], ui_mode |
| 1.3 | **Ledger agent (tools)** — insert_transaction, fetch_transactions, compute_net_worth, compute_monthly_spend, detect_duplicates | Deterministic; no creative math |
| 1.4 | **Redis state manager** — store/load conversation state, filled_slots, agent_history | TTL and key design for sessions |
| 1.5 | **Structured API response** — status, data, confidence, next_suggested_actions | Same shape for all agent-driven responses |

### Phase 2 — Ingestion Pipeline (Days 4–14, can overlap with Phase 1)

| # | Task | Notes |
|---|------|--------|
| 2.1 | **Normalized transaction model** — single schema for all parsers (amount, date, merchant, raw_description, reference, confidence) | All ingestion paths merge here |
| 2.2 | **CSV router + one bank parser** — e.g. HDFC: column mapping, DR/CR, Indian number format | Bank detection or user-selected bank |
| 2.3 | **Normalizer** — sign normalization, date parsing, currency, Indian number formats (1,23,456.00, parentheses) | Shared by CSV and PDF |
| 2.4 | **Duplicate detection** — fingerprint = hash(date\|amount\|normalized_merchant\|account_id); store and reject | Optional: UPI txn_id in fingerprint for PhonePe |
| 2.5 | **PDF pipeline** — is_scanned check → pdfplumber (or OCR fallback), table extraction, bank-specific parser | Start with one bank (e.g. HDFC) |
| 2.6 | **Bank detection** — keyword signatures (HDFC, ICICI, SBI, Axis) on first page / header | Chooses which parser to use |
| 2.7 | **Import API** — upload file (CSV/PDF), return list of normalized transactions + duplicates flagged | No auto-insert; review first |
| 2.8 | **PhonePe parser** — column mapping, intent classifier (expense / income / transfer / refund / cashback / wallet_load) | Transfers excluded from spend analytics |
| 2.9 | **PhonePe deduplication** — fingerprint with UPI txn_id when available; avoid double-count with bank import | |

### Phase 3 — Guided UI & Chat (Days 7–14)

| # | Task | Notes |
|---|------|--------|
| 3.1 | **Frontend app** — React or Next.js, routing, layout | |
| 3.2 | **Conversation state machine (XState)** — states: chat, form, selection, confirmation, result | Transitions driven by API response |
| 3.3 | **Dynamic card registry** — map ui_type to component (transaction_confirm, monthly_summary, net_worth_breakdown, affordability_result, selection_card) | |
| 3.4 | **Transaction confirmation card** — show amount, merchant, category; accept/edit/reject | When confidence < threshold |
| 3.5 | **Chat UI** — send message, stream or show structured response + suggested actions | |
| 3.6 | **UI Guide agent** — turns Ledger/Insight output into ui_type + payload + chat_summary + next_suggested_actions | |
| 3.7 | **Guided review screen (import)** — list of parsed transactions; high/medium/low confidence; bulk accept, edit, reject | |

### Phase 4 — Insights & Affordability (Days 10–21)

| # | Task | Notes |
|---|------|--------|
| 4.1 | **Insight agent** — spending patterns, top categories, month-over-month, anomaly hints | Uses Ledger tools for data; LLM for narrative |
| 4.2 | **Monthly summary card** — total spent, top category, savings vs income | |
| 4.3 | **Net worth flow** — fetch assets/liabilities, compute (deterministic), return breakdown card | |
| 4.4 | **Affordability engine** — safe EMI from income/expenses, debt ratio, risk level | Formula tuned for India; no LLM for the number |
| 4.5 | **Affordability result card** — safe EMI, risk level, short recommendation | |
| 4.6 | **Missing data detection** — e.g. “rent not added”, “salary not updated”; UI Guide prompts | Can be rule-based first |

### Phase 5 — Hardening & India (Week 4+)

| # | Task | Notes |
|---|------|--------|
| 5.1 | **Validation guardrails** — no negative income, EMI vs outstanding, expense date rules, currency normalization | |
| 5.2 | **Confidence thresholds** — below threshold → confirm before store; never silent low-confidence write | |
| 5.3 | **Observability** — agent calls, tool latency, token cost, correction rate | |
| 5.4 | **India Phase 2** — UPI detection, EMI auto-detect, CC billing cycles, FY (Apr–Mar), 80C, SIP recognition | |
| 5.5 | **Categorization service** — rule-based + optional LLM for merchant → category only (not amount/date) | |
| 5.6 | **Celery** — background jobs for heavy projections or batch import | Optional for MVP |

---

## 3. Clarifying Questions

### Product & scope

1. **Multi-currency?** — Only INR for MVP or support USD/others from day one?
2. **Accounts vs transactions** — One “account” per bank account/card; do you want multiple accounts per user from MVP (e.g. 2 banks + 1 CC)?
3. **Income model** — Is income only “recurring source” (salary, rental) or also one-off (bonus, refund)? Doc says both; confirm priority.
4. **Expenses vs transactions** — Doc uses “transactions” (debit/credit) as the heart. Should “expenses” be a view (debits only) or a separate entity? Assumption: transactions with amount < 0 = expenses for analytics.

### Import & banks

5. **Which banks first?** — HDFC, ICICI, SBI, Axis mentioned. Which one do you use? Start with that one.
6. **PhonePe export format** — Do you have a sample PhonePe CSV (column names and 2–3 rows) to lock the parser contract?
7. **PDF vs CSV priority** — Build CSV for one bank first, then PDF for same bank, or CSV for 2 banks then PDF?
8. **Import → account** — On import, does user select “which account” (e.g. HDFC Savings) or do we create account from file?

### AI & orchestration

9. **LLM provider** — OpenAI, Anthropic, local, or India-hosted? Affects tool-calling and latency.
10. **Planner implementation** — Pure LLM with strict output schema, or rule-based router for MVP (e.g. keywords → intent) and LLM later?
11. **Conversation memory** — How much history to send to Planner (last N turns vs full thread)? Affects cost and context.

### UX & guided UI

12. **First flow** — Which single flow do you want working end-to-end first: “Add expense via chat”, “Net worth”, or “Import CSV + review”?
13. **Auth** — Login/signup in scope for MVP or assume single user / dev-only?
14. **Mobile-responsive** — Web-only but must work on mobile browsers, or desktop-first?

### Compliance & risk

15. **Data residency** — Any requirement to keep DB/Redis in India?
16. **Audit trail** — Do you need immutable log of “who changed what” (e.g. for corrections)?

---

## 4. Ideas & Considerations

### Architecture

- **LangGraph vs custom orchestrator** — Doc mentions both. Start with a simple custom loop (Planner → Ledger/Insight → UI Guide); introduce LangGraph when you need cycles/conditional edges.
- **Single “Executor” vs direct Planner → Agent** — You can have Planner output “call Ledger with tool X” and have one Executor service that invokes the right agent and tools. Keeps orchestration in one place.
- **Direct Skill Prompting (Arch Decision)** — Avoid native LLM `tools=` APIs (especially for local/open-weight models like deepseek-r1). Instead, inject tool JSON schemas directly into the System Prompt.
- **Conversational vs. Skill Routing** — Instruct the LLM to return `{"tool": "name", "parameters": {...}}` for actions or `{"message": "..."}` for chatting. The framework intercepts the JSON and executes appropriately.
- **Framework Execution** — The LLM decides the routing intent, but the backend Python framework actually executes the database transactions and ledger queries safely.
- **API versioning** — Use `/v1/chat`, `/v1/import` from day one so response shapes can evolve.

### Data & ingestion

- **Idempotent import** — Same file uploaded twice should not create duplicates (fingerprint + “already imported” response).
- **Raw blob storage** — Store original CSV/PDF (e.g. S3 or filesystem) with reference in DB for re-runs and support.
- **Category taxonomy** — Fix a small list (food, rent, travel, emi, utilities, shopping, health, other) and map bank categories to it in normalizer.

### Guided UI

- **Slots for multi-turn** — e.g. “Add expense” needs amount, date, category, merchant; collect missing slots via UI Guide and confirmation cards instead of one long form.
- **Off-ramp to manual** — “Can’t parse this—add manually” with a prefilled form when possible.
- **Progress indicator** — For import, show “Parsing → Normalizing → Checking duplicates → Ready for review”.

### India-specific

- **Lakh/Crore** — Accept “15L” in chat and normalize to 15,00,000 in backend.
- **GST in receipts** — Later: optional field for business users; not needed for personal MVP.
- **TDS / Form 16** — Later: link income to TDS for tax view.

### Security & performance

- **Rate limit** — Per user on chat and import to avoid abuse and cost spikes.
- **PII** — Merchant names and descriptions are sensitive; consider encryption at rest and access control early.
- **Token budget** — Max tokens per request for Planner + Ledger so one run doesn’t blow the budget.

### Testing

- **Golden files** — Keep sample CSV/PDF (anonymized) in repo for regression tests for parsers and normalizer.
- **Deterministic tests** — Net worth, affordability, monthly spend: unit tests with fixed DB state, no LLM.

---

## 5. Suggested First Sprint (Next 7 Days)

If starting from zero, a practical order:

1. **Day 1–2:** DB schema (PostgreSQL), migrations, basic FastAPI app and project layout.
2. **Day 3:** Manual “add transaction” API + validation; simple in-memory or DB list for testing.
3. **Day 4:** One CSV parser (e.g. HDFC) → normalizer → duplicate check → in-memory or DB “staging” table; no Ledger insert yet.
4. **Day 5:** Orchestrator stub: receive message, call Planner (can be rule-based: “add expense” → Ledger add), return `{ status, data, next_suggested_actions }`.
5. **Day 6:** Ledger agent with tools: insert_transaction, fetch_transactions, compute_net_worth (from assets/liabilities or placeholder).
6. **Day 7:** Minimal chat UI (React/Next): input box, send to `/v1/chat`, display response text + one confirmation card (e.g. transaction_confirm) when intent is add_expense.

This gives you: one end-to-end flow (add expense via chat), one import path (CSV) to staging, and a clear place to add UI Guide and more intents next.

---

## 6. Doc References (from init.md)

- Architecture: 4 layers, Planner–Executor, 4 agents (Planner, Ledger, Insight, UI Guide).
- Domain: users, accounts, transactions (debit negative), assets, liabilities; derived metrics computed, not stored.
- Guardrails: math outside LLM, strong validation, confidence thresholds.
- Ingestion: unified pipeline; CSV + PDF (pdfplumber → OCR); PhonePe with intent classifier; deduplication and guided review.
- Build order: ledger + add expense + basic chat → assets/liabilities + net worth + Redis → insights + guided cards → affordability + polish.

Use this doc to track tasks (e.g. in a board or checklist), answer the questions above, and then refine the first sprint into tickets.
