"""Unit tests for spending period bounds."""
import pytest
from datetime import date

from app.agents.ledger_agent import _spend_period_bounds

pytestmark = pytest.mark.unit


def test_last_12_months_rolling():
    today = date(2026, 5, 26)
    start, end, label = _spend_period_bounds("last_12_months", today)
    assert end == today
    assert start == date(2025, 5, 26)
    assert label == "Last 12 months"


def test_this_month():
    today = date(2026, 3, 15)
    start, end, _ = _spend_period_bounds("this_month", today)
    assert start == date(2026, 3, 1)
    assert end == today
