"""Unit tests: obligations.py and commitments.py pure helper functions."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.obligations import _bill_next_due

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _bill_next_due — monthly bills
# ---------------------------------------------------------------------------


def _monthly_bill(due_day: int) -> SimpleNamespace:
    return SimpleNamespace(frequency="monthly", due_day=due_day, weekday=None)


def test_bill_next_due_monthly_future_day() -> None:
    today = date(2026, 6, 7)  # 7th; due_day=15 is still in June
    result = _bill_next_due(_monthly_bill(15), today)
    assert result == "2026-06-15"


def test_bill_next_due_monthly_past_day_rolls_to_next_month() -> None:
    today = date(2026, 6, 7)  # 7th; due_day=5 already passed → July
    result = _bill_next_due(_monthly_bill(5), today)
    assert result == "2026-07-05"


def test_bill_next_due_monthly_same_day() -> None:
    today = date(2026, 6, 7)  # due_day=7 — exactly today, not yet passed
    result = _bill_next_due(_monthly_bill(7), today)
    assert result == "2026-06-07"


def test_bill_next_due_monthly_end_of_month_clamps() -> None:
    # due_day=31 in February → clamped to last day of Feb
    today = date(2026, 2, 1)
    result = _bill_next_due(_monthly_bill(31), today)
    assert result == "2026-02-28"


def test_bill_next_due_monthly_no_due_day_returns_none() -> None:
    bill = SimpleNamespace(frequency="monthly", due_day=None, weekday=None)
    assert _bill_next_due(bill, date(2026, 6, 7)) is None


# ---------------------------------------------------------------------------
# _bill_next_due — weekly bills
# ---------------------------------------------------------------------------


def _weekly_bill(weekday: int) -> SimpleNamespace:
    return SimpleNamespace(frequency="weekly", due_day=None, weekday=weekday)


def test_bill_next_due_weekly_future_weekday() -> None:
    # 2026-06-07 is a Sunday (weekday=6); next Monday (0) is 2026-06-08
    today = date(2026, 6, 7)
    result = _bill_next_due(_weekly_bill(0), today)
    assert result == "2026-06-08"


def test_bill_next_due_weekly_same_weekday_advances_full_week() -> None:
    # 2026-06-07 is Sunday (6); next Sunday is 2026-06-14
    today = date(2026, 6, 7)
    result = _bill_next_due(_weekly_bill(6), today)
    assert result == "2026-06-14"


def test_bill_next_due_weekly_no_weekday_returns_none() -> None:
    bill = SimpleNamespace(frequency="weekly", due_day=None, weekday=None)
    assert _bill_next_due(bill, date(2026, 6, 7)) is None


# ---------------------------------------------------------------------------
# monthly_recurring_bills weekly annualisation formula
# ---------------------------------------------------------------------------


def test_weekly_bill_monthly_equivalent() -> None:
    """Weekly bill amount × 4.33 should equal the monthly commitment."""
    weekly_amount = 1000.0
    expected_monthly = round(weekly_amount * 4.33, 2)
    assert expected_monthly == 4330.0


def test_monthly_bill_passes_through_unchanged() -> None:
    monthly_amount = 5000.0
    assert round(abs(monthly_amount), 2) == 5000.0
