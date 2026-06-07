"""Shared helpers for investment/SIP chat integration tests."""
from __future__ import annotations

import uuid

from httpx import AsyncClient


def unique_user_email(prefix: str = "slice1") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@test.local"


def user_headers(email: str) -> dict[str, str]:
    return {"X-User-Email": email}


async def ensure_user(client: AsyncClient, email: str) -> None:
    r = await client.post("/v1/login", json={"email": email})
    assert r.status_code == 200


async def create_bank(
    client: AsyncClient,
    email: str,
    name: str = "Test Bank",
) -> str:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "bank", "name": name, "institution": "Test"},
        headers=user_headers(email),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def create_mf_with_pnl(
    client: AsyncClient,
    email: str,
    *,
    name: str = "Index Fund",
    invested: float = 100_000,
    current: float = 125_000,
    bank_name: str = "MF Bank",
) -> dict:
    parent_id = await create_bank(client, email, bank_name)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": name,
            "parent_account_id": parent_id,
            "invested_amount": invested,
            "current_value": current,
        },
        headers=user_headers(email),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


async def create_sip_mf(
    client: AsyncClient,
    email: str,
    *,
    name: str = "Nifty SIP",
    emi_amount: float = 5000,
    due_day: int = 10,
    start_date: str = "2025-01-10",
    tenure_months: int = 12,
    bank_name: str = "SIP Bank",
) -> dict:
    parent_id = await create_bank(client, email, bank_name)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": name,
            "parent_account_id": parent_id,
            "investment_mode": "sip",
            "emi_amount": emi_amount,
            "due_day": due_day,
            "start_date": start_date,
            "tenure_months": tenure_months,
        },
        headers=user_headers(email),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


async def create_fd(
    client: AsyncClient,
    email: str,
    *,
    name: str = "HDFC FD",
    start_date: str = "2026-01-01",
    tenure_months: int = 12,
    opening_balance: float = 500_000,
    bank_name: str = "FD Bank",
) -> dict:
    parent_id = await create_bank(client, email, bank_name)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "fixed_deposit",
            "name": name,
            "parent_account_id": parent_id,
            "opening_balance": opening_balance,
            "start_date": start_date,
            "tenure_months": tenure_months,
        },
        headers=user_headers(email),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


async def post_sip_installment(
    client: AsyncClient,
    email: str,
    account_id: str,
    *,
    amount: float,
    transaction_date: str,
) -> None:
    r = await client.post(
        "/v1/transactions",
        json={
            "amount": amount,
            "transaction_date": transaction_date,
            "account_id": account_id,
            "category": "Investments",
            "nw_impact": "transfer",
        },
        headers=user_headers(email),
    )
    assert r.status_code in (200, 201), r.text
