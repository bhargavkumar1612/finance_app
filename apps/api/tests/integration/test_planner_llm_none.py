"""Integration: Slice 1 + Slice 2 + Slice 3 intents route with LLM_PROVIDER=none (no model call)."""
import pytest
from httpx import AsyncClient

from app.core.llm_settings import clear_llm_settings_cache
from .investment_fixtures import ensure_user, unique_user_email, user_headers

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def llm_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "none")
    clear_llm_settings_cache()
    yield
    clear_llm_settings_cache()


@pytest.mark.parametrize(
    "message,expected_ui",
    [
        ("how are my investments?", "investment_portfolio_dashboard"),
        ("show my investment allocation", "investment_pie_chart"),
        ("show my most profitable investments", "investment_pnl_bars"),
        ("did I pay my SIP this month?", "sip_schedule_summary"),
    ],
)
async def test_slice1_routes_without_llm(
    client: AsyncClient,
    message: str,
    expected_ui: str,
) -> None:
    email = unique_user_email("llm-none")
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


async def test_fd_maturity_routes_without_llm_with_fd(client: AsyncClient) -> None:
    from .investment_fixtures import create_fd, ensure_user, unique_user_email, user_headers

    email = unique_user_email("llm-none-fd")
    await ensure_user(client, email)
    await create_fd(client, email, name="Test FD", start_date="2026-01-01", tenure_months=12)
    r = await client.post(
        "/v1/chat",
        json={"message": "when does my FD mature?"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    assert r.json()["response"]["ui_type"] == "fd_maturity_summary"


# ----- Slice 2 keyword routes with LLM_PROVIDER=none -----


@pytest.mark.parametrize(
    "message,expected_ui",
    [
        ("what's due this month?", "obligation_list"),
        ("loan emi summary", "obligation_list"),
        ("can I afford a new loan?", "affordability_result"),
        ("show my obligations", "obligation_list"),
    ],
)
async def test_slice2_routes_without_llm(
    client: AsyncClient,
    message: str,
    expected_ui: str,
) -> None:
    email = unique_user_email("s2-llm-none")
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


async def test_create_recurring_bill_goes_to_confirm_without_llm(client: AsyncClient) -> None:
    """create_recurring_bill keyword route triggers confirm flow without LLM."""
    email = unique_user_email("s2-rb-llm-none")
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

    conversation_id = r.json()["conversation_id"]
    r2 = await client.post(
        "/v1/chat",
        json={"message": "confirm", "conversation_id": conversation_id},
        headers=user_headers(email),
    )
    assert r2.status_code == 200
    assert r2.json()["response"]["status"] == "success"


# ----- Slice 3 keyword routes with LLM_PROVIDER=none -----


async def test_record_transfer_routes_without_llm(client: AsyncClient) -> None:
    from .investment_fixtures import create_sip_mf, ensure_user, unique_user_email, user_headers

    email = unique_user_email("s3-llm-none")
    await ensure_user(client, email)
    await create_sip_mf(client, email, name="LLM SIP", emi_amount=5000)

    r = await client.post(
        "/v1/chat",
        json={"message": "record SIP 5000 for LLM SIP"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "confirm"
    assert resp["ui_type"] == "transaction_confirm"
    assert len(resp["card_payload"]["legs"]) == 2


async def test_explain_transaction_routes_without_llm(client: AsyncClient) -> None:
    """explain_transaction keyword route works without LLM (returns transaction_detail card)."""
    email = unique_user_email("s3-explain-llm-none")
    await ensure_user(client, email)
    r = await client.post(
        "/v1/chat",
        json={"message": "explain this charge from Netflix"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == "transaction_detail"
    assert "transactions" in resp["card_payload"]


async def test_import_statement_routes_without_llm(client: AsyncClient) -> None:
    """import_statement keyword route returns import_guide card without LLM."""
    email = unique_user_email("s3-import-llm-none")
    await ensure_user(client, email)
    r = await client.post(
        "/v1/chat",
        json={"message": "import statement"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == "import_guide"
    assert resp["card_payload"]["action_url"] == "/import"


async def test_create_account_guided_routes_without_llm(client: AsyncClient) -> None:
    """create SIP/MF account keyword route triggers confirm without LLM."""
    email = unique_user_email("s3-acct-guided-llm-none")
    await ensure_user(client, email)
    r = await client.post(
        "/v1/chat",
        json={"message": "add SIP account 5000 for Nifty 50"},
        headers=user_headers(email),
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "confirm"
    assert resp["ui_type"] == "account_create_confirm"
    assert resp["card_payload"]["account_type"] == "mutual_fund"
    assert resp["card_payload"]["investment_mode"] == "sip"
