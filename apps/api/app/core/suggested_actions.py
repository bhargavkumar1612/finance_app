"""Merge missing-data hints, persona drill-downs, and default next actions."""
from __future__ import annotations

from app.core.schemas import Intent

_DRILLDOWN_LABELS: dict[str, str] = {
    "sip_status_query": "SIP status",
    "portfolio_pnl_drilldown": "Show P&L",
    "investment_allocation": "Show allocation",
    "spending_analysis": "Spending breakdown",
    "list_recurring_bills": "Recurring bills",
    "create_account": "Add an account",
    "upcoming_obligations": "What's due this month?",
    "loan_emi_summary": "Loan EMI summary",
    "affordability_check": "Can I afford a loan?",
}

_DEFAULT_NEXT = ["Add an expense", "What's my net worth?", "Where did I spend this month?"]


def merge_suggested_actions(
    intent: Intent,
    last_result: dict | None,
    hints: list[str],
    defaults: list[str],
    *,
    max_items: int = 8,
) -> list[str]:
    persona = (last_result or {}).get("persona_hints") or {}
    prioritize = persona.get("prioritize_drilldowns") or []
    persona_labels = [
        _DRILLDOWN_LABELS[key]
        for key in prioritize
        if key in _DRILLDOWN_LABELS
    ]

    merged: list[str] = []
    seen: set[str] = set()
    for item in hints + persona_labels + defaults:
        if item and item not in seen:
            seen.add(item)
            merged.append(item)
        if len(merged) >= max_items:
            break
    return merged or list(_DEFAULT_NEXT)
