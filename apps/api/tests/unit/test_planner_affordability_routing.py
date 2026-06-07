"""Unit tests: affordability EMI parsing and income follow-up routing."""
import pytest

from app.agents.planner import (
    _detect_add_income,
    _detect_affordability,
    _detect_affordability_income_followup,
    _parse_emi_from_message,
    _parse_money_amount,
    plan,
)
from app.core.schemas import ConversationState, Intent

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "message,expected",
    [
        ("emi of 20k", 20000),
        ("Can I afford an emi of 20k", 20000),
        ("afford 35000 emi", 35000),
    ],
)
def test_parse_emi_from_message(message: str, expected: float) -> None:
    assert _parse_emi_from_message(message) == expected


def test_detect_affordability_with_target_emi() -> None:
    result = _detect_affordability("Can I afford an emi of 20k")
    assert result is not None
    assert result.intent == Intent.affordability_check
    assert result.steps[0].params["target_emi"] == 20000


def test_detect_add_income_parses_amount() -> None:
    result = _detect_add_income("add salary 190000")
    assert result is not None
    assert result.intent == Intent.add_income
    assert result.steps[0].params["amount"] == 190000


def test_affordability_income_followup() -> None:
    state = ConversationState(
        conversation_id="test",
        current_step=Intent.affordability_check.value,
        filled_slots={},
        agent_history=[
            {"role": "user", "content": "Can I afford an emi of 20k"},
            {"role": "assistant", "content": "Affordability estimate ready."},
            {"role": "user", "content": "but my salary will be credited every month 190000"},
        ],
        updated_at="2026-06-07T00:00:00+00:00",
    )
    result = _detect_affordability_income_followup(
        "but my salary will be credited every month 190000",
        state,
    )
    assert result is not None
    assert result.intent == Intent.affordability_check
    assert result.steps[0].action == "compute_affordability"
    assert result.steps[0].params["hypothetical_monthly_income"] == 190000
    assert result.steps[0].params["target_emi"] == 20000
    assert _detect_add_income("but my salary will be credited every month 190000") is None


def test_affordability_emi_followup() -> None:
    state = ConversationState(
        conversation_id="test",
        current_step=Intent.affordability_check.value,
        filled_slots={},
        agent_history=[
            {"role": "user", "content": "Can I afford an emi of 20k"},
            {"role": "assistant", "content": "Affordability estimate ready."},
            {"role": "user", "content": "what about 30k emi instead?"},
        ],
        updated_at="2026-06-07T00:00:00+00:00",
    )
    from app.agents.planner import _detect_affordability_emi_followup

    result = _detect_affordability_emi_followup("what about 30k emi instead?", state)
    assert result is not None
    assert result.intent == Intent.affordability_check
    assert result.steps[0].params["target_emi"] == 30000


@pytest.mark.asyncio
async def test_plan_affordability_followup_not_add_income(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "none")
    from app.services.llm_client import clear_llm_caches

    clear_llm_caches()
    state = ConversationState(
        conversation_id="test",
        current_step=Intent.affordability_check.value,
        filled_slots={},
        agent_history=[
            {"role": "user", "content": "Can I afford an emi of 20k"},
            {"role": "assistant", "content": "Affordability estimate ready."},
            {"role": "user", "content": "but my salary will be credited every month 190000"},
        ],
        updated_at="2026-06-07T00:00:00+00:00",
    )
    result = await plan("but my salary will be credited every month 190000", state)
    assert result.intent == Intent.affordability_check
    assert result.steps[0].action == "compute_affordability"
    assert result.steps[0].params.get("hypothetical_monthly_income") == 190000


def test_parse_money_amount_lakh() -> None:
    assert _parse_money_amount("1.9 lakh salary") == 190000
