"""Integration tests: chat API (Phase 1 — planner + ledger + orchestrator)."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_chat_add_expense_confirm_before_write(client: AsyncClient, account_id: str) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "add 500 for Swiggy"},
    )
    assert r.status_code == 200
    data = r.json()
    resp = data["response"]
    assert resp["status"] == "confirm"
    assert resp["ui_type"] == "transaction_confirm"
    assert resp["card_payload"].get("preview") is True
    conv_id = data["conversation_id"]

    r2 = await client.post(
        "/v1/chat",
        json={"message": "confirm", "conversation_id": conv_id},
    )
    assert r2.status_code == 200
    resp2 = r2.json()["response"]
    assert resp2["status"] == "success"
    assert resp2["data"].get("created_id")


async def test_chat_net_worth(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "what is my net worth?"},
    )
    assert r.status_code == 200
    data = r.json()
    resp = data["response"]
    assert resp["status"] == "success"
    assert "data" in resp
    assert "net_worth" in resp["data"] or "message" in resp["data"]


async def test_chat_spending_analysis(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "where did I spend this month?"},
    )
    assert r.status_code == 200
    data = r.json()
    resp = data["response"]
    assert resp["status"] == "success"
    assert "data" in resp


async def test_chat_portfolio_summary(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "how are my investments?"},
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == "investment_portfolio_dashboard"
    assert "card_payload" in resp
    assert "totals" in resp["card_payload"]


async def test_chat_investment_allocation(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "show my investment allocation"},
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == "investment_pie_chart"


async def test_chat_portfolio_pnl(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "show my most profitable investments"},
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == "investment_pnl_bars"


async def test_chat_sip_status(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "did I pay my SIP this month?"},
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] == "sip_schedule_summary"


async def test_chat_fd_maturity(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "when does my FD mature?"},
    )
    assert r.status_code == 200
    resp = r.json()["response"]
    assert resp["status"] == "success"
    assert resp["ui_type"] in ("message_only", "fd_maturity_summary")


async def test_chat_unknown_intent(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "tell me a joke"},
    )
    assert r.status_code == 200
    data = r.json()
    resp = data["response"]
    assert resp["status"] == "success"
    assert "next_suggested_actions" in resp


async def test_chat_requires_message(client: AsyncClient) -> None:
    r = await client.post("/v1/chat", json={})
    assert r.status_code == 422


async def test_list_chat_sessions(client: AsyncClient) -> None:
    await client.post("/v1/chat", json={"message": "what is my net worth?"})
    r = await client.get("/v1/chat/sessions")
    assert r.status_code == 200
    sessions = r.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1
    assert "id" in sessions[0]
    assert "title" in sessions[0]


async def test_rename_and_delete_chat_session(client: AsyncClient) -> None:
    chat = await client.post("/v1/chat", json={"message": "add 100 for coffee"})
    assert chat.status_code == 200
    session_id = chat.json()["conversation_id"]

    rename = await client.patch(
        f"/v1/chat/sessions/{session_id}",
        json={"title": "Coffee expenses"},
    )
    assert rename.status_code == 200
    assert rename.json()["title"] == "Coffee expenses"

    listed = await client.get("/v1/chat/sessions")
    match = next((s for s in listed.json() if s["id"] == session_id), None)
    assert match is not None
    assert match["title"] == "Coffee expenses"

    delete = await client.delete(f"/v1/chat/sessions/{session_id}")
    assert delete.status_code == 204

    gone = await client.get(f"/v1/chat/sessions/{session_id}")
    assert gone.status_code == 404
