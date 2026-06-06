# AI application guidelines — Finance Copilot

Principles for building and extending this app. Follow them for new features, refactors, and reviews.

**Related:** [LLM setup](./LLM_SETUP.md) · [Phase 1 plan](./PHASE1_PLAN.md) · Cursor rules in [`.cursor/rules/`](../.cursor/rules/)

---

## 1. Layered architecture

Use four layers. Do not mix responsibilities across them.

```
UI (guided experience)
  ↓
Orchestrator
  ↓
Specialized agents (Planner, Ledger, Insight, UI Guide)
  ↓
Tools / APIs / DB
```

| Layer | Location | Responsibility |
|-------|----------|----------------|
| UI | `frontend/`, `chatMachine.ts` | Render typed cards; state machine for flows |
| Orchestrator | `app/core/orchestrator.py` | Load/save state, run plan → agents → `AgentResponse` |
| Agents | `app/agents/` | Intent, DB tools, narratives, UI hints |
| Tools/DB | `app/api/`, `app/db/`, Ledger | Source of truth, validation, persistence |

**Do not:** call the LLM from React; put business math in prompts; skip the orchestrator for chat flows.

---

## 2. Deterministic core, probabilistic edge

| Concern | Owner |
|---------|--------|
| Balances, net worth, spending totals, affordability math | Ledger / application code |
| Transactions, accounts, imports | PostgreSQL via APIs and agent tools |
| Intent, slot filling, short explanations | Planner / Insight (optional LLM) |

**Rule:** The LLM is never the source of truth for money. It interprets language and proposes actions; tools compute numbers.

---

## 3. Strict schemas between layers

All cross-layer payloads use Pydantic models in `app/core/schemas.py`.

- **Planner → Orchestrator:** `PlannerOutput` (`intent`, `steps`, `ui_mode`)
- **State:** `ConversationState` in Redis (`app/core/state_manager.py`)
- **API → UI:** `AgentResponse` with canonical `CardType` values

**Rule:** Guided UI is driven by `ui_type` + structured `data`, not by parsing free-form model text.

Extend `Intent`, `PlannerStep`, and `CardType` when adding features—do not invent parallel JSON shapes.

---

## 4. Planner–executor, not agent swarm

Preferred flow:

1. User message → **Planner** (intent + steps + params)
2. **Orchestrator** executes steps (e.g. Ledger, Insight)
3. **UI Guide** builds cards and `next_suggested_actions`

Start with a small agent set. Avoid many autonomous agents calling each other in loops (hard to debug, expensive, unreliable).

---

## 5. Confirm before mutating money

Writes (add expense, import, delete, bulk update) must:

1. Extract or collect required slots
2. Show a confirmation card (e.g. `transaction_confirm`)
3. Commit only after explicit user confirmation (or a strict, tested API path)

**Rule:** The model proposes; the user or a gated tool commits.

---

## 6. Explicit conversation state

Store in Redis per `conversation_id`:

- `current_step`, `filled_slots`, short `agent_history`

Do not rely on the model alone to remember prior turns. The frontend should use a state machine (`frontend/lib/chatMachine.ts`) for guided flows—not ad-hoc string matching in components.

---

## 7. LLM as optional infrastructure

- Settings: `app/core/llm_settings.py`, client: `app/services/llm_client.py`
- `LLM_PROVIDER=none` must remain viable (rules, router, fallbacks)
- Low temperature for extraction; one primary model until stable
- Never commit API keys; document env vars in `.env.example` and [LLM_SETUP.md](./LLM_SETUP.md)

---

## 8. Graceful degradation

Every LLM path needs a fallback:

- Semantic router / rules when the model fails
- `Intent.unknown` with helpful `next_suggested_actions`
- `message_only` card instead of HTTP 500

Core flows (add expense, list transactions, net worth from DB) must work when the LLM is disabled.

---

## 9. Observability

Log (avoid PII and secrets in logs):

- `conversation_id`, intent, agent/action, latency, provider errors

Required to debug “wrong number” or “wrong intent” reports.

---

## 10. Security and trust (finance)

- Scope data by `user_id`; no cross-user leakage
- Sanitize exports and prompts; no secrets in chat history sent to providers
- Distinguish in UI: ledger-backed facts vs estimates or narrative
- India context (₹, EMI, categories) in product copy and prompts—not invented figures

---

## 11. MVP build order

1. CRUD + ledger data model
2. Orchestrator + Planner + Ledger tools
3. Structured cards + frontend state machine
4. Optional LLM for insight/narrative
5. Import, categorization, advanced analytics

Ship one end-to-end flow (e.g. “add ₹500 Swiggy” with confirm) before adding many intents.

---

## 12. Testing

| Test | Target |
|------|--------|
| Integration | `pytest tests/` — health, accounts, transactions, chat intents |
| Unit | Ledger math, planner routing, `llm_client` with mocks |
| Avoid | Asserting exact LLM wording on every run |

---

## Summary

**Deterministic orchestrator · typed contracts · tools for facts · LLM for language and routing · explicit state · confirm-before-write · fallbacks when the model fails.**

When in doubt, match existing patterns in `orchestrator.py`, `schemas.py`, and `agents/` rather than introducing a new ad-hoc chat path.
