"""Unit tests: expense capture vs spending analysis routing."""
import pytest

from app.agents.planner import _detect_add_expense, _detect_spending_period, plan
from app.core.schemas import Intent

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "message,merchant",
    [
        ("add 200 spend on food online", "food online"),
        ("add 500 for Swiggy", "Swiggy"),
        ("I spent 100 on Uber", "Uber"),
    ],
)
def test_add_expense_capture(message: str, merchant: str) -> None:
    assert _detect_spending_period(message) is None
    result = _detect_add_expense(message)
    assert result is not None
    assert result.intent == Intent.add_expense
    assert result.steps[0].action == "insert_transaction"
    assert result.steps[0].params["amount"] > 0
    assert result.steps[0].params.get("merchant") == merchant


@pytest.mark.parametrize(
    "message",
    [
        "where did I spend this month?",
        "spending breakdown",
        "show my spending dashboard",
    ],
)
def test_spending_analysis_not_expense_capture(message: str) -> None:
    assert _detect_add_expense(message) is None
    assert _detect_spending_period(message) is not None


@pytest.mark.asyncio
async def test_plan_add_expense_before_spending() -> None:
    result = await plan("add 200 spend on food online")
    assert result.intent == Intent.add_expense
    assert result.steps[0].action == "insert_transaction"
