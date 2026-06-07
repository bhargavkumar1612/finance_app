"""Unit tests: Slice 2 keyword routing in planner."""
import pytest

from app.agents.planner import (
    _detect_affordability,
    _detect_create_recurring_bill,
    _detect_loan_emi_summary,
    _detect_upcoming_obligations,
)
from app.core.schemas import Intent

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "message",
    [
        "what's due this month?",
        "upcoming bills and EMIs",
        "show my obligations",
    ],
)
def test_detect_upcoming_obligations(message: str) -> None:
    result = _detect_upcoming_obligations(message)
    assert result is not None
    assert result.intent == Intent.upcoming_obligations
    assert result.steps[0].action == "upcoming_obligations"


@pytest.mark.parametrize(
    "message",
    [
        "loan emi summary",
        "how much is my total emi?",
        "emis left on my loans",
    ],
)
def test_detect_loan_emi_summary(message: str) -> None:
    result = _detect_loan_emi_summary(message)
    assert result is not None
    assert result.intent == Intent.loan_emi_summary


@pytest.mark.parametrize(
    "message",
    [
        "can I afford a new loan?",
        "what's my safe EMI?",
        "affordability check",
    ],
)
def test_detect_affordability(message: str) -> None:
    result = _detect_affordability(message)
    assert result is not None
    assert result.intent == Intent.affordability_check
    assert result.steps[0].action == "compute_affordability"


def test_detect_create_recurring_bill() -> None:
    result = _detect_create_recurring_bill("add recurring bill Netflix 499")
    assert result is not None
    assert result.intent == Intent.create_recurring_bill
    assert result.steps[0].action == "insert_recurring_bill"
    assert result.steps[0].params["amount"] == 499
