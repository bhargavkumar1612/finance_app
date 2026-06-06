"""Integration tests for hybrid net worth."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_net_worth_after_bank_credit(client: AsyncClient) -> None:
    acc = await client.post(
        "/v1/accounts",
        json={"account_type": "cash", "name": "Test Cash NW", "institution": None},
    )
    assert acc.status_code == 200
    account_id = acc.json()["id"]

    await client.post(
        "/v1/transactions",
        json={
            "amount": 100000,
            "transaction_date": "2026-05-01",
            "account_id": account_id,
            "merchant": "NEFT CR-SALARY-TEST",
            "category": "Income",
        },
    )

    r = await client.post("/v1/chat", json={"message": "what is my net worth?"})
    assert r.status_code == 200
    data = r.json()["response"]["data"]
    assert "net_worth" in data
    accounts = data.get("accounts", [])
    test_cash = next((a for a in accounts if a.get("name") == "Test Cash NW"), None)
    assert test_cash is not None
    assert float(test_cash.get("balance", 0)) >= 100000
