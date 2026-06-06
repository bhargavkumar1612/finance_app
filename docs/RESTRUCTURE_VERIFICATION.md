# Restructure verification — 2026-06-07

Monorepo move to `apps/api`, `apps/web`, and `e2e/` completed.

## API tests (Docker)

```
39 passed — apps/api/tests (unit + integration + smoke)
```

Commands:

```bash
make test-unit
make test-integration
make test-smoke
```

## Playwright e2e (sequential then full)

| Spec | REG IDs | Result |
|------|---------|--------|
| `specs/smoke/login.spec.ts` | REG-A002 | PASS |
| `specs/smoke/health.spec.ts` | REG-A008, REG-B001 | PASS |
| `specs/regression/accounts-credit-card.spec.ts` | REG-F001, F011, F012 | PASS |
| `specs/regression/chat-confirm-expense.spec.ts` | REG-C001–C003 | PASS |
| `specs/regression/import-hdfc.spec.ts` | REG-I001, J001 | PASS |
| `specs/regression/transactions-filters.spec.ts` | REG-H002, H003 | PASS |
| **Full suite (7 tests)** | — | **PASS (5.9s)** |

## Fixes applied during e2e hardening

- `TransactionConfirmCard.module.css` — invalid `.summaryText` selector (blocked Next.js build)
- Shared helpers: Enter-key login, `force` clicks, table-scoped assertions
- Confirm/Cancel buttons scoped to `.btn-success` / `.btn-ghost` (avoid suggestion chips)
- Import modal uses `#import-file-input` and compact-mode copy
- CC parent dropdown: exact label `Name (Bank)`
- Backend: `import_service` missing `select` import; planner keyword fallbacks for offline LLM

## Run e2e

```bash
docker compose up -d
cd e2e && npm install && npx playwright install chromium
make test-e2e
```
