# Drift audit — glossary vs code

Checklist from onboarding audit (2026-06-06). Update status as fixes land.

| # | Issue | Phase | Status |
|---|--------|-------|--------|
| 1 | Spending = all debits | PR2 | Fixed — `spending.py` + `nw_impact` |
| 2 | Net worth empty Asset/Liability | PR3 | Fixed — hybrid `net_worth.py` + assets/liabilities API |
| 3 | Chat confirm after write | PR5 | Fixed — `pending_mutation` in orchestrator |
| 4 | Derived accounts not modeled | PR4 | Fixed — `parent_account_id` |
| 5 | CC double-count risk | PR4 | Fixed — import semantics + derived CC account |
| 6 | Chat cannot record income | PR6 | Fixed — `add_income` + `insert_income` |
| 7 | subscription vs recurring bill split | PR6 | Fixed — `list_recurring_bills` + alias |
| 8 | Phase 4 stub analytics | PR7 | Fixed — real ledger queries |
| 9 | UI "expense" = debit | PR2 | Fixed — spending filter + labels |
| 10 | Categories not used for spend | PR1 | Fixed — classifier uses categories |
| 11 | Affordability double-count EMI | PR2 | Fixed — spend + Liability.emi split |
| 12 | credit_limit unused in NW | PR3 | OK — limits excluded; outstanding from CC txns |
| 13 | Recurring bill amount semantics | PR1 | Fixed — classify on confirm |
| 14 | missing_data debit assumptions | PR2 | Fixed — nw_impact filters |
| 15 | Multi-user | — | Aligned (user_id isolation) |
| 16 | Account UI label | — | Aligned |
| 17 | YNAB budget stub | PR7 | Gated — message_only coming soon |
| 18 | Refunds undefined | Round 2A | Fixed — `refund` nw_impact |

**Audit command:** Compare glossary terms to `app/services/transaction_semantics.py`, `ledger_agent.py`, and UI labels after major changes.
