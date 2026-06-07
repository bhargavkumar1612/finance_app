# Handoff — Slice 1 complete (Investment + SIP chat)

**Status:** Done · tested · **uncommitted**  
**Repo:** `finances_app`  
**PRD:** [AI_CHAT_FEATURES_PRD.md](../AI_CHAT_FEATURES_PRD.md) § Slice 1

## Summary

Chat layer for investments is implemented end-to-end: portfolio dashboard, allocation, P&L drill-down, SIP status, FD maturity, persona v1 (rules), keyword routing for `LLM_PROVIDER=none`.

## Key paths

| Area | Path |
|------|------|
| Service | `apps/api/app/services/portfolio_summary.py`, `persona_rules.py` |
| Agents | `planner.py`, `ledger_agent.py`, `ui_guide.py` |
| Cards | `InvestmentPortfolioDashboardCard`, `InvestmentPnlBarsCard`, `SipScheduleSummaryCard`, `FdMaturityCard` |
| Tests | `test_chat_slice1.py`, `test_planner_slice1.py`, e2e `REG-C010`–`C012` |

## Test report (last green run)

| Layer | Passed |
|-------|--------|
| API unit | 90 |
| API integration | 88 |
| API smoke | 5 |
| Web Vitest | 80 |
| E2E (desktop + mobile) | 8 |
| **Total** | **271** |

## Before Slice 2

```bash
git add -A && git commit -m "feat(chat): Slice 1 investment + SIP chat with tests"
```

## Next

[slice2-obligations.md](./slice2-obligations.md)
