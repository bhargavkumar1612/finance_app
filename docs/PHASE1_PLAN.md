# Phase 1 — Orchestration & Ledger — Plan

**Goal:** Chat drives real behaviour: intent → Ledger tools → structured response. Conversation state lives in Redis.

**Success criteria:**
- User says “add 500 for Swiggy” → Planner returns `add_expense` → Ledger inserts transaction → UI gets `AgentResponse` with confirmation + next actions.
- User says “what’s my net worth?” → Planner returns `net_worth_query` → Ledger computes from assets/liabilities → response with breakdown (or “no data”).
- Conversation state (e.g. `conversation_id`, `filled_slots`, `current_step`) is stored and read from Redis.

---

## 1. What Already Exists (Phase 0)

| Piece | Location | Use in Phase 1 |
|-------|----------|----------------|
| `Intent`, `PlannerOutput`, `PlannerStep` | `app/core/schemas.py` | Planner returns these. |
| `AgentResponse` | `app/core/schemas.py` | Unified response from Orchestrator. |
| `ChatRequest` / `ChatResponse` | `app/api/chat.py` | Wire to Orchestrator instead of placeholder. |
| Transaction CRUD, user/account resolution | `app/api/transactions.py`, `accounts.py` | Ledger tools will call same DB layer. |
| Redis URL | `app/core/config.py` (`REDIS_URL`) | State manager. |
| DB models | `app/db/models.py` | Ledger reads/writes. |

---

## 2. Phase 1 Task Breakdown (Ordered)

| # | Task | Owner module | Depends on |
|---|------|--------------|------------|
| **1.4** | Redis state manager | `app/core/state_manager.py` | — |
| **1.2** | Planner agent (rule-based) | `app/agents/planner.py` | — |
| **1.3** | Ledger agent (tools) | `app/agents/ledger_agent.py` | DB, user resolution |
| **1.1** | Orchestrator | `app/core/orchestrator.py` | 1.2, 1.3, 1.4 |
| **1.5** | Wire chat API to Orchestrator | `app/api/chat.py` | 1.1 |

Recommended implementation order: **1.4 → 1.2 → 1.3 → 1.1 → 1.5**.

---

## 3. File & Module Layout (New/Changed)

```
app/
  core/
    config.py          # (existing)
    schemas.py         # (existing; maybe add ConversationState)
    state_manager.py   # NEW — Redis get/set conversation state
    orchestrator.py    # NEW — run Planner → Ledger → build AgentResponse
  agents/
    planner.py         # NEW — rule-based intent + steps
    ledger_agent.py    # NEW — tools: insert_txn, fetch_txns, net_worth, monthly_spend
  api/
    chat.py           # CHANGE — call orchestrator instead of placeholder
```

Optional: add `app/core/conversation_state.py` with a Pydantic model for the state (e.g. `conversation_id`, `current_step`, `filled_slots`, `agent_history`).

---

## 4. Data Flow

```
Client                    API                    Orchestrator              Agents
  |                        |                            |                    |
  | POST /v1/chat          |                            |                    |
  | { message, conv_id }   |                            |                    |
  |----------------------->|                            |                    |
  |                        | load_state(conv_id)        |                    |
  |                        |--------------------------->| Redis              |
  |                        |                            |                    |
  |                        | plan(message, state)       |                    |
  |                        |--------------------------->|------------------->| Planner
  |                        |                            |<------------------|
  |                        |                            | PlannerOutput      |
  |                        |                            |                    |
  |                        | for step in steps:         |                    |
  |                        |   ledger.run(step)         |------------------->| Ledger
  |                        |                            |<------------------|
  |                        |                            | tool result        |
  |                        | build AgentResponse        |                    |
  |                        | save_state(conv_id, state) |                    |
  |                        |--------------------------->| Redis              |
  |                        |                            |                    |
  |<-----------------------| ChatResponse               |                    |
  | { response, conversation_id }                       |                    |
```

---

## 5. Key Interfaces

### 5.1 State (Redis)

