# Phase 3 — Guided UI & Chat — Plan

**Goal:** Replace the static HTML with a proper frontend that drives and is driven by the backend: conversation state machine, dynamic cards keyed by `ui_type`, chat with suggested actions, and a guided import review screen.

**Success criteria:**
- User sends a chat message → API returns `AgentResponse` with optional `ui_type` + payload → frontend renders the right card (e.g. transaction_confirm, monthly_summary, net_worth_breakdown) and shows next_suggested_actions.
- Add-expense flow can show a confirmation card (amount, merchant, category) with Accept / Edit / Reject when confidence is below threshold (or always for Phase 3 clarity).
- Import flow: upload → see list of normalized rows with confidence/duplicate flags → bulk accept / edit / reject → confirm posts to `/v1/import/confirm`.
- One coherent app (React or Next.js) with routing; optional: keep `static/index.html` as a simple fallback for API-only use.

---

## 1. What Exists (Phase 0–2)

| Piece | Location | Use in Phase 3 |
|-------|----------|----------------|
| `AgentResponse` | `app/core/schemas.py` | status, data, confidence, next_suggested_actions. **Extend** with optional `ui_type` + `card_payload` for dynamic cards. |
| Chat API | `app/api/chat.py` | POST `/v1/chat` → orchestrator → `ChatResponse`. Frontend will call this and render by `ui_type`. |
| Import API | `app/api/import_api.py` | POST `/v1/import`, POST `/v1/import/confirm`. Guided review screen will use these. |
| Static UI | `static/index.html` | Tab-based: Overview, Accounts, Transactions, Chat, Import. Replace or mirror in SPA. |
| Orchestrator | `app/core/orchestrator.py` | Builds `AgentResponse` with `data` (message, summary, net_worth, etc.). Phase 3 adds **UI Guide** step to set `ui_type` and `card_payload`. |

---

## 2. Phase 3 Task Breakdown (Ordered)

| # | Task | Owner | Depends on |
|---|------|--------|------------|
| **3.1** | Extend `AgentResponse` with `ui_type` and `card_payload`; define canonical card types | `app/core/schemas.py`, docs | — |
| **3.2** | UI Guide (backend) — map intent + Ledger result → `ui_type` + `card_payload` + chat_summary | `app/agents/ui_guide.py` or inside orchestrator | 3.1 |
| **3.3** | Wire orchestrator to UI Guide and return enriched `AgentResponse` | `app/core/orchestrator.py` | 3.2 |
| **3.4** | Frontend app scaffold — React or Next.js, routing, layout, API base URL | `frontend/` or `app/frontend/` | — |
| **3.5** | Conversation state machine (XState) — states: chat, form, selection, confirmation, result; transitions from API response | Frontend | 3.4 |
| **3.6** | Dynamic card registry — map `ui_type` → component (transaction_confirm, monthly_summary, net_worth_breakdown, affordability_result, selection_card, message_only) | Frontend | 3.5 |
| **3.7** | Transaction confirmation card — show amount, merchant, category; Accept / Edit / Reject buttons | Frontend | 3.6 |
| **3.8** | Chat UI — input, send to `/v1/chat`, display message + card + next_suggested_actions (clickable chips) | Frontend | 3.6, 3.7 |
| **3.9** | Guided import review screen — list parsed rows (confidence, is_duplicate), bulk accept / edit / reject, confirm button → POST `/v1/import/confirm` | Frontend | 3.4, Import API |
| **3.10** | Optional: Replace or hide static HTML when SPA is served (e.g. FastAPI serves SPA at `/` in prod, static only in dev) | `app/main.py`, frontend build | 3.8, 3.9 |

Recommended implementation order: **3.1 → 3.2 → 3.3** (backend first), then **3.4 → 3.5 → 3.6 → 3.7 → 3.8** (frontend chat), then **3.9 → 3.10**.

---

## 3. File & Module Layout (New/Changed)

### Backend

```
app/
  core/
    schemas.py           # Add: ui_type, card_payload to AgentResponse; CardType enum or literal
  agents/
    ui_guide.py          # NEW — intent + result → ui_type, card_payload, message
  core/
    orchestrator.py      # CHANGE — after Ledger, call UI Guide; attach ui_type, card_payload to response
  api/
    chat.py              # (no change if response model already returns full AgentResponse)
```

### Frontend (example: React + Vite or Next.js)

```
frontend/                 # or app/frontend/
  src/
    api/
      client.ts           # base URL, fetch /v1/chat, /v1/import, /v1/import/confirm
    state/
      chatMachine.ts      # XState machine: chat | form | selection | confirmation | result
    components/
      Chat/
        ChatInput.tsx
        ChatLog.tsx
        SuggestedActions.tsx
      cards/
        registry.ts       # ui_type → Component
        TransactionConfirmCard.tsx
        MonthlySummaryCard.tsx
        NetWorthBreakdownCard.tsx
        MessageOnlyCard.tsx
    pages/
      Chat.tsx
      ImportReview.tsx
      Accounts.tsx
      Transactions.tsx
    App.tsx
  package.json
```

If you keep a single repo and serve the SPA from FastAPI: build frontend to `static/dist` or similar and mount that for `/` while keeping `/docs` and `/v1/*` on FastAPI.

---

## 4. Data Flow

### Chat flow

