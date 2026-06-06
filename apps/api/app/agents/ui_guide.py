"""
UI Guide: maps (intent, last_result) → (ui_type, card_payload, chat_summary).

Pure function — no LLM, no I/O. Deterministic, fast, testable.
Called by the orchestrator after the Ledger agent runs.
"""
from typing import Any

from app.core.schemas import Intent


def build_ui_guide(
    intent: Intent,
    last_result: dict[str, Any],
) -> tuple[str, dict[str, Any], str]:
    """
    Return (ui_type, card_payload, chat_summary).

    ui_type       — one of the CardType literals defined in schemas.py
    card_payload  — structured data the frontend card component will render
    chat_summary  — plain-text message shown in the chat log
    """
    if intent == Intent.add_expense or intent == Intent.add_income:
        amount = last_result.get("amount")
        abs_amount = abs(float(amount)) if amount is not None else None
        merchant = last_result.get("merchant") or ""
        category = last_result.get("category")
        preview = last_result.get("preview", False)
        label = "Income" if intent == Intent.add_income else "Expense"
        summary = last_result.get("summary") or (
            f"{'Add' if preview else 'Recorded'} {label.lower()} ₹{abs_amount}"
            + (f" for {merchant}" if merchant else "")
            + "."
        )
        payload: dict[str, Any] = {
            "amount": abs_amount,
            "merchant": merchant,
            "category": category,
            "summary": summary,
            "created_id": last_result.get("created_id"),
            "transaction_date": last_result.get("transaction_date"),
            "nw_impact": last_result.get("nw_impact"),
            "preview": preview,
            "committed": not preview,
        }
        return "transaction_confirm", payload, summary

    if intent == Intent.spending_analysis:
        total = abs(float(last_result.get("total_spend", 0)))
        by_cat = last_result.get("by_category", {})
        by_cat_display = {k: abs(float(v)) for k, v in by_cat.items()}
        period = last_result.get("period", "")
        period_label = last_result.get("period_label", period)
        by_month = last_result.get("by_month", [])
        narrative = last_result.get("message")

        pie_data = [
            {"name": cat, "value": round(amt, 2)}
            for cat, amt in sorted(by_cat_display.items(), key=lambda x: x[1], reverse=True)
            if amt > 0
        ]
        top_cat = pie_data[0]["name"] if pie_data else None
        chat_summary = narrative or (
            f"You spent ₹{total:,.0f} over {period_label}"
            + (f". Top category: {top_cat}." if top_cat else ".")
        )
        payload = {
            "total_spend": total,
            "by_category": by_cat_display,
            "by_month": by_month,
            "pie_data": pie_data,
            "period": period,
            "period_label": period_label,
            "start": last_result.get("start"),
            "end": last_result.get("end"),
            "transaction_count": last_result.get("transaction_count", 0),
            "narrative": narrative,
        }
        return "spending_dashboard", payload, chat_summary

    if intent == Intent.net_worth_query:
        nw = last_result.get("net_worth", 0)
        assets = last_result.get("assets_total", 0)
        liabs = last_result.get("liabilities_total", 0)
        chat_summary = f"Your net worth is ₹{float(nw):,.2f} (assets − liabilities)."
        payload = {
            "net_worth": float(nw),
            "assets_total": float(assets),
            "liabilities_total": float(liabs),
            "cash_and_primary": last_result.get("cash_and_primary"),
            "manual_assets": last_result.get("manual_assets"),
            "credit_card_outstanding": last_result.get("credit_card_outstanding"),
            "loan_liabilities": last_result.get("loan_liabilities"),
            "accounts": last_result.get("accounts", []),
            "currency": last_result.get("currency", "INR"),
        }
        return "net_worth_breakdown", payload, chat_summary

    if intent == Intent.affordability_check:
        safe_emi = last_result.get("safe_emi_estimate", 0)
        nw = last_result.get("net_worth", 0)
        spend = last_result.get("monthly_spend", 0)
        msg = last_result.get("message", "Affordability estimate ready.")
        # Simple risk bucketing
        if safe_emi == 0:
            risk_level = "unknown"
        elif safe_emi < 5000:
            risk_level = "high"
        elif safe_emi < 20000:
            risk_level = "medium"
        else:
            risk_level = "low"
        chat_summary = f"Safe EMI estimate: ₹{float(safe_emi):,.2f}/month (risk: {risk_level})."
        payload = {
            "safe_emi_estimate": float(safe_emi),
            "net_worth": float(nw),
            "monthly_spend": float(spend),
            "risk_level": risk_level,
            "message": msg,
        }
        return "affordability_result", payload, chat_summary

    if intent == Intent.manage_accounts:
        msg = last_result.get("message", "Account updated.")
        accounts = last_result.get("accounts")
        if accounts is not None:
            return "account_list", {"accounts": accounts, "message": msg}, msg
        single = {
            k: last_result.get(k)
            for k in ("id", "name", "account_type", "institution", "credit_limit", "currency", "transaction_count")
            if last_result.get(k) is not None
        }
        if single:
            return "account_list", {"accounts": [single], "message": msg}, msg
        return "message_only", {"message": msg}, msg

    if intent == Intent.import_statement:
        msg = last_result.get(
            "message",
            "Use the Import tab to upload a CSV or PDF bank statement.",
        )
        return "message_only", {"message": msg}, msg

    # Phase 4 AI Analytical Views
    if intent == Intent.analyze_category_spending:
        return "category_drilldown", last_result, last_result.get("message", "Here is your category spending drilldown.")

    if intent in (Intent.track_subscriptions, Intent.list_recurring_bills):
        ui = "recurring_bill_list" if intent == Intent.list_recurring_bills else "subscription_list"
        return ui, last_result, last_result.get("message", "Here are your recurring bills.")

    if intent == Intent.budget_vs_actual:
        if last_result.get("coming_soon"):
            msg = last_result.get("message", "Envelope budgeting coming soon.")
            return "message_only", {"message": msg}, msg
        return "budget_comparison", last_result, last_result.get("message", "Budget comparison.")

    if intent == Intent.analyze_cash_flow:
        return "cash_flow_summary", last_result, last_result.get("message", "Here is your cash flow analysis.")

    if intent == Intent.get_top_expenses:
        return "top_expenses_list", last_result, last_result.get("message", "Here are your top expenses.")

    if intent == Intent.project_future_balance:
        return "future_balance_projection", last_result, last_result.get("message", "Here is your future balance projection.")

    if intent == Intent.debt_payoff_planner:
        return "debt_payoff_plan", last_result, last_result.get("message", "Here is your debt payoff plan.")

    if intent == Intent.investment_allocation:
        return "investment_pie_chart", last_result, last_result.get("message", "Here is your investment allocation.")

    if intent == Intent.vendor_spending_history:
        return "vendor_history", last_result, last_result.get("message", "Here is your spending history with this vendor.")

    if intent == Intent.unusual_spending_alert:
        return "anomaly_alert", last_result, last_result.get("message", "Here are your unusual spending alerts.")

    # unknown / fallback
    msg = last_result.get(
        "message",
        "I didn't quite get that. You can ask to add an expense, see your net worth, or spending breakdown.",
    )
    return "message_only", {"message": msg}, msg
