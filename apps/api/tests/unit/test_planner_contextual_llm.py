"""Unit tests: contextual LLM-first planner routing."""
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.planner import (
    _needs_contextual_llm,
    _prefer_llm_planner,
    plan,
)
from app.core.schemas import ConversationState, Intent

pytestmark = pytest.mark.unit


def _afford_state(message: str) -> ConversationState:
    return ConversationState(
        conversation_id="test",
        current_step=Intent.affordability_check.value,
        filled_slots={},
        agent_history=[
            {"role": "user", "content": "Can I afford an emi of 20k"},
            {"role": "assistant", "content": "Affordability estimate ready."},
            {"role": "user", "content": message},
        ],
        updated_at="2026-06-07T00:00:00+00:00",
    )


def test_needs_contextual_llm_on_salary_followup() -> None:
    state = _afford_state("but my salary will be credited every month 190000")
    assert _needs_contextual_llm("but my salary will be credited every month 190000", state) is True


def test_needs_contextual_llm_false_on_first_message() -> None:
    assert _needs_contextual_llm("what is my net worth?", None) is False


@pytest.mark.asyncio
async def test_contextual_followup_uses_llm_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PLANNER_MODE", "auto")
    from app.services.llm_client import clear_llm_caches

    clear_llm_caches()

    state = _afford_state("but my salary will be credited every month 190000")
    mock_llm = AsyncMock(
        return_value=__import__(
            "app.core.schemas", fromlist=["PlannerOutput"]
        ).PlannerOutput(
            intent=Intent.affordability_check,
            steps=[
                __import__(
                    "app.core.schemas", fromlist=["PlannerStep"]
                ).PlannerStep(
                    agent="ledger",
                    action="compute_affordability",
                    params={"target_emi": 20000, "hypothetical_monthly_income": 190000},
                )
            ],
            ui_mode="guided_flow",
        )
    )

    with patch("app.agents.planner._llm_plan", mock_llm):
        with patch("app.agents.planner._semantic_route_hint", return_value="compute_affordability"):
            result = await plan("but my salary will be credited every month 190000", state)

    mock_llm.assert_awaited_once()
    assert mock_llm.await_args.kwargs["contextual"] is True
    assert result.intent == Intent.affordability_check


@pytest.mark.asyncio
async def test_first_message_still_uses_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PLANNER_MODE", "auto")
    from app.services.llm_client import clear_llm_caches

    clear_llm_caches()

    mock_llm = AsyncMock()
    with patch("app.agents.planner._llm_plan", mock_llm):
        result = await plan("Can I afford an emi of 20k")

    mock_llm.assert_not_awaited()
    assert result.intent == Intent.affordability_check
    assert result.steps[0].params.get("target_emi") == 20000
