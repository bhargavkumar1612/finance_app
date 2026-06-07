"""Unit tests: account-scoped balance queries vs net worth routing."""
import pytest

from app.agents.planner import (
    _detect_account_balance_query,
    _detect_net_worth,
    _detect_portfolio_summary,
)
from app.core.schemas import Intent

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "message",
    [
        "how much money do I have in my EPF?",
        "what is my EPF balance",
        "how much is in my provident fund",
    ],
)
def test_epf_balance_routes_to_list_accounts(message: str) -> None:
    result = _detect_account_balance_query(message)
    assert result is not None
    assert result.intent == Intent.manage_accounts
    assert result.steps[0].action == "list_accounts"
    assert result.steps[0].params["account_type"] == "epf"
    assert _detect_net_worth(message) is None


def test_mutual_fund_performance_routes_to_portfolio_not_account_list() -> None:
    message = "what mutual funds did i invest in and how much and how are they performing"
    assert _detect_account_balance_query(message) is None
    result = _detect_portfolio_summary(message)
    assert result is not None
    assert result.intent == Intent.portfolio_summary


def test_compound_affordability_route() -> None:
    from app.agents.planner import _detect_compound_affordability

    result = _detect_compound_affordability(
        "compare my spending to my obligations and tell me if I am safe"
    )
    assert result is not None
    assert result.intent == Intent.affordability_check
    assert result.steps[0].action == "compute_affordability"


@pytest.mark.parametrize(
    "message",
    [
        "what is my net worth",
        "how much money do I have",
        "total assets",
    ],
)
def test_net_worth_still_routes(message: str) -> None:
    assert _detect_net_worth(message) is not None
    assert _detect_net_worth(message).intent == Intent.net_worth_query
