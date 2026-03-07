"""Integration tests: chat API (Phase 1 — planner + ledger + orchestrator)."""
import pytest
from httpx import AsyncClient


async def test_chat_add_expense(client: AsyncClient, account_id: str) -> None:
    r = await client.post(
        "/v1/chat",
        json={"message": "add 500 for Swiggy"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert "conversation_id" in data
    resp = data["response"]
    assert resp["status"] in ("success", "error")
    assert "data" in resp
    assert "next_suggested_actions" in resp
    if resp["status"] == "success":
        assert "message" in resp["data"] or "summary" in resp["data"] or "created_id" in resp["data"]


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
