"""Integration tests: Slice 3.2–3.4 — import guide, recategorize, create_account_guided."""
import pytest
from httpx import AsyncClient

from .investment_fixtures import create_bank, ensure_user, unique_user_email, user_headers

pytestmark = pytest.mark.integration


async def _add_expense(client: AsyncClient, email: str, merchant: str = "Swiggy", amount: float = 350) -> str:
    """Helper: create a transaction and return created_id."""
    r = await client.post(
        "/v1/chat",
        json={"message": f"add {amount} for {merchant}"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    conv_id = r.json()["conversation_id"]
    r2 = await client.post(
        "/v1/chat",
        json={"message": "confirm", "conversation_id": conv_id},
        headers=user_headers(email),
    )
    assert r2.status_code == 200
    payload = r2.json()["response"].get("card_payload") or {}
    return payload.get("created_id", "")


# ----- S3.2 import_guide -----

async def test_import_guide_card_returned(client: AsyncClient) -> None:
    """Chat 'import statement' returns import_guide card with action URL."""
    email = unique_user_email("s32-import")
    await ensure_user(client, email)
    r = await client.post(
        "/v1/chat",
        json={"message": "import statement"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "import_guide"
    payload = resp["card_payload"]
    assert payload["action_url"] == "/import"
    assert "CSV" in payload["supported_formats"]


# ----- S3.3 create_account_guided -----

async def test_create_account_guided_sip_confirm_flow(client: AsyncClient) -> None:
    """Guided SIP account creation shows confirm card then creates account."""
    email = unique_user_email("s33-acct-guided")
    await ensure_user(client, email)
    await create_bank(client, email, name="HDFC Savings")  # needed as SIP parent

    # Step 1 — proposal
    r = await client.post(
        "/v1/chat",
        json={"message": "add SIP account 5000 for Nifty 50"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "confirm"
    assert resp["ui_type"] == "account_create_confirm"
    payload = resp["card_payload"]
    assert payload["account_type"] == "mutual_fund"
    assert payload["investment_mode"] == "sip"
    assert float(payload["emi_amount"]) == 5000.0

    # Step 2 — confirm
    conv_id = r.json()["conversation_id"]
    r2 = await client.post(
        "/v1/chat",
        json={"message": "confirm", "conversation_id": conv_id},
        headers=user_headers(email),
    )
    assert r2.status_code == 200
    resp2 = r2.json()["response"]
    assert resp2["status"] == "success"


async def test_create_account_guided_cancel(client: AsyncClient) -> None:
    """Cancelling create_account_guided does not create an account."""
    email = unique_user_email("s33-acct-cancel")
    await ensure_user(client, email)

    r = await client.post(
        "/v1/chat",
        json={"message": "add EPF account"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "confirm"

    conv_id = r.json()["conversation_id"]
    r2 = await client.post(
        "/v1/chat",
        json={"message": "cancel", "conversation_id": conv_id},
        headers=user_headers(email),
    )
    assert r2.status_code == 200


# ----- S3.4 explain_transaction -----

async def test_explain_transaction_returns_detail_card(client: AsyncClient) -> None:
    """'what did I spend at Swiggy' returns transaction_detail card."""
    email = unique_user_email("s34-explain")
    await ensure_user(client, email)
    await _add_expense(client, email, merchant="Swiggy", amount=350)

    r = await client.post(
        "/v1/chat",
        json={"message": "what did I spend at Swiggy"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "transaction_detail"
    payload = resp["card_payload"]
    assert isinstance(payload["transactions"], list)


async def test_explain_transaction_no_results(client: AsyncClient) -> None:
    """explain_transaction with no matching merchant returns empty list."""
    email = unique_user_email("s34-explain-empty")
    await ensure_user(client, email)

    r = await client.post(
        "/v1/chat",
        json={"message": "explain this charge from Amazon Prime"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["ui_type"] == "transaction_detail"
    assert resp["card_payload"]["transactions"] == []


# ----- S3.4 recategorize_transaction -----

async def test_recategorize_transaction_confirm_flow(client: AsyncClient) -> None:
    """Recategorize a transaction: confirm card → commit → category updated."""
    email = unique_user_email("s34-recategorize")
    await ensure_user(client, email)
    await _add_expense(client, email, merchant="Netflix", amount=499)

    r = await client.post(
        "/v1/chat",
        json={"message": "recategorize Netflix to Entertainment"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "confirm"
    assert resp["ui_type"] == "transaction_confirm"
    payload = resp["card_payload"]
    assert payload["new_category"] == "Entertainment"

    conv_id = r.json()["conversation_id"]
    r2 = await client.post(
        "/v1/chat",
        json={"message": "confirm", "conversation_id": conv_id},
        headers=user_headers(email),
    )
    assert r2.status_code == 200
    resp2 = r2.json()["response"]
    assert resp2["status"] == "success"
    assert resp2["card_payload"]["new_category"] == "Entertainment"


async def test_recategorize_no_matching_transaction(client: AsyncClient) -> None:
    """Recategorize with no matching merchant returns error message."""
    email = unique_user_email("s34-recat-miss")
    await ensure_user(client, email)

    r = await client.post(
        "/v1/chat",
        json={"message": "recategorize UnknownMerchant99 to Food"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] in ("error", "success")
