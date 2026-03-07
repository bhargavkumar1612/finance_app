# Finance Copilot — Phases Overview

One-line goals and links to detailed plans. Use this as the index for “what’s next.”

| Phase | Goal | Plan |
|-------|------|------|
| **Phase 0** | Foundation — DB, layout, core contracts, manual transaction API, basic chat stub | (Done; see REQUIREMENTS_BREAKDOWN.md) |
| **Phase 1** | Orchestration & Ledger — Planner, Ledger tools, Redis state, chat → real behaviour | [PHASE1_PLAN.md](PHASE1_PLAN.md) |
| **Phase 2** | Ingestion — CSV/PDF parser, normalizer, deduper, import API, confirm flow | [PHASE2_PLAN.md](PHASE2_PLAN.md) |
| **Phase 3** | Guided UI & Chat — Frontend app, XState, card registry, chat UI, import review screen, UI Guide | [PHASE3_PLAN.md](PHASE3_PLAN.md) |
| **Phase 4** | Insights & Affordability — Insight agent (narrative), monthly summary, net worth card, affordability engine, missing data | [PHASE4_PLAN.md](PHASE4_PLAN.md) |
| **Phase 5** | Hardening & India — Validation, confidence thresholds, observability, UPI/EMI/FY/80C, categorization, optional Celery | [PHASE5_PLAN.md](PHASE5_PLAN.md) |

---

## Suggested order

- **Next:** Phase 3 (Guided UI) — so the product has a proper frontend and cards.
- **Then:** Phase 4 (Insights & Affordability) — richer answers and affordability.
- **Then:** Phase 5 (Hardening & India) — production-ready rules and India features.

High-level task breakdown and clarifying questions: [../REQUIREMENTS_BREAKDOWN.md](../REQUIREMENTS_BREAKDOWN.md).
