"""Integration tests: accounts API."""
import pytest
from httpx import AsyncClient


async def test_create_account(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "wallet", "name": "Test Wallet", "institution": "Test"},
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_type"] == "wallet"
    assert data["name"] == "Test Wallet"
    assert "id" in data
    assert "user_id" in data


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
