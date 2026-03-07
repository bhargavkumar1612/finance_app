"""
Integration test fixtures. Tests hit real app with real DB and Redis.
Use AsyncClient + session-scoped event loop so async DB and tests share one loop.
Run with: pytest tests/ (requires Docker stack or local Postgres + Redis).
"""
import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
async def account_id(client: AsyncClient) -> str:
    """Ensure at least one account exists; return its id for use in transactions/chat."""
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "cash", "name": "Cash", "institution": None},
    )
    if r.status_code in (200, 201):
        return r.json()["id"]
    r = await client.get("/v1/accounts")
    r.raise_for_status()
    accounts = r.json()
    assert accounts, "Need at least one account; POST /v1/accounts first."
    return accounts[0]["id"]
