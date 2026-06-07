"""Unit tests for suggested action merging."""
from app.core.schemas import Intent
from app.core.suggested_actions import merge_suggested_actions


def test_persona_drilldowns_prepended_after_hints() -> None:
    result = merge_suggested_actions(
        Intent.portfolio_summary,
        {"persona_hints": {"prioritize_drilldowns": ["portfolio_pnl_drilldown", "sip_status_query"]}},
        ["Add this month's salary"],
        ["Show allocation", "SIP status"],
    )
    assert result[0] == "Add this month's salary"
    assert "Show P&L" in result
    assert "SIP status" in result
    assert result.count("SIP status") == 1


def test_dedupes_defaults() -> None:
    result = merge_suggested_actions(
        Intent.net_worth_query,
        None,
        [],
        ["What's my net worth?", "Spending breakdown"],
    )
    assert result == ["What's my net worth?", "Spending breakdown"]
