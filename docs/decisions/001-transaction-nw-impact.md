# 001 — Transaction nw_impact semantics

**Status:** accepted

**Context:** Glossary defines spending as net-worth-reducing actions, not all bank debits. Code summed `amount < 0`, inflating spend with EMI, SIP, and CC bill payments.

**Decision:** Add `Transaction.nw_impact` (`spending`, `income`, `transfer`, `liability_payment`, `refund`, `unknown`) classified centrally in `app/services/transaction_semantics.py`. All spend totals filter on `nw_impact=spending`.

**Consequences:** Import review shows suggested impact; backfill script for legacy rows; hybrid net worth uses semantics for CC outstanding.

**Decided on:** 2026-06-06
