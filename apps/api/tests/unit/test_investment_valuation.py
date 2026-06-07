"""Unit tests: invested vs current value and P&L for holdings."""
import pytest

from app.services.investment_valuation import compute_pnl, effective_holdings_value

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("invested", "current", "amount", "percent"),
    [
        (100000, 125000, 25000, 25.0),
        (100000, 90000, -10000, -10.0),
        (100000, 100000, 0, 0.0),
    ],
)
def test_compute_pnl(invested, current, amount, percent):
    pnl_amount, pnl_percent = compute_pnl(invested, current)
    assert pnl_amount == amount
    assert pnl_percent == percent


@pytest.mark.parametrize(
    ("invested", "current"),
    [
        (None, 100000),
        (100000, None),
        (0, 100000),
        (-1, 100000),
    ],
)
def test_compute_pnl_returns_none_when_incomplete(invested, current):
    assert compute_pnl(invested, current) == (None, None)


def test_effective_holdings_value_prefers_current():
    assert effective_holdings_value(140000, 125000) == 140000


def test_effective_holdings_value_falls_back_to_balance():
    assert effective_holdings_value(None, 125000) == 125000
    assert effective_holdings_value(None, None) == 0.0
