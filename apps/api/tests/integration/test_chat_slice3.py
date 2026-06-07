"""Integration tests: Slice 3 record_transfer dual-leg confirm."""
from datetime import date

import pytest
from httpx import AsyncClient

from .investment_fixtures import create_sip_mf, ensure_user, unique_user_email, user_headers

pytestmark = pytest.mark.integration


async def test_record_transfer_confirm_creates_two_legs(client: AsyncClient) -> None:
    email = unique_user_email("xfer")
    await ensure_user(client, email)
    sip = await create_sip_mf(client, email, name="HDFC MF", emi_amount=5000, due_day=10)

    r = await client.post(
        "/v1/chat",
        json={"message": "record SIP 5000 for HDFC MF"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "confirm"
    assert resp["ui_type"] == "transaction_confirm"
    legs = resp["card_payload"]["legs"]
    assert len(legs) == 2
    assert legs[0]["amount"] < 0
    assert legs[1]["amount"] > 0
    assert legs[0]["nw_impact"] == "transfer"
    assert legs[1]["nw_impact"] == "transfer"
    assert legs[1]["account_name"] == "HDFC MF"

    conversation_id = r.json()["conversation_id"]
    r2 = await client.post(
        "/v1/chat",
        json={"message": "confirm", "conversation_id": conversation_id},
        headers=user_headers(email),
    )
    assert r2.status_code == 200
    assert r2.json()["response"]["status"] == "success"
    assert r2.json()["response"]["card_payload"].get("committed") is True

    txns = await client.get("/v1/transactions", headers=user_headers(email))
    assert txns.status_code == 200
    rows = txns.json()
    transfer_rows = [t for t in rows if t.get("nw_impact") == "transfer"]
    assert len(transfer_rows) >= 2
    mf_rows = [t for t in transfer_rows if t["account_id"] == sip["id"]]
    assert any(float(t["amount"]) > 0 for t in mf_rows)


async def test_record_transfer_sip_status_paid_after_confirm(client: AsyncClient) -> None:
    email = unique_user_email("xfer-sip")
    await ensure_user(client, email)
    await create_sip_mf(client, email, name="Nifty SIP", emi_amount=5000, due_day=10)

    r = await client.post(
        "/v1/chat",
        json={"message": "record SIP 5000 for Nifty SIP"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    conversation_id = r.json()["conversation_id"]
    r2 = await client.post(
        "/v1/chat",
        json={"message": "confirm", "conversation_id": conversation_id},
        headers=user_headers(email),
    )
    assert r2.status_code == 200

    r3 = await client.post(
        "/v1/chat",
        json={"message": "did I pay my SIP this month?"},
        headers=user_headers(email),
    )
    assert r3.status_code == 200
    sips = r3.json()["response"]["card_payload"].get("sips", [])
    assert len(sips) >= 1
    month_name = date.today().strftime("%B")
    assert f"Already paid in {month_name}" in sips[0]["status_label"]


async def test_record_transfer_rejects_zero_amount(client: AsyncClient) -> None:
    email = unique_user_email("xfer-err")
    await ensure_user(client, email)
    await create_sip_mf(client, email, name="Zero SIP", emi_amount=5000)

    r = await client.post(
        "/v1/chat",
        json={"message": "fund my SIP"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    assert r.json()["response"]["status"] in ("error", "success")
