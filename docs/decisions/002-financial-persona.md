# 002 — Financial persona (per-user copilot profile)

**Status:** accepted

**Context:** Owner wants proactive, personalized nudges on Accounts + chat without letting the LLM invent financial facts. Portfolio dashboard should hide sections the user has no stake in and suggest onboarding in the card footer. Personality should improve over time.

**Decision:**

1. Store a **per-user financial persona** in PostgreSQL (markdown body and/or structured JSON fields).
2. **Update after each chat session:** deterministic rules merge first; optional LLM writes a short summary delta into the stored persona (not shown raw in chat by default).
3. **User can view and edit** persona in Settings.
4. **Consumers:** Insight agent narrative tone; proactive nudge copy (Accounts + chat); portfolio drill-down / footer suggestion prioritization.
5. **Not a source of truth for money** — Ledger + PostgreSQL transactions remain authoritative; persona is preferences and derived patterns only.

**Persona fields (all in scope):**

- Income pattern (salary day, average surplus)
- Spending personality (category skew, subscription-heavy, etc.)
- Investment style (SIP-regular vs lump-sum)
- Risk / tone preference (blunt vs encouraging)
- Goals mentioned in chat (free text, user-editable)

**Privacy:** Server-side per user; OK to include in agent context; do not log full persona to application info logs.

**Consequences:**

- New migration + API for persona CRUD and session hook in orchestrator.
- Settings UI for edit.
- Tests must mock LLM persona updates; app must work when persona is empty.
- Expand surfaces beyond Accounts/chat later without schema change if body is markdown.

**Decided on:** 2026-06-07 (domain interview Round 8)
