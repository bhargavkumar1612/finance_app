# Task — Slice 2: Obligations hub

**Prerequisite:** Slice 1 committed  
**PRD:** [AI_CHAT_FEATURES_PRD.md](../AI_CHAT_FEATURES_PRD.md) § Slice 2, §10, §11  
**ADR:** [002-financial-persona.md](../decisions/002-financial-persona.md)

## Goal

Unified obligations card in chat + affordability that subtracts **all** commitments + persona DB/Settings.

## Scope (S2.1–S2.6)

| ID | Feature | Intent | Card |
|----|---------|--------|------|
| S2.1 | Upcoming obligations | `upcoming_obligations` | `obligation_list` |
| S2.2 | Loan EMI summary | `loan_emi_summary` | section in obligation card |
| S2.3 | Affordability + commitments | `affordability_check` | `affordability_result` |
| S2.4 | Create recurring from chat | `create_recurring_bill` | confirm → REST |
| S2.5 | Post-import bill suggestions | — | CTA from `recurring_suggestions` |
| S2.6 | Persona LLM + Settings | — | user-editable persona |

## Affordability formula

```
safe_surplus = income − spending − loan_emis − sip_emis − recurring_bills − cc_commitments
```

Then apply existing safe-EMI ratio on remainder.

## Obligations card sections

1. **SIPs** — MF SIP accounts (`due_day`, paid this month)
2. **Loan EMIs** — `loan` accounts + `loan_schedule`
3. **Recurring bills** — `RecurringBill` rows
4. **Credit cards** — `due_day` (informational)

Sort by next due date within each section.

## Implementation order

1. `commitments.py` + `obligations.py`
2. Extend `affordability.py`
3. Schemas → ledger → planner → ui_guide → `ObligationListCard`
4. `create_recurring_bill` confirm flow
5. `api.ts` + import/Accounts CTA for suggestions
6. Persona migration + API + Settings editor + orchestrator post-session hook (`persona_hook.py`)

## Touch points

- `schemas.py`, `ledger_agent.py`, `planner.py`, `ui_guide.py`, `orchestrator.py`, `pending_mutation.py`
- `apps/web/components/cards/ObligationListCard.tsx`
- `apps/web/app/settings/page.tsx` (persona section)
- Tests: `test_chat_slice2.py`, `test_planner_slice2.py`, e2e `REG-C020+`

## Out of scope (Slice 3)

- `record_transfer` dual-leg SIP capture
- Chat-guided import wizard

## Success criteria

- Obligations card shows four sections when data exists
- Affordability changes when SIP/EMI/bills added
- Persona round-trip in Settings
- `LLM_PROVIDER=none` routes Slice 2 phrases
- All test layers green
