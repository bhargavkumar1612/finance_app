# Phase 5 — Hardening & India — Plan

**Goal:** Harden the product with validation guardrails, confidence thresholds for writes, and observability; add India-specific features (UPI, EMI, FY, 80C, SIP); optional categorization service and Celery for background jobs.

**Success criteria:**
- All writes (manual, chat, import) pass validation guardrails (no negative income, EMI vs outstanding, date rules, currency).
- Low-confidence writes require explicit confirm; no silent low-confidence insert.
- Observability: log or expose agent calls, tool latency, token usage, correction rate (for tuning).
- India: UPI detection in narrations, EMI auto-detect from liabilities, FY (Apr–Mar) in reports, optional 80C/SIP recognition.

---

## 1. What Exists (Phase 0–4)

| Piece | Location | Use in Phase 5 |
|-------|----------|----------------|
| Transaction, Asset, Liability | `app/db/models.py` | Validation: amount sign, date, EMI vs outstanding. |
| Ledger insert_transaction | `app/agents/ledger_agent.py` | Add validation layer before insert; respect confidence threshold. |
| Import flow | `app/api/import_api.py`, normalizer | Confidence on rows; confirm only selected. |
| Config | `app/core/config.py` | Add CONFIDENCE_THRESHOLD, feature flags for India. |
| No observability yet | — | Add middleware or agent wrapper for latency, token count. |

---

## 2. Phase 5 Task Breakdown (Ordered)

| # | Task | Owner | Depends on |
|---|------|--------|------------|
| **5.1** | Validation guardrails — central validator: income (credit) not negative; expense date not future; EMI ≤ outstanding; currency normalize to INR | `app/core/validation.py` or in Ledger | — |
| **5.2** | Confidence thresholds — config CONFIDENCE_THRESHOLD (e.g. 0.8); below threshold → status=confirm, do not insert until user confirms; never silent low-confidence write | Ledger, Import API, orchestrator | 5.1 |
| **5.3** | Observability — log agent (Planner/Insight) calls, Ledger tool name + latency; optional: token usage, correction rate metric | Middleware or wrapper in `app/core/observability.py` | — |
| **5.4** | India: UPI detection — tag or detect UPI in narration/merchant; use in categorization or reporting | `app/ingestion/normalizer.py` or `app/services/categorization.py` | — |
| **5.5** | India: EMI auto-detect — from liability type or description; link to recurring expense for affordability | Ledger, affordability | 4.5 |
| **5.6** | India: FY (Apr–Mar) — reports and spending analysis support “this FY” / “last FY” period | Ledger compute_monthly_spend, API params | — |
| **5.7** | India: 80C / SIP recognition — optional; tag transactions as 80C-eligible or SIP for tax view | Categorization or tags | 5.5 |
| **5.8** | Categorization service — rule-based merchant → category (e.g. SWIGGY → food); optional LLM for unknown merchant (category only, not amount/date) | `app/services/categorization.py` | — |
| **5.9** | Celery (optional) — background jobs for heavy projections, batch import, or report generation | `app/workers/`, config | — |

Recommended order: **5.1 → 5.2** (guardrails + confidence), **5.3** (observability), then **5.4 → 5.5 → 5.6 → 5.7** (India), **5.8** (categorization), **5.9** (Celery if needed).

---

## 3. File & Module Layout (New/Changed)

### Backend

```
app/
  core/
    validation.py          # NEW — validate_transaction, validate_income, validate_emi_vs_outstanding
    config.py              # ADD — CONFIDENCE_THRESHOLD, ENABLE_INDIA_FEATURES
    observability.py       # NEW — log_agent_call, log_tool_latency, optional token counter
  services/
    categorization.py      # NEW — merchant -> category (rules + optional LLM)
  ingestion/
    normalizer.py          # CHANGE — optional UPI tag in output
  agents/
    ledger_agent.py        # CHANGE — call validation before insert; respect confidence; optional EMI detection
  api/
    import_api.py          # CHANGE — confidence threshold for auto-suggest (already have per-row confidence)
  workers/                 # OPTIONAL
    celery_app.py
    tasks.py               # e.g. batch_import, generate_report
```

---

## 4. Validation Guardrails (Detail)

| Rule | Description | Where |
|------|-------------|--------|
| Income non-negative | Credits (income) must have amount ≥ 0 | validation.validate_transaction |
| Expense date | transaction_date not in future; optional: not older than N years | validation.validate_transaction |
| EMI vs outstanding | For liabilities: EMI × tenure consistent with outstanding (or warn) | validation.validate_liability or on update |
| Currency | Normalize to INR for MVP; reject or convert others if multi-currency later | validation or normalizer |
| Duplicate | Already in Phase 2 (fingerprint); ensure import confirm uses it | — |

---

## 5. Confidence Threshold Flow

- **Config:** `CONFIDENCE_THRESHOLD = 0.8` (or env).
- **Ledger insert_transaction:** If confidence < threshold (e.g. from Planner slot extraction), return status=confirm, data=preview, do not insert; frontend shows confirm card; on Accept, call confirm endpoint that then inserts.
- **Import:** Rows already have confidence; confirm API only inserts selected rows. Optional: hide or flag rows with confidence < threshold in UI.
- **Never:** Insert with confidence < threshold without explicit user confirm.

---

## 6. Observability (Minimal)

- **Log:** For each chat request: conversation_id, intent, steps, Ledger actions + latency per tool.
- **Optional:** Planner/Insight: token count (if using OpenAI/Anthropic); store in Redis or append to log.
- **Optional:** Correction rate = (reverts or edits) / (inserts) over last N days — for tuning confidence and UX.

---

## 7. India Features (Summary)

| Feature | Description |
|---------|-------------|
| UPI detection | Detect "UPI", "GPay", "PhonePe" in narration; tag or category. |
| EMI auto-detect | From liability.type or description "EMI"; link to affordability and monthly outflow. |
| FY (Apr–Mar) | Period param: "this_fy", "last_fy"; compute from current date. |
| 80C / SIP | Tag transactions as 80C-eligible or SIP for future tax view; optional. |

---

## 8. Step-by-Step Checklist

- [ ] **5.1** Implement validation module: validate_transaction (amount sign, date, currency), validate_liability (EMI vs outstanding).
- [ ] **5.2** Add CONFIDENCE_THRESHOLD; in Ledger (and optional Import path), require confirm when confidence < threshold; add confirm endpoint if not present.
- [ ] **5.3** Add observability: log agent/tool calls and latency; optional token and correction metrics.
- [ ] **5.4** UPI detection in normalizer or categorization; tag or category field.
- [ ] **5.5** EMI auto-detect from liabilities; feed into affordability.
- [ ] **5.6** FY periods: add period_type or date range for “this FY” / “last FY” in spending and reports.
- [ ] **5.7** (Optional) 80C/SIP tags for transactions or categories.
- [ ] **5.8** Categorization service: rule-based map + optional LLM for unknown merchant.
- [ ] **5.9** (Optional) Celery: worker, tasks for batch import or heavy reports.

---

## 9. Out of Scope for Phase 5

- Full tax computation (80C is tagging only).
- Multi-currency (Phase 5 assumes INR).
- Production auth (can stay dev/single-user).

---

## 10. Doc References

- REQUIREMENTS_BREAKDOWN.md — Phase 5 tasks 5.1–5.6.
- PHASE4_PLAN.md — Affordability, Insight.
- PHASE2_PLAN.md — Import, confidence on rows.
