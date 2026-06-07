"""Test auth helpers (Round 9).

Email-only auto-create is gone; protected endpoints require a bearer token from
an *approved* user. These helpers register a user, approve it directly in the
DB (the super-admin step), log in, and cache the token by username so the many
existing `user_headers(email)` call sites keep working unchanged.
"""
from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from app.core import security
from app.db import User, async_session_maker
from app.services.user_provisioning import seed_default_cash_account

TEST_PASSWORD = "test-pass-123"

# username -> bearer token, populated by register_approve_login()
_token_cache: dict[str, str] = {}


async def _approve_in_db(username: str) -> None:
    """Approve a freshly-registered user and seed its default Cash account,
    mirroring what a super admin's approve action does."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one()
        user.status = security.STATUS_APPROVED
        user.role = security.ROLE_USER
        user.rejected_at = None
        await session.flush()
        await seed_default_cash_account(session, user.id)
        await session.commit()


async def register_approve_login(
    client: AsyncClient, username: str, password: str = TEST_PASSWORD
) -> str:
    """Register -> approve -> login. Returns a bearer token (cached per username)."""
    if username in _token_cache:
        return _token_cache[username]

    r = await client.post(
        "/v1/auth/register", json={"username": username, "password": password}
    )
    # 409 = already exists (persistent DB across runs); approve + login still work.
    assert r.status_code in (200, 409), r.text

    await _approve_in_db(username)

    r = await client.post(
        "/v1/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    _token_cache[username] = token
    return token


async def register_super_admin_login(
    client: AsyncClient, username: str, password: str = TEST_PASSWORD
) -> str:
    """Like register_approve_login but promotes the user to super_admin."""
    token = await register_approve_login(client, username, password)
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one()
        user.role = security.ROLE_SUPER_ADMIN
        await session.commit()
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
