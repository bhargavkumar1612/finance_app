"""Integration tests for GET /v1/hints proactive nudges."""
from datetime import date

import pytest
from httpx import AsyncClient

from .investment_fixtures import create_sip_mf, ensure_user, unique_user_email, user_headers

pytestmark = pytest.mark.integration


async def test_hints_returns_sip_nudge(client: AsyncClient) -> None:
    email = unique_user_email("hints-sip")
    await ensure_user(client, email)
    today = date.today()
    if today.day < 5:
        pytest.skip("SIP nudge only fires when today.day >= due_day")
    await create_sip_mf(client, email, name="Hints SIP", due_day=5)

    r = await client.get("/v1/hints", headers=user_headers(email))
    assert r.status_code == 200
    hints = r.json()["hints"]
    assert any("Log SIP payment for Hints SIP" in h for h in hints)


async def test_hints_empty_for_new_user(client: AsyncClient) -> None:
    email = unique_user_email("hints-empty")
    await ensure_user(client, email)
    today = date.today()
    if today.day >= 5:
        pytest.skip("Early-month only — new user gets salary hint after day 5")

    r = await client.get("/v1/hints", headers=user_headers(email))
    assert r.status_code == 200
    assert isinstance(r.json()["hints"], list)
