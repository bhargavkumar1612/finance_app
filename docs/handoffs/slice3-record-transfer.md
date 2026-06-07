# Handoff — 2026-06-07 — Slice 3: Capture & Onboarding ✅ DONE

## Summary

**Slice 3 is complete.** All four S3 features are implemented, tested, and green across unit, integration, smoke, Vitest, and e2e layers.

| ID | Feature | Status |
|----|---------|--------|
| S3.1 | `record_transfer` — dual-leg SIP confirm | ✅ Done |
| S3.2 | `import_statement` → `import_guide` card with action link | ✅ Done |
| S3.3 | `create_account_guided` — SIP/EPF confirm-before-write | ✅ Done |
| S3.4 | `explain_transaction` + `recategorize_transaction` with confirm | ✅ Done |

Also closed from prior sessions:

- **S2.6** — Post-session persona hook (`persona_hook.py`) wired in orchestrator
- **Atomic rollback test** — `test_insert_transfer_atomic_rollback_on_bad_account`

---

## New intents & card types

| Intent | Card type | Action |
|--------|-----------|--------|
| `record_transfer` | `transaction_confirm` (legs[]) | `propose_transfer` / `insert_transfer` |
| `import_statement` | `import_guide` | — (no ledger action; directs to /import) |
| `create_account_guided` | `account_create_confirm` | `propose_account` / `insert_account` |
| `explain_transaction` | `transaction_detail` | `explain_transaction` |
| `recategorize_transaction` | `transaction_confirm` | `propose_recategorize` / `insert_recategorize` |

---

## New files

| File | Purpose |
|------|---------|
| `apps/api/app/services/persona_hook.py` | Post-session persona enrichment (S2.6) |
| `apps/web/components/cards/ImportGuideCard.tsx` | S3.2 import guide card |
| `apps/web/components/cards/TransactionDetailCard.tsx` | S3.4 explain card |
| `apps/web/components/cards/AccountCreateConfirmCard.tsx` | S3.3 account confirm card |
| `apps/api/tests/integration/test_chat_slice3_ext.py` | S3.2–3.4 integration tests |
| `apps/api/tests/smoke/test_chat_slice3.py` | Extended smoke (all S3 intents) |
| `apps/web/tests/integration/Slice3Cards.test.tsx` | Vitest for 3 new cards |
| `e2e/specs/regression/chat-slice3-ext.spec.ts` | REG-C031–C034 e2e |

---

## Modified files (key changes)

| File | Change |
|------|--------|
| `apps/api/app/core/schemas.py` | +`explain_transaction`, `recategorize_transaction`, `create_account_guided` intents; +`import_guide`, `transaction_detail`, `account_create_confirm` card types |
| `apps/api/app/core/pending_mutation.py` | +`insert_account`, `insert_recategorize` to `MUTATION_ACTIONS`; propose/commit mappings |
| `apps/api/app/agents/ledger_agent.py` | +`_propose_account`, `_insert_account`, `_explain_transaction`, `_propose_recategorize`, `_insert_recategorize`, `_auto_resolve_parent` |
| `apps/api/app/agents/planner.py` | +4 keyword detectors; S3 detectors ordered before `_detect_spending_period` to avoid false matches |
| `apps/api/app/agents/ui_guide.py` | +routing for `import_statement`, `explain_transaction`, `recategorize_transaction`, `create_account_guided` |
| `apps/api/app/core/orchestrator.py` | +`_NEXT_ACTIONS` entries; +`name`, `transaction_id`, `new_category`, etc. to param merge keys |
| `apps/web/components/cards/CardRenderer.tsx` | +`import_guide`, `transaction_detail`, `account_create_confirm` registrations |
| `e2e/specs/regression/chat-obligations.spec.ts` | Fixed `#acc-loan-start` field ID + `.first()` strict-mode fixes |

---

## Test results (all green)

```
Unit:        149 passed
Smoke:        13 passed
Integration:  21 passed (test_chat_slice3_ext + test_planner_llm_none)
Vitest:       57 passed (12 test files)
E2E:          13 passed (REG-C001–C003, C010–C012, C020–C022, C030–C034)
```

---

## Planner keyword ordering (important invariant)

Detectors run in this order (most-specific first):

1. `_detect_explain_transaction` — "explain this charge", "what did I spend at X"
2. `_detect_recategorize_transaction` — "recategorize", "change category"
3. `_detect_spending_period` — "spend/spent/spending" (broad — must be after above)
4. `_detect_create_account_guided` — "add SIP account", "create MF"
5. `_detect_record_transfer` — "record SIP", "transfer to MF"
6. `_detect_create_recurring_bill` — "add recurring bill"
7. `_detect_add_expense` — "add expense", "add 500 for X"
8. `_detect_net_worth`
9. `_slice1_keyword_route`
10. `_slice2_keyword_route`
11. `_slice3_keyword_route` (import_statement only)

**Do NOT** move spending detection before explain/recategorize — "what did I spend at X" contains "spend" and will misroute.

---

## Deferred (stretch goals)

- `transfer_group_id` on transactions (link both legs in DB)
- Edit amount/date on confirm card before commit
- Explicit atomic-rollback integration test with mock failure on 2nd insert (unit test covers it)
- E2E asserting SIP paid status after REG-C030 confirm
- E2E for persona hook side-effect (chat → persona body/traits updated)
