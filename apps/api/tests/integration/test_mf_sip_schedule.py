"""Integration tests: mf_sip_schedule service via accounts API."""
import pytest
from httpx import AsyncClient

from .investment_fixtures import (
    create_sip_mf,
    ensure_user,
    post_sip_installment,
    unique_user_email,
    user_headers,
)

pytestmark = pytest.mark.integration


async def test_sip_schedule_counts_installments(client: AsyncClient) -> None:
    email = unique_user_email("schedule")
    await ensure_user(client, email)
    sip = await create_sip_mf(client, email, emi_amount=3000, tenure_months=6)
    account_id = sip["id"]

    await post_sip_installment(client, email, account_id, amount=3000, transaction_date="2026-01-05")
    await post_sip_installment(client, email, account_id, amount=3000, transaction_date="2026-02-05")

    r = await client.get("/v1/accounts", headers=user_headers(email))
    match = next(a for a in r.json() if a["id"] == account_id)
    assert match["sip_paid_count"] == 2
    assert match["sip_pending_count"] == 4
    assert len(match["payment_history"]) == 2
    assert match["payment_history"][-1]["date"] == "2026-02-05"
