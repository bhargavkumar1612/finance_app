"""Smoke tests: Slice 2 obligations hub intents respond without error."""
import pytest
from httpx import AsyncClient

from tests.integration.investment_fixtures import ensure_user, unique_user_email, user_headers

pytestmark = pytest.mark.smoke


@pytest.mark.parametrize(
    "message,expected_ui",
    [
        ("what's due this month?", "obligation_list"),
        ("how much is my total EMI?", "obligation_list"),
        ("can I afford a new loan?", "affordability_result"),
        ("what's my safe EMI?", "affordability_result"),
    ],
)
async def test_slice2_chat_intents_smoke(
    client: AsyncClient,
    message: str,
    expected_ui: str,
) -> None:
    email = unique_user_email("s2-smoke")
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
