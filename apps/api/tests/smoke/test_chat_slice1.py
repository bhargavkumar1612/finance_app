"""Smoke tests: Slice 1 chat intents respond without error."""
import pytest
from httpx import AsyncClient

from tests.integration.investment_fixtures import ensure_user, unique_user_email, user_headers  # noqa: E402 — smoke imports integration helpers

pytestmark = pytest.mark.smoke


@pytest.mark.parametrize(
    "message,expected_ui",
    [
        ("how are my investments?", "investment_portfolio_dashboard"),
        ("show my investment allocation", "investment_pie_chart"),
        ("did I pay my SIP this month?", "sip_schedule_summary"),
        ("when does my FD mature?", "message_only"),  # no FD seeded → message_only
    ],
)
async def test_slice1_chat_intents_smoke(
    client: AsyncClient,
    message: str,
    expected_ui: str,
) -> None:
    email = unique_user_email("smoke")
    await ensure_user(client, email)
    r = await client.post(
        "/v1/chat",
        json={"message": message},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == expected_ui
