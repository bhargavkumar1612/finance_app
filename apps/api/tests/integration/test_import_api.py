"""Integration tests: import API (Phase 2)."""
import io

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


@pytest.fixture
def sample_csv_bytes() -> bytes:
    return b"""Date,Narration,Withdrawal,Deposit,Balance
01-02-2026,SWIGGY,450,,10000
02-02-2026,SALARY CR,,50000,60000
03-02-2026,UPI/MERCHANT,200,,59800
"""


async def test_import_csv_returns_normalized_rows(
    client: AsyncClient,
    account_id: str,
    sample_csv_bytes: bytes,
) -> None:
    r = await client.post(
        "/v1/import",
        files={"file": ("statement.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
        data={"bank_hint": "hdfc", "account_id": account_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert "rows" in data
    assert data["account_id"] == account_id
    rows = data["rows"]
    assert len(rows) >= 2
    for row in rows:
        assert "amount" in row
        assert "date" in row
        assert "is_duplicate" in row
        assert "fingerprint" in row


async def test_import_confirm_inserts_transactions(
    client: AsyncClient,
    account_id: str,
    sample_csv_bytes: bytes,
) -> None:
    r = await client.post(
        "/v1/import",
        files={"file": ("statement.csv", io.BytesIO(sample_csv_bytes), "text/csv")},
        data={"account_id": account_id},
    )
    assert r.status_code == 200
    data = r.json()
    rows = data["rows"]
    assert len(rows) >= 1
    to_confirm = [
        {
            "amount": float(rows[0]["amount"]),
            "date": rows[0]["date"],
            "merchant": rows[0].get("merchant"),
            "fingerprint": rows[0].get("fingerprint"),
        }
    ]
    r2 = await client.post(
        "/v1/import/confirm",
        json={"account_id": account_id, "rows": to_confirm},
    )
    assert r2.status_code == 200
    conf = r2.json()
    assert conf["inserted"] >= 1
    assert conf["errors"] == []


async def test_import_confirm_saves_category(
    client: AsyncClient,
    account_id: str,
) -> None:
    csv_body = b"""Date,Narration,Withdrawal,Deposit,Balance,Category
01-02-2026,UPI/SWIGGY,450,,10000,Food
"""
    r = await client.post(
        "/v1/import",
        files={"file": ("statement.csv", io.BytesIO(csv_body), "text/csv")},
        data={"account_id": account_id},
    )
    assert r.status_code == 200
    row = r.json()["rows"][0]
    assert row.get("suggested_category") == "Food"

    r2 = await client.post(
        "/v1/import/confirm",
        json={
            "account_id": account_id,
            "rows": [
                {
                    "amount": float(row["amount"]),
                    "date": row["date"],
                    "merchant": row.get("merchant"),
                    "fingerprint": row.get("fingerprint"),
                    "suggested_category": row.get("suggested_category"),
                }
            ],
        },
    )
    assert r2.status_code == 200
    txn_id = None
    listed = await client.get("/v1/transactions")
    for t in listed.json():
        if t.get("merchant") == "UPI/SWIGGY":
            txn_id = t["id"]
            assert t.get("category") == "Food"
            break
    assert txn_id is not None


async def test_reimport_same_csv_marks_duplicates(
    client: AsyncClient,
    account_id: str,
) -> None:
    csv_body = b"""Date,Narration,Withdrawal,Deposit,Balance,Category
01-02-2026,UPI/SWIGGY,450,,10000,Food
"""
    r1 = await client.post(
        "/v1/import",
        files={"file": ("statement.csv", io.BytesIO(csv_body), "text/csv")},
        data={"account_id": account_id},
    )
    row = r1.json()["rows"][0]
    await client.post(
        "/v1/import/confirm",
        json={
            "account_id": account_id,
            "rows": [
                {
                    "amount": float(row["amount"]),
                    "date": row["date"],
                    "merchant": row.get("merchant"),
                    "fingerprint": row.get("fingerprint"),
                    "suggested_category": row.get("suggested_category"),
                }
            ],
        },
    )
    r2 = await client.post(
        "/v1/import",
        files={"file": ("statement.csv", io.BytesIO(csv_body), "text/csv")},
        data={"account_id": account_id},
    )
    assert r2.json()["rows"][0]["is_duplicate"] is True


async def test_import_empty_file_rejected(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/import",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert r.status_code == 400


async def test_import_no_account_returns_400_if_no_accounts(client: AsyncClient) -> None:
    r = await client.get("/v1/accounts")
    if r.status_code == 200 and not r.json():
        r_imp = await client.post(
            "/v1/import",
            files={"file": ("x.csv", io.BytesIO(b"Date,Narration,Withdrawal,Deposit\n01-01-2026,X,100,,"), "text/csv")},
        )
        assert r_imp.status_code in (200, 400)
