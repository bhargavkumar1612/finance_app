"""Smoke tests: Slice 3 intents respond without error."""
import pytest
from httpx import AsyncClient

from tests.integration.investment_fixtures import create_sip_mf, ensure_user, unique_user_email, user_headers

pytestmark = pytest.mark.smoke


async def test_record_transfer_smoke(client: AsyncClient) -> None:
    email = unique_user_email("s3-smoke")
    await ensure_user(client, email)
    await create_sip_mf(client, email, name="Smoke SIP", emi_amount=5000)

    r = await client.post(
        "/v1/chat",
        json={"message": "record SIP 5000 for Smoke SIP"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "confirm"
    assert resp["ui_type"] == "transaction_confirm"
    assert len(resp["card_payload"]["legs"]) == 2


async def test_import_guide_smoke(client: AsyncClient) -> None:
    email = unique_user_email("s3-import-smoke")
    await ensure_user(client, email)

    r = await client.post(
        "/v1/chat",
        json={"message": "import statement"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    assert r.json()["response"]["ui_type"] == "import_guide"


async def test_explain_transaction_smoke(client: AsyncClient) -> None:
    email = unique_user_email("s3-explain-smoke")
    await ensure_user(client, email)

    r = await client.post(
        "/v1/chat",
        json={"message": "explain this charge from Swiggy"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    assert r.json()["response"]["ui_type"] == "transaction_detail"


async def test_create_account_guided_smoke(client: AsyncClient) -> None:
    email = unique_user_email("s3-acct-smoke")
    await ensure_user(client, email)

    r = await client.post(
        "/v1/chat",
        json={"message": "add SIP account 3000 for HDFC MF"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    assert r.json()["response"]["status"] == "confirm"
    assert r.json()["response"]["ui_type"] == "account_create_confirm"
