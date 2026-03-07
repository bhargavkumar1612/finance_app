# Phase 4 — Insights & Affordability — Plan

**Goal:** Add an Insight agent that uses Ledger data to produce spending patterns and narratives (LLM for text only); polish net worth and monthly summary flows; implement a deterministic affordability engine (India-tuned formulas); and detect missing data to prompt the user.

**Success criteria:**
- User asks “where did I spend this month?” or “spending breakdown” → Insight agent gets data via Ledger tools, returns narrative + structured summary → UI shows monthly_summary card.
- Net worth flow returns assets, liabilities, net worth with breakdown (deterministic; already partly in Ledger).
- User asks “can I afford 30k EMI?” → Affordability engine computes safe EMI, debt ratio, risk level (formulas only; no LLM for numbers) → affordability_result card.
- Missing data detection: rule-based checks (e.g. no salary this month, no rent) → UI Guide or dedicated prompt so user can fill gaps.

---

## 1. What Exists (Phase 0–3)

| Piece | Location | Use in Phase 4 |
|-------|----------|----------------|
| Ledger agent | `app/agents/ledger_agent.py` | Already has compute_net_worth, compute_monthly_spend, compute_affordability. Insight will call these. |
| Planner | `app/agents/planner.py` | Intent: spending_analysis, net_worth_query, affordability_check. Orchestrator routes to Ledger; Phase 4 adds Insight step for narrative. |
| Orchestrator | `app/core/orchestrator.py` | Today: plan → Ledger only. Phase 4: for insight intents, run Ledger then **Insight agent**; UI Guide already maps to cards (Phase 3). |
| AgentResponse, ui_type, card_payload | `app/core/schemas.py` | monthly_summary, net_worth_breakdown, affordability_result card types (Phase 3). |
| Assets, Liabilities | `app/db/models.py` | Net worth = sum(assets) − sum(liabilities); affordability uses income/expenses/EMI. |

---

## 2. Phase 4 Task Breakdown (Ordered)

| # | Task | Owner | Depends on |
|---|------|--------|------------|
| **4.1** | Insight agent — input: intent + Ledger result; output: narrative message + optional structured summary (top categories, month-over-month, anomaly hint) | `app/agents/insight_agent.py` | Ledger, LLM config |
| **4.2** | Wire Planner/orchestrator to Insight for spending_analysis (and optionally net_worth_query, affordability_check for narrative) | `app/core/orchestrator.py` | 4.1 |
| **4.3** | Monthly summary card payload — ensure Ledger/Insight return by_category, total_spend, period, top_category; UI Guide maps to monthly_summary | Backend + Phase 3 frontend | 4.1, 4.2 |
| **4.4** | Net worth breakdown — Ledger already returns net_worth/assets/liabilities; ensure UI Guide sends net_worth_breakdown card_payload; frontend card if not done in Phase 3 | Backend, frontend | Phase 3 cards |
| **4.5** | Affordability engine — refine formula: income vs expenses, debt-service ratio, safe EMI (e.g. 40–50% of surplus); no LLM for numbers | `app/agents/ledger_agent.py` or `app/services/affordability.py` | Ledger tools |
| **4.6** | Affordability result card — safe_emi, risk_level, message; UI Guide maps to affordability_result | Backend, frontend | 4.5, Phase 3 cards |
| **4.7** | Missing data detection — rules: e.g. “no income transaction this month”, “no rent”, “no EMI”; return list of hints; UI Guide or dedicated response can surface these | `app/services/missing_data.py` or in Ledger | 4.1 |

Recommended order: **4.5 → 4.6** (affordability deterministic first), **4.1 → 4.2 → 4.3** (Insight + monthly summary), **4.4** (net worth card payload), **4.7** (missing data).

---

## 3. File & Module Layout (New/Changed)

### Backend

```
app/
  agents/
    insight_agent.py       # NEW — run(session, user_id, intent, ledger_result) -> narrative + summary dict
  services/
    affordability.py       # OPTIONAL — move affordability formula here from ledger_agent for clarity
    missing_data.py        # NEW — check_missing_data(session, user_id) -> list[str] hints
  core/
    orchestrator.py        # CHANGE — for spending_analysis (and optionally others), call Insight after Ledger; merge narrative into response
  agents/
    ledger_agent.py        # CHANGE — ensure compute_affordability returns safe_emi, risk_level, message; maybe delegate to affordability.py
```