- **Key pattern:** `conv:{conversation_id}` (or `session:{user_id}:{conversation_id}` if you add user later).
- **Value:** JSON with e.g. `current_step`, `filled_slots`, `agent_history` (last N messages or summary), `created_at`, `updated_at`.
- **TTL:** e.g. 24 hours; refresh on each request.
- **StateManager API (suggested):**
  - `get_state(conversation_id: str) -> ConversationState | None`
  - `set_state(conversation_id: str, state: ConversationState, ttl_seconds: int = 86400) -> None`

### 5.2 Planner

- **Input:** `message: str`, optional `state: ConversationState` (for slots / multi-turn later).
- **Direct Skill Prompting (Arch Decision):** The LLM is given manual JSON schemas of all tools in its system prompt rather than using the native OpenAI `tools=` API (which models like deepseek-r1 struggle with).
- **Conversational vs. Skill Routing:** The LLM is instructed to return `{"tool": "name", "parameters": {...}}` if a tool is needed, OR `{"message": "..."}` if it is just chatting/summarizing.
- **Output:** Parsed JSON into `PlannerOutput` (intent, steps, ui_mode, optional message).
- **Unknown:** If the LLM returns `{"message": "..."}`, intent defaults to `unknown`, steps empty, and the Orchestrator surfaces the LLM's conversational reply directly.

### 5.3 Ledger agent (tools)

- **Interface:** One entrypoint, e.g. `run(session, user_id, action: str, params: dict) -> dict`.
- **Actions (Phase 1):**
  - `insert_transaction`: params = amount, transaction_date, account_id, merchant?, category? → create transaction; return `{ created_id, summary }`.
  - `fetch_transactions`: params = limit?, from_date?, to_date? → return list of transactions (or summary).
  - `compute_net_worth`: params = {} → sum assets − sum liabilities; return `{ net_worth, assets_total, liabilities_total, breakdown? }`.
  - `compute_monthly_spend`: params = month?, year? → sum(transactions where amount < 0) by category; return `{ total_spend, by_category, period }`.
- **User/session:** Ledger gets `user_id` (and optionally `account_id` for default) from Orchestrator; Orchestrator gets user from request (e.g. same as Phase 0: default user or header).

### 5.4 Orchestrator

- **Input:** `message: str`, `conversation_id: str`, `user_id: UUID` (from request / default).
- **Steps:**
  1. Load state from Redis for `conversation_id`; if none, create empty state.
  2. Call Planner with `message` (and state if needed) → `PlannerOutput`.
  3. For each step: if `agent == "ledger"`, call Ledger with `action` and `params`; collect result.
  4. Build `AgentResponse`: status, data = combined results, confidence, next_suggested_actions (e.g. from a small rule map per intent).
  5. Optionally update state (e.g. append to agent_history, set current_step); save to Redis.
  6. Return `AgentResponse`.
- **Error handling:** On Ledger/Planner error, return `AgentResponse(status="error", data={"error": "..."})`.

---

## 6. Implementation Checklist (Step-by-Step)

### Step 1 — Redis state manager (Task 1.4)

- [ ] Add `redis` to `requirements.txt` if not present (already there).
- [ ] Create `app/core/state_manager.py`:
  - [ ] Redis connection from `settings.redis_url` (sync or async; async preferred if rest of app is async).
  - [ ] `ConversationState` model (e.g. Pydantic): `conversation_id`, `current_step`, `filled_slots`, `agent_history`, `updated_at`.
  - [ ] `get_state(conversation_id) -> ConversationState | None`.
  - [ ] `set_state(conversation_id, state, ttl_seconds=86400)`.
- [ ] Optional: add `ConversationState` to `app/core/schemas.py` and import in state_manager.
- [ ] Unit test or manual test: set state, get state, TTL expiry.

### Step 2 — Planner agent (Task 1.2)

- [ ] Create `app/agents/planner.py`:
  - [ ] `plan(message: str, state: ConversationState | None = None) -> PlannerOutput`.
  - [ ] Rule-based: normalize message (lower, strip), match keywords to `Intent`, build one step with `agent="ledger"` and appropriate `action` + `params`.
  - [ ] For `add_expense`: simple extraction (e.g. regex for amount, rest as merchant); if missing amount/date, params can be partial (UI Guide can ask later).
  - [ ] Return `PlannerOutput(intent=..., steps=[...], ui_mode="guided_flow")`.
