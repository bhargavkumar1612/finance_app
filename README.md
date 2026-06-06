# Finance Copilot — Phase 0

AI-powered personal finance chat (India-focused). Phase 0: Dockerized backend, DB schema, manual expense API, placeholder chat.

## Guidelines

AI architecture, finance safety, and contribution rules: **[docs/AI_PRINCIPLES.md](docs/AI_PRINCIPLES.md)** (also [AGENTS.md](AGENTS.md) and [`.cursor/rules/`](.cursor/rules/) for coding agents).

## Stack

- **API:** FastAPI (Python 3.12)
- **DB:** PostgreSQL 16
- **Cache/state:** Redis 7
- **Migrations:** Alembic

## Run with Docker (recommended)

1. Start Docker Desktop (or ensure the Docker daemon is running).

2. Copy env and start services:

   ```bash
   cp .env.example .env
   # Optional: OpenRouter for planner + insight (see docs/LLM_SETUP.md)
   # LLM_PROVIDER=openrouter
   # OPENROUTER_API_KEY=sk-or-v1-...
   docker compose up --build
   ```

3. Open in browser:
   - **Next.js UI:** **http://localhost:3000** (rewrites `/v1/*` to the API)
   - **Legacy static UI:** **http://localhost:8000/static-ui**
   - **API docs:** **http://localhost:8000/docs**
   - **Health:** **http://localhost:8000/health**

4. On first run, the API container runs `alembic upgrade head` then starts uvicorn. DB and Redis are created by docker-compose.

### Rebuild after code or dependency changes

API code is volume-mounted and hot-reloads; the **frontend** uses a separate `node_modules` volume, so dependency or Dockerfile changes need a rebuild:

```bash
# Rebuild images and restart (keeps database data)
docker compose build frontend api
docker compose up -d --force-recreate

# If frontend still misses packages (e.g. "Can't resolve …"), refresh node_modules:
docker compose exec frontend npm ci

# Full clean rebuild (slowest; use when images act stale)
docker compose build --no-cache frontend api
docker compose up -d --force-recreate
```

## API (Phase 0)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| POST | `/v1/accounts` | Create account (type: bank \| credit_card \| wallet \| cash; optional `credit_limit` for cards) |
| GET | `/v1/accounts` | List accounts (includes transaction counts) |
| GET | `/v1/accounts/{id}` | Get one account |
| PUT | `/v1/accounts/{id}` | Update name, type, institution, credit limit |
| DELETE | `/v1/accounts/{id}` | Delete account (blocked if it has transactions or recurring bills) |
| POST | `/v1/transactions` | Create transaction (manual expense; debit = negative amount) |
| GET | `/v1/transactions` | List transactions (`?limit=`, default 500, max 2000) |
| PUT | `/v1/transactions/{id}` | Update transaction |
| DELETE | `/v1/transactions/{id}` | Delete one transaction |
| POST | `/v1/transactions/bulk-delete` | Delete many: `{ "ids": ["uuid", ...] }` |
| POST | `/v1/transactions/delete-all` | Delete all transactions for the current user |
| POST | `/v1/chat` | Chat (placeholder; returns echo + suggested actions) |

## Quick test (after `docker compose up`)

```bash
# Create an account
curl -s -X POST http://localhost:8000/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{"account_type":"cash","name":"Cash","institution":null}' | jq

# Use the returned account id in the next call
curl -s -X POST http://localhost:8000/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"amount":-450,"transaction_date":"2026-02-26","account_id":"<ACCOUNT_ID>","merchant":"Swiggy","category":"food"}' | jq

# Chat (placeholder)
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What did I spend last month?"}' | jq
```

## Project layout

```
apps/
  api/               # FastAPI + agents + ingestion (Python)
    app/
    alembic/
    tests/           # unit | integration | smoke
  web/               # Next.js UI (was frontend/)
e2e/                 # Playwright specs (smoke + regression)
data/                # CSV/PDF fixtures
docs/
scripts/             # init-db.sql, test-in-docker.sh
```

## Tests

With Docker stack running (`docker compose up`):

```bash
make test-unit          # apps/api/tests/unit — no DB for most tests
make test-integration   # API integration tests (Postgres + Redis)
make test-smoke         # health endpoint
./scripts/test-in-docker.sh   # all API tests in container

# Playwright e2e (UI + API via :3000)
cd e2e && npm install && npx playwright install chromium
make test-e2e           # all specs
make test-e2e-smoke     # @smoke tag only
```

See [docs/REGRESSION_TEST_PLAN.md](docs/REGRESSION_TEST_PLAN.md) for scenario IDs.

## Run without Docker (local dev)

1. Start PostgreSQL and Redis locally (or use Docker only for them).

2. Create a DB and set env:

   ```bash
   cp .env.example .env
   # Edit .env: DATABASE_URL and REDIS_URL for your local Postgres/Redis
   ```

3. Run migrations and API:

   ```bash
   cd apps/api
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   export PYTHONPATH=.
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

4. Frontend (separate terminal):

   ```bash
   cd apps/web && npm ci && npm run dev
   ```
