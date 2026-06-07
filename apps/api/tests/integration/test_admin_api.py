"""Integration tests for the super admin API (ADR 003, Round 9).

Covers authorization gating, stats, signup lifecycle, password-reset resolve,
and an exhaustive orphan-free hard delete across every user-owned table.
"""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import func, select

from app.core import security
from app.db import (
    Account,
    Asset,
    AuthToken,
    ChatMessage,
    ChatSession,
    ImportFingerprint,
    PasswordResetRequest,
    RecurringBill,
    Transaction,
    User,
    async_session_maker,
)
from app.db.models import UserFinancialPersona
from tests.auth_helpers import (
    TEST_PASSWORD,
    bearer,
    register_approve_login,
    register_super_admin_login,
)


def _uname(prefix: str = "adm") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


async def _user_id(username: str) -> str:
    async with async_session_maker() as session:
        res = await session.execute(select(User).where(User.username == username))
        return str(res.scalar_one().id)


async def test_admin_routes_require_super_admin(unauth_client: AsyncClient):
    # no token
    assert (await unauth_client.get("/v1/admin/stats")).status_code == 401
    # normal approved user is forbidden
    user_token = await register_approve_login(unauth_client, _uname("plain"))
    r = await unauth_client.get("/v1/admin/stats", headers=bearer(user_token))
    assert r.status_code == 403


