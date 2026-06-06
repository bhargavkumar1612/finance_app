"""Integration tests: accounts API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def _create_primary_bank(client: AsyncClient, name: str = "Test Bank") -> str:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "bank", "name": name, "institution": "Test"},
    )
    assert r.status_code in (200, 201)
    return r.json()["id"]


async def test_create_wallet_requires_parent(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "wallet", "name": "Test Wallet", "institution": "Test"},
    )
    assert r.status_code == 400


async def test_create_wallet_with_parent(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "wallet",
            "name": "Test Wallet",
            "institution": "Test",
            "parent_account_id": parent_id,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_type"] == "wallet"
    assert data["name"] == "Test Wallet"
    assert data["parent_account_id"] == parent_id


async def test_create_account_invalid_type(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "invalid", "name": "X", "institution": None},
    )
    assert r.status_code == 400


async def test_list_accounts(client: AsyncClient) -> None:
    r = await client.get("/v1/accounts")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    for acc in data:
        assert "id" in acc and "name" in acc and "account_type" in acc


async def test_create_credit_card_with_limit(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "HDFC Savings")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "credit_card",
            "name": "HDFC Regalia",
            "institution": "HDFC",
            "credit_limit": 250000,
            "parent_account_id": parent_id,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["credit_limit"] == 250000
    account_id = data["id"]

    r2 = await client.put(
        f"/v1/accounts/{account_id}",
        json={"name": "HDFC Regalia Gold", "credit_limit": 300000},
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "HDFC Regalia Gold"
    assert r2.json()["credit_limit"] == 300000

    r3 = await client.delete(f"/v1/accounts/{account_id}")
    assert r3.status_code == 204


async def test_delete_account_with_transactions_blocked(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Blocked Delete Bank")
    acc = await client.post(
        "/v1/accounts",
        json={
            "account_type": "wallet",
            "name": "Blocked Delete",
            "parent_account_id": parent_id,
        },
    )
    assert acc.status_code in (200, 201)
    account_id = acc.json()["id"]
    await client.post(
        "/v1/transactions",
        json={
            "amount": -100,
            "transaction_date": "2026-01-15",
            "account_id": account_id,
        },
    )
    r = await client.delete(f"/v1/accounts/{account_id}")
    assert r.status_code == 409
