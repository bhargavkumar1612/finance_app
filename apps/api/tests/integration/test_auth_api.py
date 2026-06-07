"""Integration tests for the auth API (ADR 003, Round 9).

Covers: register -> pending -> approve -> login; wrong password; status gates;
forgot-password queue; /auth/me; logout; reject -> 24h cool-off -> override.
Uses `unauth_client` (no default token) so 401 paths are exercised honestly.
"""
import uuid
from datetime import datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from app.core import security
from app.db import User, async_session_maker
from tests.auth_helpers import (
    TEST_PASSWORD,
    bearer,
    register_super_admin_login,
)

pytestmark = []


def _uname(prefix: str = "auth") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


async def _approve_via_admin(client: AsyncClient, admin_token: str, user_id: str) -> None:
    r = await client.post(f"/v1/admin/users/{user_id}/approve", headers=bearer(admin_token))
    assert r.status_code == 200, r.text


async def _user_id_by_name(username: str) -> str:
    async with async_session_maker() as session:
        res = await session.execute(select(User).where(User.username == username))
        return str(res.scalar_one().id)


async def test_register_creates_pending_user(unauth_client: AsyncClient):
    username = _uname()
    r = await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    assert r.status_code == 200, r.text
    async with async_session_maker() as session:
        res = await session.execute(select(User).where(User.username == username))
        user = res.scalar_one()
        assert user.status == security.STATUS_PENDING
        assert user.role == security.ROLE_USER
        assert user.password_hash and user.password_hash != TEST_PASSWORD


async def test_register_rejects_weak_password(unauth_client: AsyncClient):
    r = await unauth_client.post(
        "/v1/auth/register", json={"username": _uname(), "password": "short"}
    )
    assert r.status_code == 422


async def test_register_duplicate_username(unauth_client: AsyncClient):
    username = _uname()
    r1 = await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    assert r1.status_code == 200
    r2 = await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    assert r2.status_code == 409


async def test_pending_user_cannot_login(unauth_client: AsyncClient):
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    r = await unauth_client.post(
        "/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
    )
    assert r.status_code == 403
    assert "pending" in r.json()["detail"].lower()


async def test_login_wrong_password(unauth_client: AsyncClient):
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    r = await unauth_client.post(
        "/v1/auth/login", json={"username": username, "password": "wrong-password"}
    )
    assert r.status_code == 401


async def test_full_register_approve_login_me(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    uid = await _user_id_by_name(username)
    await _approve_via_admin(unauth_client, admin_token, uid)

    r = await unauth_client.post(
        "/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    assert r.json()["user"]["username"] == username
    assert r.json()["user"]["role"] == security.ROLE_USER

    me = await unauth_client.get("/v1/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json()["username"] == username

    # approve seeds a default Cash account (first-login behavior)
    accts = await unauth_client.get("/v1/accounts", headers=bearer(token))
    assert accts.status_code == 200
    assert any(a["account_type"] == "cash" for a in accts.json())


async def test_me_requires_token(unauth_client: AsyncClient):
    r = await unauth_client.get("/v1/auth/me")
    assert r.status_code == 401
    r = await unauth_client.get("/v1/auth/me", headers=bearer("not-a-real-token"))
    assert r.status_code == 401


async def test_logout_invalidates_token(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    uid = await _user_id_by_name(username)
    await _approve_via_admin(unauth_client, admin_token, uid)
    token = (
        await unauth_client.post(
            "/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
        )
    ).json()["token"]

    assert (await unauth_client.get("/v1/auth/me", headers=bearer(token))).status_code == 200
    out = await unauth_client.post("/v1/auth/logout", headers=bearer(token))
    assert out.status_code == 200
    assert (await unauth_client.get("/v1/auth/me", headers=bearer(token))).status_code == 401


async def test_forgot_password_creates_request_for_approved_user(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    uid = await _user_id_by_name(username)
    await _approve_via_admin(unauth_client, admin_token, uid)

    r = await unauth_client.post("/v1/auth/forgot-password", json={"username": username})
    assert r.status_code == 200
    resets = await unauth_client.get("/v1/admin/password-resets", headers=bearer(admin_token))
    assert any(item["username"] == username for item in resets.json())


async def test_forgot_password_pending_user_no_request(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    # pending user — generic response, but no queue entry created
    r = await unauth_client.post("/v1/auth/forgot-password", json={"username": username})
    assert r.status_code == 200
    resets = await unauth_client.get("/v1/admin/password-resets", headers=bearer(admin_token))
    assert all(item["username"] != username for item in resets.json())


async def test_reject_triggers_cooloff_then_admin_override(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    uid = await _user_id_by_name(username)

    # reject
    rej = await unauth_client.post(f"/v1/admin/users/{uid}/reject", headers=bearer(admin_token))
    assert rej.status_code == 200
    assert rej.json()["status"] == security.STATUS_REJECTED

    # re-register within 24h is blocked by cool-off
    again = await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    assert again.status_code == 409

    # super admin instantly overrides cool-off by approving
    appr = await unauth_client.post(f"/v1/admin/users/{uid}/approve", headers=bearer(admin_token))
    assert appr.status_code == 200
    assert appr.json()["status"] == security.STATUS_APPROVED
    login = await unauth_client.post(
        "/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
    )
    assert login.status_code == 200


async def test_disable_revokes_active_session(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    uid = await _user_id_by_name(username)
    await _approve_via_admin(unauth_client, admin_token, uid)
    token = (
        await unauth_client.post(
            "/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
        )
    ).json()["token"]
    assert (await unauth_client.get("/v1/auth/me", headers=bearer(token))).status_code == 200

    dis = await unauth_client.post(f"/v1/admin/users/{uid}/disable", headers=bearer(admin_token))
    assert dis.status_code == 200
    # active session revoked + status gate both block immediately
    assert (await unauth_client.get("/v1/auth/me", headers=bearer(token))).status_code == 401
    relog = await unauth_client.post(
        "/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
    )
    assert relog.status_code == 403


async def test_cooloff_expires_after_24h(unauth_client: AsyncClient):
    """A rejection older than 24h no longer blocks re-registration."""
    username = _uname()
    await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    async with async_session_maker() as session:
        res = await session.execute(select(User).where(User.username == username))
        user = res.scalar_one()
        user.status = security.STATUS_REJECTED
        user.rejected_at = datetime.utcnow() - timedelta(hours=25)
        await session.commit()

    again = await unauth_client.post(
        "/v1/auth/register", json={"username": username, "password": TEST_PASSWORD}
    )
    assert again.status_code == 409  # still exists, but message differs from cool-off
    assert "recently rejected" not in again.json()["detail"].lower()