async def test_stats_and_pending_signups(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    pending_name = _uname("pending")
    await unauth_client.post(
        "/v1/auth/register", json={"username": pending_name, "password": TEST_PASSWORD}
    )

    stats = await unauth_client.get("/v1/admin/stats", headers=bearer(admin_token))
    assert stats.status_code == 200
    body = stats.json()
    assert body["user_count"] >= 2
    assert body["pending_signups"] >= 1

    pend = await unauth_client.get("/v1/admin/pending-signups", headers=bearer(admin_token))
    assert pend.status_code == 200
    assert any(u["username"] == pending_name for u in pend.json())


async def test_users_list_paginated(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    r = await unauth_client.get("/v1/admin/users?limit=5&offset=0", headers=bearer(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert "total" in body and isinstance(body["users"], list)
    assert len(body["users"]) <= 5


async def test_users_search_by_username(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    needle = f"findme-{uuid.uuid4().hex[:8]}"
    await register_approve_login(unauth_client, needle)

    hit = await unauth_client.get(f"/v1/admin/users?q={needle}", headers=bearer(admin_token))
    assert hit.status_code == 200
    body = hit.json()
    assert body["total"] >= 1
    assert any(u["username"] == needle for u in body["users"])

    miss = await unauth_client.get(
        "/v1/admin/users?q=zzz-no-such-user-zzz", headers=bearer(admin_token)
    )
    assert miss.json()["total"] == 0


async def test_disable_then_enable(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    uname = _uname("toggle")
    await register_approve_login(unauth_client, uname)
    uid = await _user_id(uname)

    dis = await unauth_client.post(f"/v1/admin/users/{uid}/disable", headers=bearer(admin_token))
    assert dis.status_code == 200 and dis.json()["status"] == security.STATUS_DISABLED

    en = await unauth_client.post(f"/v1/admin/users/{uid}/enable", headers=bearer(admin_token))
    assert en.status_code == 200 and en.json()["status"] == security.STATUS_APPROVED


async def test_admin_cannot_delete_self(unauth_client: AsyncClient):
    admin_name = _uname("admin")
    admin_token = await register_super_admin_login(unauth_client, admin_name)
    uid = await _user_id(admin_name)
    r = await unauth_client.delete(f"/v1/admin/users/{uid}", headers=bearer(admin_token))
    assert r.status_code == 400


async def test_password_reset_resolve_flow(unauth_client: AsyncClient):
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    uname = _uname("resetme")
    await register_approve_login(unauth_client, uname)

    # user forgets password
    await unauth_client.post("/v1/auth/forgot-password", json={"username": uname})
    resets = await unauth_client.get("/v1/admin/password-resets", headers=bearer(admin_token))
    req = next(item for item in resets.json() if item["username"] == uname)

    new_pw = "brand-new-pass-9"
    res = await unauth_client.post(
        f"/v1/admin/password-resets/{req['id']}/resolve",
        json={"new_password": new_pw},
        headers=bearer(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["new_password"] == new_pw  # returned once for offline share

    # old password no longer works, new one does
    assert (
        await unauth_client.post(
            "/v1/auth/login", json={"username": uname, "password": TEST_PASSWORD}
        )
    ).status_code == 401
    assert (
        await unauth_client.post(
            "/v1/auth/login", json={"username": uname, "password": new_pw}
        )
    ).status_code == 200

    # request is no longer open
    resets2 = await unauth_client.get("/v1/admin/password-resets", headers=bearer(admin_token))
    assert all(item["id"] != req["id"] for item in resets2.json())


async def _count_for_user(model, user_id: uuid.UUID) -> int:
    async with async_session_maker() as session:
        return (
            await session.scalar(
                select(func.count()).select_from(model).where(model.user_id == user_id)
            )
        ) or 0


async def test_hard_delete_cascades_all_user_data(unauth_client: AsyncClient):
    """Seed a row in EVERY user-owned table, then assert delete leaves no orphans."""
    admin_token = await register_super_admin_login(unauth_client, _uname("admin"))
    uname = _uname("victim")
    await register_approve_login(unauth_client, uname)
    uid = uuid.UUID(await _user_id(uname))

    async with async_session_maker() as session:
        # accounts incl. self-referential parent link
        parent = Account(user_id=uid, account_type="bank", name="Parent Bank")
        session.add(parent)
        await session.flush()
        child = Account(
            user_id=uid, account_type="credit_card", name="CC", parent_account_id=parent.id
        )
        session.add(child)
        await session.flush()

        bill = RecurringBill(
            user_id=uid, account_id=parent.id, name="Rent", amount=Decimal("1000"), frequency="monthly"
        )
        session.add(bill)
        await session.flush()

        txn = Transaction(
            user_id=uid,
            account_id=parent.id,
            amount=Decimal("-50"),
            transaction_date=date(2026, 1, 1),
            recurring_bill_id=bill.id,
        )
        session.add(txn)
        session.add(Asset(user_id=uid, asset_type="gold", name="Gold", current_value=Decimal("500")))
        session.add(ImportFingerprint(user_id=uid, fingerprint="fp-" + uuid.uuid4().hex))
        session.add(UserFinancialPersona(user_id=uid, body="persona"))
        session.add(PasswordResetRequest(user_id=uid, status=security.RESET_OPEN))
        session.add(
            AuthToken(
                user_id=uid,
                token_hash="hash-" + uuid.uuid4().hex,
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        chat = ChatSession(user_id=uid, title="Chat")
        session.add(chat)
        await session.flush()
        session.add(ChatMessage(session_id=chat.id, role="user", text="hi"))
        await session.commit()

    # sanity: rows exist (>=2 here: 1 seeded Cash on approval + 2 created above)
    assert await _count_for_user(Account, uid) >= 2
    assert await _count_for_user(Transaction, uid) == 1

    # delete via admin API
    r = await unauth_client.delete(f"/v1/admin/users/{uid}", headers=bearer(admin_token))
    assert r.status_code == 200, r.text

    # zero orphans across every user-owned table
    for model in (
        Account,
        Transaction,
        RecurringBill,
        Asset,
        ImportFingerprint,
        UserFinancialPersona,
        PasswordResetRequest,
        AuthToken,
        ChatSession,
    ):
        assert await _count_for_user(model, uid) == 0, f"orphans left in {model.__tablename__}"

    async with async_session_maker() as session:
        # chat messages gone (no user_id column — check via session join)
        msg_count = await session.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id.in_(select(ChatSession.id).where(ChatSession.user_id == uid)))
        )
        assert (msg_count or 0) == 0
        # user gone
        assert await session.get(User, uid) is None
