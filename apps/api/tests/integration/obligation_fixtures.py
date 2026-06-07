"""Shared helpers for Slice 2 obligations chat integration tests."""
from __future__ import annotations

from httpx import AsyncClient

from .investment_fixtures import create_bank, create_sip_mf, ensure_user, user_headers


async def create_loan(
    client: AsyncClient,
    email: str,
    *,
    name: str = "Home Loan",
    emi_amount: float = 25_000,
    due_day: int = 5,
    bank_name: str = "Loan Bank",
) -> dict:
    parent_id = await create_bank(client, email, bank_name)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "name": name,
            "parent_account_id": parent_id,
            "emi_amount": emi_amount,
            "due_day": due_day,
            "start_date": "2020-01-05",
            "sanctioned_amount": 5_000_000,
            "tenure_months": 240,
        },
        headers=user_headers(email),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


async def create_recurring_bill_api(
    client: AsyncClient,
    email: str,
    *,
    name: str = "Rent",
    amount: float = -15_000,
    due_day: int = 1,
    bank_name: str = "Bill Bank",
) -> dict:
    account_id = await create_bank(client, email, bank_name)
    r = await client.post(
        "/v1/recurring-bills",
        json={
            "account_id": account_id,
            "name": name,
            "amount": amount,
            "frequency": "monthly",
            "due_day": due_day,
            "category": "Housing",
        },
        headers=user_headers(email),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


async def post_income(
    client: AsyncClient,
    email: str,
    amount: float,
    *,
    bank_name: str = "Salary Bank",
) -> None:
    account_id = await create_bank(client, email, bank_name)
    r = await client.post(
        "/v1/transactions",
        json={
            "account_id": account_id,
            "amount": amount,
            "transaction_date": "2026-05-01",
            "merchant": "Salary",
            "category": "Income",
        },
        headers=user_headers(email),
    )
    assert r.status_code in (200, 201), r.text
