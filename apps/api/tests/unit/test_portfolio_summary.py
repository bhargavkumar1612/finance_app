"""Unit tests for portfolio_summary service (Slice 1)."""
from datetime import date

import pytest

from app.services.portfolio_summary import (
    _add_months,
    _aggregate_totals,
    _by_liquidity,
    _footer_suggestions,
    _next_due_date,
    apply_persona_filters_to_payload,
)
from app.services.persona_rules import apply_persona_filters


def test_add_months():
    assert _add_months(date(2024, 1, 15), 12) == date(2025, 1, 15)
    assert _add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_next_due_date_unpaid_this_month():
    today = date(2026, 6, 7)
    assert _next_due_date(15, today, False) == date(2026, 6, 15)
    assert _next_due_date(5, today, False) == date(2026, 7, 5)


def test_next_due_date_paid_this_month():
    today = date(2026, 6, 7)
    assert _next_due_date(5, today, True) == date(2026, 7, 5)


def test_aggregate_totals():
    entries = [
        {"type": "bank", "current_value": 10000, "invested": None},
        {"type": "mutual_fund", "current_value": 50000, "invested": 40000},
    ]
    totals = _aggregate_totals(entries, [])
    assert totals["current"] == 60000
    assert totals["cash_total"] == 10000
    assert totals["pnl_amount"] == 10000
    assert totals["pnl_percent"] == 25.0


def test_by_liquidity_order():
    entries = [
        {"id": "1", "type": "fixed_deposit", "current_value": 100, "liquidity_rank": 5},
        {"id": "2", "type": "bank", "current_value": 200, "liquidity_rank": 1},
        {"id": "3", "type": "mutual_fund", "current_value": 300, "liquidity_rank": 3},
    ]
    result = _by_liquidity(entries, [])
    assert [r["bucket"] for r in result] == ["bank", "mutual_fund", "fixed_deposit"]


def test_footer_suggestions_no_mf():
    suggestions = _footer_suggestions(
        [{"type": "bank", "current_value": 1000}],
        [],
        [],
    )
    labels = [s["label"] for s in suggestions]
    assert any("mutual fund" in l.lower() for l in labels)


def test_footer_suggestions_debt_paydown():
    suggestions = _footer_suggestions(
        [{"type": "bank", "current_value": 1000}],
        [],
        [],
        loan_outstanding=50_000,
        cc_outstanding=10_000,
    )
    labels = [s["label"] for s in suggestions]
    assert any("debt" in l.lower() for l in labels)


def test_footer_suggestions_80c_in_q1():
    suggestions = _footer_suggestions(
        [{"type": "bank", "current_value": 1000}],
        [],
        [],
        today=date(2026, 2, 15),
    )
    labels = [s["label"] for s in suggestions]
    assert any("80c" in l.lower() for l in labels)


def test_persona_hides_pnl_without_holdings():
    hints = apply_persona_filters(
        [{"type": "bank", "current_value": 1000}],
        [],
        [],
    )
    assert "pnl" in hints["hide_sections"]


def test_persona_category_skew_prioritizes_spending():
    hints = apply_persona_filters(
        [{"type": "mutual_fund", "current_value": 50000, "pnl_percent": 10}],
        [],
        [],
        category_skew={"top_category": "Food", "top_category_pct": 42.0, "subscription_heavy": False},
    )
    assert "category_skew" in hints["traits"]
    assert "spending_analysis" in hints["prioritize_drilldowns"]


def test_persona_subscription_heavy_trait():
    hints = apply_persona_filters(
        [{"type": "bank", "current_value": 1000}],
        [],
        [],
        category_skew={"top_category": "Entertainment", "top_category_pct": 15.0, "subscription_heavy": True},
    )
    assert "subscription_heavy" in hints["traits"]
    assert "list_recurring_bills" in hints["prioritize_drilldowns"]


def test_compute_investment_allocation_percentages():
    entries = [
        {"type": "mutual_fund", "current_value": 75000, "invested": 60000},
        {"type": "stock", "current_value": 25000, "invested": 20000},
    ]
    type_totals: dict[str, float] = {}
    for e in entries:
        label = e["type"].replace("_", " ").title()
        type_totals[label] = type_totals.get(label, 0) + e["current_value"]
    total = sum(type_totals.values())
    allocation = {k: round(v / total * 100, 1) for k, v in type_totals.items()}
    assert allocation["Mutual Fund"] == 75.0
    assert allocation["Stock"] == 25.0


def test_persona_filter_payload():
    payload = {
        "by_pnl_percent": [{"name": "X"}],
        "by_pnl_amount": [{"name": "X"}],
        "physical_assets": [],
        "pie_by_type": [],
    }
    filtered = apply_persona_filters_to_payload(payload, {"hide_sections": ["pnl"]})
    assert filtered["by_pnl_percent"] == []
    assert filtered["by_pnl_amount"] == []
