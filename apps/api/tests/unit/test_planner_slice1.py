"""Unit tests: Slice 1 keyword routing in planner (LLM_PROVIDER=none safe)."""
import pytest

from app.agents.planner import (
    _detect_fd_maturity,
    _detect_investment_allocation,
    _detect_portfolio_pnl,
    _detect_portfolio_summary,
    _detect_sip_status,
)
from app.core.schemas import Intent

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "message",
    [
        "how are my investments?",
        "show my investment dashboard",
        "how is my portfolio doing",
        "how are my mfs doing",
        "show my MF P&L",
    ],
)
def test_detect_portfolio_summary(message: str) -> None:
    result = _detect_portfolio_summary(message)
    assert result is not None
    assert result.intent == Intent.portfolio_summary
    assert result.steps[0].action == "portfolio_summary"


@pytest.mark.parametrize(
    "message",
    [
        "show my investment allocation",
        "portfolio allocation pie",
        "breakdown by type for investments",
    ],
)
def test_detect_investment_allocation(message: str) -> None:
    result = _detect_investment_allocation(message)
    assert result is not None
    assert result.intent == Intent.investment_allocation


@pytest.mark.parametrize(
    "message",
    [
        "show my most profitable investments",
        "top performers by pnl",
        "profit and loss on holdings",
    ],
)
def test_detect_portfolio_pnl(message: str) -> None:
    result = _detect_portfolio_pnl(message)
    assert result is not None
    assert result.intent == Intent.portfolio_pnl_drilldown


@pytest.mark.parametrize(
    "message",
    [
        "did I pay my SIP this month?",
        "sip status",
        "sips due this month",
        "how many installments left on my sip",
    ],
)
def test_detect_sip_status(message: str) -> None:
    result = _detect_sip_status(message)
    assert result is not None
    assert result.intent == Intent.sip_status_query


@pytest.mark.parametrize(
    "message",
    [
        "when does my FD mature?",
        "fd maturity date",
        "rd maturity",
    ],
)
def test_detect_fd_maturity(message: str) -> None:
    result = _detect_fd_maturity(message)
    assert result is not None
    assert result.intent == Intent.fd_maturity_query


def test_no_false_positive_on_expense() -> None:
    assert _detect_portfolio_summary("add 500 for lunch") is None
    assert _detect_sip_status("add expense for coffee") is None
