"""Integration tests: Slice 1 investment/SIP chat with seeded accounts."""
from datetime import date

import pytest
from httpx import AsyncClient

from .investment_fixtures import (
    create_fd,
    create_mf_with_pnl,
    create_sip_mf,
    ensure_user,
    post_sip_installment,
    unique_user_email,
    user_headers,
)

pytestmark = pytest.mark.integration


async def test_portfolio_summary_matches_accounts_api(client: AsyncClient) -> None:
    email = unique_user_email("portfolio")
    await ensure_user(client, email)
    mf = await create_mf_with_pnl(client, email, invested=100_000, current=125_000)

    accounts = await client.get("/v1/accounts", headers=user_headers(email))
    assert accounts.status_code == 200
    mf_row = next(a for a in accounts.json() if a["id"] == mf["id"])

    r = await client.post(
        "/v1/chat",
        json={"message": "how are my investments?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == "investment_portfolio_dashboard"

    totals = resp["card_payload"]["totals"]
    assert totals["current"] == pytest.approx(mf_row["current_value"], rel=0, abs=0.01)
    assert totals["pnl_amount"] == pytest.approx(mf_row["pnl_amount"], rel=0, abs=0.01)
    assert len(resp["card_payload"]["footer_suggestions"]) >= 1


async def test_investment_allocation_from_holdings_not_legacy_asset(client: AsyncClient) -> None:
    email = unique_user_email("alloc")
    await ensure_user(client, email)
    await create_mf_with_pnl(client, email, name="Only MF", invested=50_000, current=60_000)

    r = await client.post(
        "/v1/chat",
        json={"message": "show my investment allocation"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "investment_pie_chart"
    assert resp["card_payload"]["total_invested"] > 0
    allocation = resp["card_payload"]["allocation"]
    assert any("mutual" in k.lower() or "fund" in k.lower() for k in allocation)


async def test_portfolio_pnl_drilldown_lists_holdings(client: AsyncClient) -> None:
    email = unique_user_email("pnl")
    await ensure_user(client, email)
    await create_mf_with_pnl(client, email, name="Winner Fund", invested=100_000, current=130_000)

    r = await client.post(
        "/v1/chat",
        json={"message": "show my most profitable investments"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "investment_pnl_bars"
    by_pct = resp["card_payload"]["by_pnl_percent"]
    assert len(by_pct) >= 1
    assert by_pct[0]["name"] == "Winner Fund"
    assert by_pct[0]["pnl_percent"] == pytest.approx(30.0, abs=0.1)


async def test_sip_status_already_paid_copy(client: AsyncClient) -> None:
    email = unique_user_email("sip-paid")
    await ensure_user(client, email)
    sip = await create_sip_mf(client, email, name="Paid SIP", due_day=5)
    today = date.today()
    await post_sip_installment(
        client,
        email,
        sip["id"],
        amount=5000,
        transaction_date=today.replace(day=min(5, 28)).isoformat(),
    )

    r = await client.post(
        "/v1/chat",
        json={"message": "did I pay my SIP this month?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "sip_schedule_summary"
    sips = resp["card_payload"]["sips"]
    assert len(sips) == 1
    assert f"Already paid in {today.strftime('%B')}" in sips[0]["status_label"]
    assert sips[0]["last_paid_on"] is not None


async def test_sip_status_pending_when_unpaid(client: AsyncClient) -> None:
    email = unique_user_email("sip-pending")
    await ensure_user(client, email)
    await create_sip_mf(client, email, name="Pending SIP", due_day=28)

    r = await client.post(
        "/v1/chat",
        json={"message": "sip status"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    sips = r.json()["response"]["card_payload"]["sips"]
    assert sips[0]["status_label"] == "Pending this month"


async def test_portfolio_includes_physical_asset(client: AsyncClient) -> None:
    email = unique_user_email("physical")
    await ensure_user(client, email)
    await create_mf_with_pnl(client, email, invested=50_000, current=60_000)
    asset = await client.post(
        "/v1/assets",
        json={"asset_type": "gold", "name": "Family gold", "current_value": 200_000},
        headers=user_headers(email),
    )
    assert asset.status_code in (200, 201)

    r = await client.post(
        "/v1/chat",
        json={"message": "how are my investments?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    payload = r.json()["response"]["card_payload"]
    assert payload["totals"]["current"] == pytest.approx(260_000, rel=0, abs=0.01)
    physical = payload.get("physical_assets", [])
    assert any(p["name"] == "Family gold" for p in physical)


async def test_fd_maturity_computed_in_chat(client: AsyncClient) -> None:
    email = unique_user_email("fd")
    await ensure_user(client, email)
    await create_fd(
        client,
        email,
        name="12M FD",
        start_date="2026-01-01",
        tenure_months=12,
    )

    r = await client.post(
        "/v1/chat",
        json={"message": "when does my FD mature?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "fd_maturity_summary"
    deposits = resp["card_payload"]["deposits"]
    assert deposits[0]["maturity_date"] == "2027-01-01"
    assert "2027-01-01" in resp["card_payload"]["message"]


async def test_missing_data_sip_nudge_after_due_day(client: AsyncClient) -> None:
    email = unique_user_email("sip-nudge")
    await ensure_user(client, email)
    today = date.today()
    if today.day < 5:
        pytest.skip("SIP nudge only fires when today.day >= due_day")
    await create_sip_mf(client, email, name="Late SIP", due_day=5)

    r = await client.post(
        "/v1/chat",
        json={"message": "what is my net worth?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    hints = r.json()["response"]["next_suggested_actions"]
    assert hints[0].startswith("Log SIP payment for Late SIP")


async def test_portfolio_persona_drilldown_in_suggested_actions(client: AsyncClient) -> None:
    email = unique_user_email("persona-actions")
    await ensure_user(client, email)
    await create_mf_with_pnl(client, email, name="Fund A", invested=100_000, current=120_000)
    await create_mf_with_pnl(client, email, name="Fund B", invested=50_000, current=55_000)

    r = await client.post(
        "/v1/chat",
        json={"message": "how are my investments?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    actions = r.json()["response"]["next_suggested_actions"]
    assert "Show P&L" in actions