1. User types message → frontend sends POST `/v1/chat` with `{ "message": "...", "conversation_id": "..." }`.
2. Backend: orchestrator → planner → ledger → **UI Guide** → `AgentResponse(status, data, ui_type, card_payload, next_suggested_actions)`.
3. Frontend: state machine transitions to `result` (or stays in `chat`); card registry renders component for `ui_type` with `card_payload`; suggested actions shown as chips; user can click chip to send a follow-up or click Accept/Reject on card.

### Import review flow

1. User uploads file in Import tab → POST `/v1/import` with file + account_id (optional).
2. API returns `{ rows, account_id }`; frontend shows table/list with confidence, is_duplicate, amount, date, merchant.
3. User selects which rows to add (or bulk accept), optionally edits; clicks Confirm → POST `/v1/import/confirm` with `{ account_id, rows }`.
4. API returns `{ inserted, errors }`; frontend shows result and optionally navigates to Transactions.

### Confirmation card (add_expense)

- When `ui_type === "transaction_confirm"`, payload might be `{ amount, merchant, category, transaction_id?, summary }`.
- Accept → no further API call if already committed; or call a “confirm” endpoint if we defer commit (Phase 3 can keep current behaviour: Ledger already inserted, card is informational + “Add another”).
- Reject → could call a “revert last” API in a later phase; for Phase 3, Reject can be “Don’t add another” or hide card.

---

## 5. API Contract: `ui_type` and `card_payload`

Extend `AgentResponse` (and ChatResponse if it mirrors it):

```python
# app/core/schemas.py
class AgentResponse(BaseModel):
    status: str = "success"
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    next_suggested_actions: list[str] = Field(default_factory=list)
    # Phase 3
    ui_type: Optional[str] = None   # transaction_confirm | monthly_summary | net_worth_breakdown | affordability_result | selection_card | message_only
    card_payload: Optional[dict[str, Any]] = None
```

Suggested `ui_type` values and payloads:

| ui_type | When | card_payload (example) |
|--------|------|------------------------|
| `message_only` | unknown intent, or simple reply | `{}` or `{ "message": "..." }` |
| `transaction_confirm` | add_expense success | `{ "amount", "merchant", "category", "summary" }` |
| `monthly_summary` | spending_analysis | `{ "total_spend", "by_category", "period" }` |
| `net_worth_breakdown` | net_worth_query | `{ "net_worth", "assets", "liabilities" }` |
| `affordability_result` | affordability_check | `{ "safe_emi", "risk_level", "message" }` |
| `selection_card` | future: multi-option choice | `{ "options", "title" }` |

UI Guide agent (or a pure function) in backend maps `intent + last_result` to `ui_type` and `card_payload`, and optionally refines `data.message` as chat_summary.

---

## 6. XState (Conversation) States (Reference)

- **chat** — idle; user can type or click suggested action.
- **form** — optional; multi-slot form when we need amount/merchant/date (can be Phase 3.5 or later).
- **selection** — user selecting from a list (e.g. which account for import).
- **confirmation** — showing a confirmation card (e.g. transaction_confirm) with Accept/Reject.
- **result** — showing result card (e.g. monthly_summary) and suggested actions.

Transitions: API response can set `status` or `ui_type` to drive transition (e.g. `transaction_confirm` → confirmation; `monthly_summary` → result).

---

## 7. Step-by-Step Checklist

### Backend

- [ ] **3.1** Add `ui_type` and `card_payload` to `AgentResponse` in `schemas.py`; document canonical types in this doc or OPENAPI.
- [ ] **3.2** Implement UI Guide: function or light module that takes `(intent, last_result)` and returns `(ui_type, card_payload, chat_summary)`.
- [ ] **3.3** In orchestrator, after Ledger steps, call UI Guide and set `response.ui_type`, `response.card_payload`; use `chat_summary` for `data.message` when provided.

### Frontend

- [ ] **3.4** Create frontend app (React+Vite or Next.js), routing (e.g. `/`, `/chat`, `/import`, `/accounts`, `/transactions`), layout, env for API base URL.
- [ ] **3.5** Add XState machine for conversation (chat / form / selection / confirmation / result); transition on API response.
- [ ] **3.6** Card registry: map `ui_type` → component; default to `MessageOnlyCard` when `ui_type` is null or unknown.
- [ ] **3.7** Implement `TransactionConfirmCard` (amount, merchant, category, Accept/Edit/Reject).
- [ ] **3.8** Chat UI: input, send to `/v1/chat`, render response message + card + suggested actions; wire suggested action click to send that as next message.
- [ ] **3.9** Import review: upload → table of rows → select rows → confirm → POST `/v1/import/confirm`; show result.
- [ ] **3.10** (Optional) Serve SPA from FastAPI at `/` and keep `/docs`, `/v1/*`; or document dev setup (SPA on :3000, API on :8000).

---

## 8. Out of Scope for Phase 3 (Later)

- **Streaming** chat (Phase 3 can use single request/response).
- **Edit** on transaction card calling a real “update transaction” API (can be stub or Phase 4).
- **Revert** last transaction from Reject (Phase 4 or 5).
- **Auth** (login/signup) — keep single-user/dev for now unless you decide otherwise.
- **Insight agent** and narrative summaries (Phase 4).

---

## 9. Doc References

- REQUIREMENTS_BREAKDOWN.md — Phase 3 tasks 3.1–3.7 (Frontend app, XState, card registry, transaction confirm card, Chat UI, UI Guide agent, guided import review).
- PHASE1_PLAN.md — Orchestrator, Planner, Ledger, Redis state.
- PHASE2_PLAN.md — Import API, normalized rows, confirm endpoint.

Use this doc as the single checklist for Phase 3; update the tables above as you implement.
