# Project context — Finance Copilot

Owner priorities, mental model, and non-goals. Complements [DOMAIN_GLOSSARY.md](./DOMAIN_GLOSSARY.md) (terms) and [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) (architecture).

**Maintained by:** [domain-interview](../.cursor/skills/domain-interview/SKILL.md) sessions.

**Onboarding status:** Rounds 1–2 and 4 complete (2026-06-06). Drift remediation in progress.

---

## Product mental model

**Audience:** Multi-user — per-user data and isolation; not a single-user-only toy app.

**Core loop:** Deterministic orchestrator, typed responses, Ledger for facts and writes, LLM for language/routing only, confirm before mutating money.

**Financial lens:** Net worth is the anchor. **Spending** means what reduces net worth; liability payments and transfers are not spending. Primary accounts (bank, cash) fund derived accounts (credit cards, wallets).

---

## Priorities

All three pillars are **heavily used** and must be **high quality** — no "good enough for MVP" split between them.

| Pillar | What "perfect" means (owner intent) |
|--------|-------------------------------------|
| **Tracking** | Reliable imports, transactions, categories, account model (primary + derived) |
| **Planning** | Recurring bills, affordability, budget vs actual; later full YNAB-style envelopes |
| **Copilot chat** | Natural language over accurate ledger data — numbers from tools, not the model |

---

## Roadmap (owner-confirmed)

| Phase | Scope |
|-------|--------|
| **Now** | Tracking + planning + chat at high quality; spending/net-worth semantics per glossary |
| **Later** | YNAB-style envelope budgeting (assign income to categories; spend from envelopes) |

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

---

## Open questions

All Round 2 items resolved — see [DOMAIN_GLOSSARY.md](./DOMAIN_GLOSSARY.md) (Import and data, Chat and intents).