### Frontend (if not done in Phase 3)

```
frontend/src/components/cards/
  MonthlySummaryCard.tsx   # total_spend, by_category, period, top_category
  NetWorthBreakdownCard.tsx # net_worth, assets, liabilities
  AffordabilityResultCard.tsx # safe_emi, risk_level, message
```

---

## 4. Data Flow

### Spending analysis (Insight)

1. User: “Where did I spend this month?” → Planner: spending_analysis → Orchestrator runs Ledger `compute_monthly_spend` → gets `total_spend`, `by_category`, etc.
2. Orchestrator calls **Insight agent** with intent=spending_analysis, ledger_result=that dict.
3. Insight (LLM): generates short narrative (e.g. “You spent ₹X this month; top category was Food.”). Optional: add month-over-month or anomaly hint from rules.
4. UI Guide: ui_type=monthly_summary, card_payload={ total_spend, by_category, period, top_category, narrative }.
5. Frontend: MonthlySummaryCard + suggested actions.

### Affordability

1. User: “Can I afford 30k EMI?” → Planner: affordability_check, params e.g. { requested_emi: 30000 }.
2. Ledger `compute_affordability`: fetch income (credits), expenses (debits), existing EMI/liabilities; compute surplus, debt ratio, safe EMI (formula); return risk_level (low/medium/high).
3. No LLM for numbers. Optional: Insight adds one-sentence recommendation.
4. UI Guide: ui_type=affordability_result, card_payload={ safe_emi, risk_level, message }.

### Missing data

1. After Ledger (or on demand): call `check_missing_data(session, user_id)`.
2. Rules: e.g. no transaction with category/description “salary” this month; no “rent”; no liability with type EMI. Return list of hints.
3. Orchestrator or UI Guide can append to response: “You might want to add: salary for this month, rent.”
4. Frontend: can show as a small “Suggestions” block or in chat_summary.

---

## 5. Key Interfaces

### 5.1 Insight agent

- **Input:** `session`, `user_id`, `intent` (spending_analysis | net_worth_query | affordability_check), `ledger_result: dict`.
- **Output:** `{ "narrative": str, "summary": dict }` (summary optional; narrative is the chat message or addition to it).
- **LLM:** Use only for narrative text. No amounts or dates from LLM; all numbers from ledger_result.

### 5.2 Affordability (deterministic)

- **Input:** user_id, optional `requested_emi` (for “can I afford X?”).
- **Output:** `{ "safe_emi", "risk_level", "message", "debt_ratio", "surplus" }` (or similar). Formula: e.g. safe_emi = min(requested_emi, surplus * 0.4).

### 5.3 Missing data

- **Input:** session, user_id, optional period (default: current month).
- **Output:** `list[str]` e.g. ["Add salary for this month", "Rent not found"].

---

## 6. Step-by-Step Checklist

- [ ] **4.5** Implement or refine affordability formula in Ledger (or affordability.py); return safe_emi, risk_level, message.
- [ ] **4.6** UI Guide: map affordability result to affordability_result card; frontend AffordabilityResultCard if not in Phase 3.
- [ ] **4.1** Implement Insight agent: call LLM with intent + ledger_result (no numbers in prompt except for display); return narrative + optional summary.
- [ ] **4.2** Orchestrator: for spending_analysis (and optionally net_worth_query, affordability_check), call Insight after Ledger; merge narrative into data.message or card.
- [ ] **4.3** Ensure monthly_summary card_payload is complete; MonthlySummaryCard in frontend.
- [ ] **4.4** Net worth: ensure net_worth_breakdown payload; NetWorthBreakdownCard if not done in Phase 3.
- [ ] **4.7** Missing data: implement rule-based check_missing_data; hook into response (e.g. next_suggested_actions or extra data field).

---

## 7. Out of Scope for Phase 4

- Full anomaly detection (ML); Phase 4 uses simple rules (e.g. “spend > 2× last month”).
- Multi-currency or multi-FY (India FY Apr–Mar) — Phase 5.
- Categorization service (Phase 5).

---

## 8. Doc References

- REQUIREMENTS_BREAKDOWN.md — Phase 4 tasks 4.1–4.6.
- PHASE3_PLAN.md — UI Guide, card types, frontend cards.
- PHASE1_PLAN.md — Orchestrator, Ledger tools.
