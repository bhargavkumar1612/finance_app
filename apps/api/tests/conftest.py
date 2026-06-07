"""
Integration test fixtures. Tests hit real app with real DB and Redis.
Use AsyncClient + session-scoped event loop so async DB and tests share one loop.
Run with: pytest tests/ (requires Docker stack or local Postgres + Redis).

Auth (Round 9): the legacy email-only auto-create is gone. The default `client`
is authenticated as an approved test user via a bearer token; tests that act as
other users pass `user_headers(email)` per request (httpx overrides the default
header). `unauth_client` has no token, for testing 401 paths.
"""
import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.auth_helpers import bearer, register_approve_login

DEFAULT_TEST_USER = "default-test-user"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client():
    """Authenticated client (approved default user) for general API tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = await register_approve_login(ac, DEFAULT_TEST_USER)
        ac.headers.update(bearer(token))
        yield ac


@pytest.fixture(scope="session")
async def unauth_client():
    """Client with no Authorization header — for 401/auth-flow tests."""
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
