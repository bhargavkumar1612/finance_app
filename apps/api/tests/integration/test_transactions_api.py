"""Integration tests: transactions API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


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
    await client.post(
        "/v1/transactions",
        json={
            "amount": -99,
            "transaction_date": "2026-02-20",
            "account_id": account_id,
            "merchant": "Filter Test Shop",
            "category": "shopping",
        },
    )
    r = await client.get("/v1/transactions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    row = data[0]
    assert "account_name" in row
    assert "account_id" in row


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


async def test_delete_transaction(client: AsyncClient, account_id: str) -> None:
    r = await client.post(
        "/v1/transactions",
        json={
            "amount": -99,
            "transaction_date": "2026-02-26",
            "account_id": account_id,
            "merchant": "ToDelete",
        },
    )
    assert r.status_code in (200, 201)
    txn_id = r.json()["id"]

    r_del = await client.delete(f"/v1/transactions/{txn_id}")
    assert r_del.status_code == 204

    r_get = await client.get("/v1/transactions")
    ids = [t["id"] for t in r_get.json()]
    assert txn_id not in ids


async def test_bulk_delete_transactions(client: AsyncClient, account_id: str) -> None:
    ids = []
    for i in range(3):
        r = await client.post(
            "/v1/transactions",
            json={
                "amount": -(10 + i),
                "transaction_date": "2026-02-26",
                "account_id": account_id,
                "merchant": f"BulkDel{i}",
            },
        )
        assert r.status_code in (200, 201)
        ids.append(r.json()["id"])

    r = await client.post("/v1/transactions/bulk-delete", json={"ids": ids})
    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] == 3
    assert data["not_found"] == []

    r_list = await client.get("/v1/transactions")
    remaining = {t["id"] for t in r_list.json()}
    for tid in ids:
        assert tid not in remaining


async def test_delete_all_transactions(client: AsyncClient, account_id: str) -> None:
    for i in range(2):
        await client.post(
            "/v1/transactions",
            json={
                "amount": -(50 + i),
                "transaction_date": "2026-02-26",
                "account_id": account_id,
                "merchant": f"DeleteAll{i}",
            },
        )

    r = await client.post("/v1/transactions/delete-all", json={})
    assert r.status_code == 200
    assert r.json()["deleted"] >= 2

    r_list = await client.get("/v1/transactions")
    assert r_list.json() == []
