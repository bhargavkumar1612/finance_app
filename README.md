# Finance Copilot — Phase 0

AI-powered personal finance chat (India-focused). Phase 0: Dockerized backend, DB schema, manual expense API, placeholder chat.

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
   docker compose up --build
   ```

3. Open in browser:
   - **UI:** **http://localhost:8000** — accounts, transactions, chat, import CSV
   - **API docs:** **http://localhost:8000/docs**
   - **Health:** **http://localhost:8000/health**

4. On first run, the API container runs `alembic upgrade head` then starts uvicorn. DB and Redis are created by docker-compose.

## API (Phase 0)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| POST | `/v1/accounts` | Create account (type: bank \| credit_card \| wallet \| cash) |
| GET | `/v1/accounts` | List accounts |
| POST | `/v1/transactions` | Create transaction (manual expense; debit = negative amount) |
| GET | `/v1/transactions` | List transactions |
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

## Run without Docker (local dev)

1. Start PostgreSQL and Redis locally (or use Docker only for them).

2. Create a DB and set env:

   ```bash
   cp .env.example .env
   # Edit .env: DATABASE_URL and REDIS_URL for your local Postgres/Redis
   ```

3. Run migrations and API:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

Optional: set `DEFAULT_USER_ID` in `.env` to a UUID to pin the “current user” (otherwise the first request creates a dev user).

## Project layout (Phase 0)

```
app/
  agents/          # Planner, Ledger, Insight, UI Guide (Phase 1)
  api/             # accounts, transactions, chat
  core/            # config, schemas (data contracts)
  db/               # models, database, migrations
  ingestion/        # csv_parsers, pdf_parsers (Phase 2)
  services/        # import, categorization (Phase 2+)
alembic/
scripts/           # entrypoint.sh, init-db.sql
```

## Integration tests

Requires the stack to be running (e.g. `docker compose up` in another terminal).

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests cover: health, accounts (create/list), transactions (create/list), chat (add expense, net worth, spending, unknown intent).

## Next (Phase 1)

- Orchestrator, Planner agent, Ledger agent tools
- Redis conversation state
- Structured chat response from orchestrator
