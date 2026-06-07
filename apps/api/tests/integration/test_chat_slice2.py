"""Integration tests: Slice 2 obligations hub chat."""
import pytest
from httpx import AsyncClient

from .investment_fixtures import create_sip_mf, ensure_user, unique_user_email, user_headers
from .obligation_fixtures import create_loan, create_recurring_bill_api, post_income

pytestmark = pytest.mark.integration


async def test_upcoming_obligations_card_sections(client: AsyncClient) -> None:
    email = unique_user_email("oblig")
    await ensure_user(client, email)
    await create_sip_mf(client, email, name="Nifty SIP", emi_amount=5000, due_day=10)
    await create_loan(client, email, name="Home Loan", emi_amount=25000, due_day=5)
    await create_recurring_bill_api(client, email, name="Rent", amount=-15000, due_day=1)

    r = await client.post(
        "/v1/chat",
        json={"message": "what's due this month?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == "obligation_list"
    sections = resp["card_payload"]["sections"]
    assert len(sections["sips"]) >= 1
    assert len(sections["loan_emis"]) >= 1
    assert len(sections["recurring_bills"]) >= 1
    assert resp["card_payload"]["total_monthly_commitments"] >= 45_000


async def test_loan_emi_summary_intent(client: AsyncClient) -> None:
    email = unique_user_email("emi")
    await ensure_user(client, email)
    await create_loan(client, email, emi_amount=18_000)

    r = await client.post(
        "/v1/chat",
        json={"message": "how much is my total EMI?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "obligation_list"
    assert resp["card_payload"]["total_monthly_emi"] == pytest.approx(18_000, abs=0.01)


async def test_affordability_includes_commitments(client: AsyncClient) -> None:
    email = unique_user_email("afford")
    await ensure_user(client, email)
    await post_income(client, email, 150_000)
    await create_loan(client, email, emi_amount=30_000)
    await create_sip_mf(client, email, emi_amount=10_000)

    r = await client.post(
        "/v1/chat",
        json={"message": "can I afford a new loan?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "affordability_result"
    commitments = resp["card_payload"]["commitments"]
    assert commitments["loan_emis"] == pytest.approx(30_000, abs=0.01)
    assert commitments["sip_emis"] == pytest.approx(10_000, abs=0.01)
    assert resp["card_payload"]["total_commitments"] >= 40_000


async def test_create_recurring_bill_confirm_flow(client: AsyncClient) -> None:
    email = unique_user_email("rbill")
    await ensure_user(client, email)

    r = await client.post(
        "/v1/chat",
        json={"message": "add recurring bill Netflix 499"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "confirm"
    assert resp["ui_type"] == "recurring_bill_confirm"
    assert resp["card_payload"]["name"] == "Netflix"
    assert resp["card_payload"]["amount"] == pytest.approx(499, abs=0.01)

    r2 = await client.post(
        "/v1/chat",
        json={"message": "confirm", "conversation_id": r.json()["conversation_id"]},
        headers=user_headers(email),
    )
    assert r2.status_code == 200
    resp2 = r2.json()["response"]
    assert resp2["status"] == "success"
    assert resp2["card_payload"].get("committed") is True

    bills = await client.get("/v1/recurring-bills", headers=user_headers(email))
    assert bills.status_code == 200
    names = [b["name"] for b in bills.json()]
    assert "Netflix" in names
