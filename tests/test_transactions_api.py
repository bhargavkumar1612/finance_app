"""Integration tests: transactions API."""
import pytest
from httpx import AsyncClient


async def test_create_transaction(client: AsyncClient, account_id: str) -> None:
    r = await client.post(
        "/v1/transactions",
        json={
            "amount": -450,
            "transaction_date": "2026-02-26",
            "account_id": account_id,
            "merchant": "Swiggy",
            "category": "food",
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert float(data["amount"]) == -450
    assert data["merchant"] == "Swiggy"
    assert data["source"] == "manual"
    assert "id" in data


async def test_list_transactions(client: AsyncClient, account_id: str) -> None:
    r = await client.get("/v1/transactions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


async def test_create_transaction_rejects_unknown_account(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/transactions",
        json={
            "amount": -100,
            "transaction_date": "2026-02-26",
            "account_id": "00000000-0000-0000-0000-000000000000",
            "merchant": "X",
        },
    )
    assert r.status_code == 404