- [ ] Test with a few sample messages (add expense, net worth, spending, unknown).

### Step 3 — Ledger agent / tools (Task 1.3)

- [ ] Create `app/agents/ledger_agent.py`:
  - [ ] Accept async DB session and `user_id` (and optionally default `account_id`).
  - [ ] `run(session, user_id, action: str, params: dict) -> dict`:
    - [ ] `insert_transaction`: validate params, create `Transaction` (reuse logic from `api/transactions.py`), return `{ "created_id": str, "summary": str }`.
    - [ ] `fetch_transactions`: query `Transaction` by user_id, optional date range, limit; return list or summary.
    - [ ] `compute_net_worth`: query `Asset` and `Liability` for user, sum; return `{ "net_worth", "assets_total", "liabilities_total" }`.
    - [ ] `compute_monthly_spend`: filter transactions by month/year, amount < 0, group by category; return `{ "total_spend", "by_category", "period" }`.
  - [ ] On validation error, raise or return `{ "error": "..." }` so Orchestrator can map to `AgentResponse(status="error", ...)`.
- [ ] Reuse or import from `app.db.models` and existing validation patterns; avoid duplicating business logic.

### Step 4 — Orchestrator (Task 1.1)

- [ ] Create `app/core/orchestrator.py`:
  - [ ] `run(message: str, conversation_id: str, user_id: UUID) -> AgentResponse`.
  - [ ] Load state (state_manager); call Planner; for each Ledger step, get DB session (e.g. `async_session_maker`), call Ledger, collect results.
  - [ ] Build `AgentResponse`: data = last result or combined; next_suggested_actions = simple list per intent (e.g. add_expense → ["Add another expense", "View this month's spending"]).
  - [ ] Save updated state; return response.
- [ ] Handle exceptions: Planner/Ledger errors → `AgentResponse(status="error", data={"error": str(e)})`.

### Step 5 — Wire chat API (Task 1.5)

- [ ] In `app/api/chat.py`:
  - [ ] Resolve `user_id` (same as Phase 0: get_or_create_default_user or from header/env).
  - [ ] Generate or use `conversation_id` from body (required or default to new UUID per request for MVP).
  - [ ] Call `orchestrator.run(message, conversation_id, user_id)`.
  - [ ] Return `ChatResponse(response=..., conversation_id=conversation_id)`.
- [ ] Remove placeholder echo logic.
- [ ] End-to-end test: “add 500 for Swiggy”, “what’s my net worth?”.

---

## 7. Optional Enhancements (Within Phase 1)

- **Planner:** Simple slot extraction for add_expense (amount, merchant) and pass to Ledger so one-shot “add 500 Swiggy” works without a follow-up.
- **State:** Store last N user/assistant messages in `agent_history` for future LLM context.
- **Next actions:** Map intent → suggested actions in Orchestrator or a tiny config table.

---

## 8. Out of Scope for Phase 1

- Insight agent (Phase 4).
- UI Guide agent (Phase 3); Orchestrator can still return `next_suggested_actions` and a fixed `ui_mode`.
- LLM-based Planner (can add in Phase 1.2 iteration).
- Auth (continue using default user / single user).

---

## 9. Testing & Validation

- **Unit:** State manager get/set; Planner intent for 5–10 sample messages; Ledger each action with in-memory or test DB.
- **Integration:** Orchestrator with real Redis + Postgres (e.g. docker-compose); one add_expense and one net_worth_query.
- **API:** `POST /v1/chat` with “add 450 for Swiggy” and “what’s my net worth?”; assert response shape and, for add_expense, that a transaction exists.

---

## 10. Rough Effort (Reference)

| Task | Estimate |
|------|----------|
| 1.4 State manager | 0.5 day |
| 1.2 Planner (rule-based) | 1 day |
| 1.3 Ledger tools | 1–1.5 days |
| 1.1 Orchestrator | 1 day |
| 1.5 Wire chat + E2E | 0.5 day |
| **Total** | **~4–5 days** |

Use this doc as the single source of truth for Phase 1; tick the checkboxes as you implement each item.
