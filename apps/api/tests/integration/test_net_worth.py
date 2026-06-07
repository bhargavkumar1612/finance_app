"""Integration tests for hybrid net worth."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_net_worth_after_bank_credit(client: AsyncClient) -> None:
    acc = await client.post(
        "/v1/accounts",
        json={"account_type": "cash", "name": "Test Cash NW Unique", "institution": None},
    )
    assert acc.status_code in (200, 201)
    account_id = acc.json()["id"]

    txn = await client.post(
        "/v1/transactions",
        json={
            "amount": 100000,
            "transaction_date": "2026-05-01",
            "account_id": account_id,
            "merchant": "NEFT CR-SALARY-TEST",
            "category": "Income",
        },
    )
    assert txn.status_code in (200, 201)

    r = await client.post("/v1/chat", json={"message": "what is my net worth?"})
    assert r.status_code == 200
    data = r.json()["response"]["data"]
    assert "net_worth" in data
    accounts = data.get("accounts", [])
    test_cash = next((a for a in accounts if a.get("name") == "Test Cash NW Unique"), None)
    assert test_cash is not None
    assert float(test_cash.get("balance", 0)) >= 100000


@pytest.mark.asyncio
async def test_net_worth_includes_opening_balance(client: AsyncClient) -> None:
    acc = await client.post(
        "/v1/accounts",
        json={
            "account_type": "bank",
            "name": "NW Opening Bank",
            "opening_balance": 75000,
        },
    )
    assert acc.status_code in (200, 201)

    r = await client.post("/v1/chat", json={"message": "what is my net worth?"})
    assert r.status_code == 200
    data = r.json()["response"]["data"]
    assert float(data.get("net_worth", 0)) >= 75000


@pytest.mark.asyncio
async def test_net_worth_includes_investment_holdings(client: AsyncClient) -> None:
    parent = await client.post(
        "/v1/accounts",
        json={"account_type": "bank", "name": "NW Investment Bank", "institution": "HDFC"},
    )
    assert parent.status_code in (200, 201)
    parent_id = parent.json()["id"]

    mf = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "NW Test MF",
            "institution": "Zerodha",
            "parent_account_id": parent_id,
            "opening_balance": 200000,
        },
    )
    assert mf.status_code in (200, 201)

    r = await client.post("/v1/chat", json={"message": "what is my net worth?"})
    assert r.status_code == 200
    data = r.json()["response"]["data"]
    assert float(data.get("investment_holdings", 0)) >= 200000
    assert float(data.get("net_worth", 0)) >= 200000
    accounts = data.get("accounts", [])
    mf_row = next((a for a in accounts if a.get("name") == "NW Test MF"), None)
    assert mf_row is not None
    assert mf_row.get("role") == "investment"
    assert float(mf_row.get("balance", 0)) >= 200000
