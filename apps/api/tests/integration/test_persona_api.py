"""Integration tests: financial persona API."""
import pytest
from httpx import AsyncClient

from .investment_fixtures import ensure_user, unique_user_email, user_headers

pytestmark = pytest.mark.integration


async def test_persona_round_trip(client: AsyncClient) -> None:
    email = unique_user_email("persona")
    await ensure_user(client, email)

    get0 = await client.get("/v1/persona", headers=user_headers(email))
    assert get0.status_code == 200
    assert get0.json()["body"] == ""

    put = await client.put(
        "/v1/persona",
        json={"body": "SIP-heavy. Salary on 1st."},
        headers=user_headers(email),
    )
    assert put.status_code == 200
    assert put.json()["body"] == "SIP-heavy. Salary on 1st."

    get1 = await client.get("/v1/persona", headers=user_headers(email))
    assert get1.status_code == 200
    assert get1.json()["body"] == "SIP-heavy. Salary on 1st."
