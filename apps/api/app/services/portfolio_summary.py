"""Portfolio dashboard, allocation, P&L drill-down, SIP status, FD maturity — deterministic Ledger facts."""
from __future__ import annotations

import calendar
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Asset
from app.services.account_balances import account_balance
from app.services.account_types import HOLDINGS_TYPES, INVESTMENT_FD_TYPES, PRIMARY_TYPES
from app.services.investment_valuation import (
    compute_pnl,
    effective_holdings_value,
    resolve_current_value,
    resolve_invested_amount,
)
from app.services.mf_investment_mode import is_sip_account
from app.services.mf_sip_schedule import compute_sip_schedule

# Liquidity rank — glossary canonical order (most liquid → least)
LIQUIDITY_RANK: dict[str, int] = {
    "bank": 1,
    "cash": 1,
    "wallet": 1,
    "stock": 2,
    "mutual_fund": 3,
    "recurring_deposit": 4,
    "fixed_deposit": 5,
    "epf": 6,
    "asset": 7,
}

_TYPE_LABELS = {
    "bank": "Bank",
    "cash": "Cash",
    "wallet": "Wallet",
    "stock": "Stock",
    "mutual_fund": "Mutual Fund",
    "fixed_deposit": "Fixed Deposit",
    "recurring_deposit": "Recurring Deposit",
    "epf": "EPF",
    "asset": "Physical Asset",
}

TOP_N = 5


def _type_label(account_type: str) -> str:
    return _TYPE_LABELS.get(account_type, account_type.replace("_", " ").title())


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(start.day, last_day)
    return date(year, month, day)


def _next_due_date(due_day: int, today: date, paid_this_month: bool) -> date:
    if paid_this_month:
        if today.month == 12:
            return date(today.year + 1, 1, min(due_day, 31))
        return date(today.year, today.month + 1, min(due_day, calendar.monthrange(today.year, today.month + 1)[1]))
    if today.day <= due_day:
        return date(today.year, today.month, min(due_day, calendar.monthrange(today.year, today.month)[1]))
    if today.month == 12:
        return date(today.year + 1, 1, min(due_day, 31))
    return date(today.year, today.month + 1, min(due_day, calendar.monthrange(today.year, today.month + 1)[1]))


async def _holding_entries(session: AsyncSession, user_id: UUID) -> list[dict]:
    result = await session.execute(select(Account).where(Account.user_id == user_id))
    entries: list[dict] = []
    for acc in result.scalars().all():
        balance = float(await account_balance(session, acc.id, user_id))
        if acc.account_type in PRIMARY_TYPES or acc.account_type == "wallet":
            current = balance
            invested = None
            pnl_amount, pnl_percent = None, None
            as_per_ledger = False
        elif acc.account_type in HOLDINGS_TYPES:
            invested = await resolve_invested_amount(session, acc, user_id)
            current_raw = await resolve_current_value(session, acc, user_id, balance)
            current = effective_holdings_value(current_raw, balance)
            pnl_amount, pnl_percent = compute_pnl(invested, current)
            as_per_ledger = acc.current_value is None
        else:
            continue
        if current <= 0 and (invested is None or invested <= 0):
            continue
        entries.append({
            "id": str(acc.id),
            "name": acc.name,
            "type": acc.account_type,
            "current_value": current,
            "invested": invested,
            "pnl_amount": pnl_amount,
            "pnl_percent": pnl_percent,
            "as_per_ledger": as_per_ledger,
            "liquidity_rank": LIQUIDITY_RANK.get(acc.account_type, 99),
        })
    return entries


async def _physical_assets(session: AsyncSession, user_id: UUID) -> list[dict]:
    result = await session.execute(select(Asset).where(Asset.user_id == user_id))
    items = []
    for asset in result.scalars().all():
        value = float(asset.current_value or 0)
        if value <= 0:
            continue
        items.append({
            "name": asset.name,
            "asset_type": asset.asset_type or "other",
            "current_value": value,
            "liquidity_rank": LIQUIDITY_RANK["asset"],
        })
    return items


def _aggregate_totals(entries: list[dict], physical: list[dict]) -> dict:
    invested = sum(e["invested"] or 0 for e in entries if e.get("invested") is not None)
    current = sum(e["current_value"] for e in entries) + sum(p["current_value"] for p in physical)
    holdings_invested = sum(e["invested"] or 0 for e in entries if e["type"] in HOLDINGS_TYPES)
    holdings_current = sum(e["current_value"] for e in entries if e["type"] in HOLDINGS_TYPES)
    pnl_amount = holdings_current - holdings_invested if holdings_invested > 0 else None
    pnl_percent = (pnl_amount / holdings_invested * 100) if pnl_amount is not None and holdings_invested > 0 else None
    cash_total = sum(e["current_value"] for e in entries if e["type"] in PRIMARY_TYPES | {"wallet"})
    return {
        "invested": round(invested, 2),
        "current": round(current, 2),
        "pnl_amount": round(pnl_amount, 2) if pnl_amount is not None else None,
        "pnl_percent": round(pnl_percent, 2) if pnl_percent is not None else None,
        "cash_total": round(cash_total, 2),
    }


def _by_liquidity(entries: list[dict], physical: list[dict]) -> list[dict]:
    buckets: dict[str, dict] = {}
    for e in entries:
        bucket = e["type"]
        if bucket not in buckets:
            buckets[bucket] = {
                "rank": e["liquidity_rank"],
                "bucket": bucket,
                "label": _type_label(bucket),
                "current_value": 0.0,
                "account_ids": [],
            }
        buckets[bucket]["current_value"] += e["current_value"]
        buckets[bucket]["account_ids"].append(e["id"])
    if physical:
        total_phys = sum(p["current_value"] for p in physical)
        buckets["asset"] = {
            "rank": LIQUIDITY_RANK["asset"],
            "bucket": "asset",
            "label": _TYPE_LABELS["asset"],
            "current_value": total_phys,
            "account_ids": [],
        }
    return sorted(
        [{**b, "current_value": round(b["current_value"], 2)} for b in buckets.values()],
        key=lambda x: x["rank"],
    )


def _footer_suggestions(
    entries: list[dict],
    physical: list[dict],
    accounts: list[Account],
    *,
    loan_outstanding: float = 0,
    cc_outstanding: float = 0,
    today: date | None = None,
) -> list[dict]:
    suggestions: list[dict] = []
    types_present = {e["type"] for e in entries}
    has_mf = "mutual_fund" in types_present
    has_fd = "fixed_deposit" in types_present or "recurring_deposit" in types_present
    has_bank = bool(types_present & PRIMARY_TYPES)
    stale = [e for e in entries if e.get("as_per_ledger") and e["type"] in HOLDINGS_TYPES]
    today = today or date.today()
    total_debt = loan_outstanding + cc_outstanding

    if total_debt > 0:
        suggestions.append({
            "action": "debt_payoff",
            "label": "Pay down high-interest debt",
            "reason": f"₹{total_debt:,.0f} outstanding on loans and credit cards",
        })
    if today.month in (1, 2, 3):
        suggestions.append({
            "action": "tax_80c",
            "label": "Review 80C tax-saving investments",
            "reason": "FY ending soon — check ELSS/PPF/NPS contributions (informational only)",
        })
    if not has_mf:
        suggestions.append({
            "action": "create_account",
            "label": "Add a mutual fund",
            "reason": "Diversify with SIP or lump-sum MF holdings",
        })
    if has_bank and not has_fd:
        suggestions.append({
            "action": "create_account",
            "label": "Park idle cash in FD/RD",
            "reason": "You have bank balance but no fixed/recurring deposits",
        })
    if stale:
        suggestions.append({
            "action": "update_account",
            "label": f"Update current value for {stale[0]['name']}",
            "reason": "Holdings shown as per ledger — refresh for accurate P&L",
        })
    if not any(is_sip_account(a) for a in accounts):
        suggestions.append({
            "action": "create_account",
            "label": "Set up a SIP mutual fund",
            "reason": "Regular SIPs build long-term wealth",
        })
    if not physical:
        suggestions.append({
            "action": "add_asset",
            "label": "Add physical assets (gold, property)",
            "reason": "Complete your net worth picture",
        })
    return suggestions[:5]


async def compute_portfolio_summary(session: AsyncSession, user_id: UUID) -> dict:
    from app.services.account_balances import liability_outstanding
    from app.services.account_types import LOAN_TYPES
    from app.services.persona_rules import apply_persona_filters, derive_category_skew

    accounts_result = await session.execute(select(Account).where(Account.user_id == user_id))
    accounts = list(accounts_result.scalars().all())
    category_skew = await derive_category_skew(session, user_id)
    entries = await _holding_entries(session, user_id)
    physical = await _physical_assets(session, user_id)
    loan_outstanding = 0.0
    cc_outstanding = 0.0
    for acc in accounts:
        if acc.account_type in LOAN_TYPES:
            loan_outstanding += float(await liability_outstanding(session, acc.id, user_id))
        elif acc.account_type == "credit_card":
            cc_outstanding += float(await liability_outstanding(session, acc.id, user_id))
    totals = _aggregate_totals(entries, physical)
    by_liquidity = _by_liquidity(entries, physical)
    by_value = sorted(entries + [
        {"name": p["name"], "type": "asset", "current_value": p["current_value"],
         "invested": None, "pnl_percent": None, "pnl_amount": None, "as_per_ledger": False}
        for p in physical
    ], key=lambda x: x["current_value"], reverse=True)[:TOP_N]

    holdings_with_pnl = [e for e in entries if e.get("pnl_percent") is not None]
    by_pnl_percent = sorted(holdings_with_pnl, key=lambda x: x["pnl_percent"], reverse=True)[:TOP_N]
    by_pnl_amount = sorted(
        [e for e in holdings_with_pnl if e.get("pnl_amount") is not None],
        key=lambda x: x["pnl_amount"],
        reverse=True,
    )[:TOP_N]

    type_totals: dict[str, float] = {}
    for e in entries:
        if e["type"] in HOLDINGS_TYPES:
            type_totals[e["type"]] = type_totals.get(e["type"], 0) + e["current_value"]
    pie_by_type = [
        {"name": _type_label(t), "value": round(v, 2)}
        for t, v in sorted(type_totals.items(), key=lambda x: x[1], reverse=True)
        if v > 0
    ]
    pie_by_account = [
        {"name": e["name"], "value": round(e["current_value"], 2)}
        for e in sorted(entries, key=lambda x: x["current_value"], reverse=True)
        if e["type"] in HOLDINGS_TYPES and e["current_value"] > 0
    ][:TOP_N]
    if len(pie_by_account) > TOP_N:
        other = sum(e["current_value"] for e in entries[TOP_N:] if e["type"] in HOLDINGS_TYPES)
        if other > 0:
            pie_by_account.append({"name": "Other", "value": round(other, 2)})

    footer = _footer_suggestions(
        entries,
        physical,
        accounts,
        loan_outstanding=loan_outstanding,
        cc_outstanding=cc_outstanding,
    )
    persona_hints = apply_persona_filters(entries, physical, accounts, category_skew)

    payload = {
        "totals": totals,
        "by_liquidity": by_liquidity,
        "by_value": by_value,
        "by_pnl_percent": by_pnl_percent,
        "by_pnl_amount": by_pnl_amount,
        "pie_by_type": pie_by_type,
        "pie_by_account": pie_by_account,
        "physical_assets": physical,
        "cash_total": totals["cash_total"],
        "footer_suggestions": footer,
        "persona_hints": persona_hints,
    }
    payload = apply_persona_filters_to_payload(payload, persona_hints)
    current = totals["current"]
    msg = f"Portfolio current value ₹{current:,.0f}"
    if totals["pnl_amount"] is not None:
        msg += f" · P&L ₹{totals['pnl_amount']:,.0f} ({totals['pnl_percent']:+.1f}%)"
    payload["message"] = msg + "."
    return payload


def apply_persona_filters_to_payload(payload: dict, persona_hints: dict) -> dict:
    """Hide sections with no stake per persona v1 rules."""
    hide = set(persona_hints.get("hide_sections", []))
    if "pnl" in hide:
        payload["by_pnl_percent"] = []
        payload["by_pnl_amount"] = []
    if "physical_assets" in hide:
        payload["physical_assets"] = []
    if "pie" in hide and not payload.get("pie_by_type"):
        payload["pie_by_type"] = []
    return payload


async def compute_pnl_drilldown(session: AsyncSession, user_id: UUID) -> dict:
    entries = await _holding_entries(session, user_id)
    holdings = [e for e in entries if e.get("pnl_percent") is not None]
    by_pnl_percent = sorted(holdings, key=lambda x: x["pnl_percent"], reverse=True)[:TOP_N]
    by_pnl_amount = sorted(
        [e for e in holdings if e.get("pnl_amount") is not None],
        key=lambda x: x["pnl_amount"],
        reverse=True,
    )[:TOP_N]
    return {
        "by_pnl_percent": by_pnl_percent,
        "by_pnl_amount": by_pnl_amount,
        "message": (
            f"Top performers: {by_pnl_percent[0]['name']} ({by_pnl_percent[0]['pnl_percent']:+.1f}%)"
            if by_pnl_percent
            else "No holdings with P&L data yet. Add invested and current values."
        ),
    }


async def compute_investment_allocation(session: AsyncSession, user_id: UUID) -> dict:
    entries = await _holding_entries(session, user_id)
    physical = await _physical_assets(session, user_id)
    type_totals: dict[str, float] = {}
    for e in entries:
        if e["type"] in HOLDINGS_TYPES or e["type"] in PRIMARY_TYPES | {"wallet"}:
            label = _type_label(e["type"])
            type_totals[label] = type_totals.get(label, 0) + e["current_value"]
    for p in physical:
        label = (p.get("asset_type") or "Physical Asset").replace("_", " ").title()
        type_totals[label] = type_totals.get(label, 0) + p["current_value"]
    total = sum(type_totals.values())
    allocation = {
        k: round(v / total * 100, 1) if total else 0
        for k, v in sorted(type_totals.items(), key=lambda x: x[1], reverse=True)
    }
    top_accounts = sorted(
        [e for e in entries if e["type"] in HOLDINGS_TYPES],
        key=lambda x: x["current_value"],
        reverse=True,
    )[:TOP_N]
    return {
        "total_invested": round(total, 2),
        "allocation": allocation,
        "pie_by_type": [{"name": k, "value": round(v, 2)} for k, v in type_totals.items()],
        "top_accounts": top_accounts,
        "message": (
            "Portfolio allocation across holdings and assets."
            if total
            else "Add investment accounts or assets to see allocation."
        ),
    }


async def compute_sip_status(session: AsyncSession, user_id: UUID) -> dict:
    today = date.today()
    month_name = today.strftime("%B")
    result = await session.execute(
        select(Account).where(Account.user_id == user_id, Account.account_type == "mutual_fund")
    )
    sips: list[dict] = []
    for acc in result.scalars().all():
        if not is_sip_account(acc):
            continue
        schedule = await compute_sip_schedule(session, acc, user_id)
        history = schedule.get("payment_history", [])
        last_paid_on = history[-1]["date"] if history else None
        paid_this_month = False
        if history:
            for p in history:
                pd = date.fromisoformat(p["date"])
                if pd.year == today.year and pd.month == today.month:
                    paid_this_month = True
                    break
        status_label = f"Already paid in {month_name}" if paid_this_month else "Pending this month"
        next_expected_on = None
        if acc.due_day and not paid_this_month:
            next_expected_on = _next_due_date(acc.due_day, today, False).isoformat()
        elif acc.due_day and paid_this_month:
            next_expected_on = _next_due_date(acc.due_day, today, True).isoformat()
        sips.append({
            "account_id": str(acc.id),
            "name": acc.name,
            "emi_amount": float(acc.emi_amount or 0),
            "due_day": acc.due_day,
            "last_paid_on": last_paid_on,
            "next_expected_on": next_expected_on,
            "status_label": status_label,
            "sip_paid_count": schedule.get("sip_paid_count"),
            "sip_pending_count": schedule.get("sip_pending_count"),
        })
    return {
        "sips": sips,
        "message": (
            f"{len(sips)} SIP fund(s) tracked."
            if sips
            else "No SIP mutual funds set up. Add an MF account with investment_mode=sip."
        ),
    }


async def compute_fd_maturity(session: AsyncSession, user_id: UUID) -> dict:
    result = await session.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type.in_(tuple(INVESTMENT_FD_TYPES)),
        )
    )
    items: list[dict] = []
    for acc in result.scalars().all():
        if not acc.start_date or not acc.tenure_months:
            items.append({
                "account_id": str(acc.id),
                "name": acc.name,
                "type": acc.account_type,
                "maturity_date": None,
                "message": "Set start_date and tenure_months to compute maturity",
            })
            continue
        maturity = _add_months(acc.start_date, acc.tenure_months)
        items.append({
            "account_id": str(acc.id),
            "name": acc.name,
            "type": acc.account_type,
            "start_date": acc.start_date.isoformat(),
            "tenure_months": acc.tenure_months,
            "maturity_date": maturity.isoformat(),
        })
    return {
        "deposits": items,
        "message": (
            f"{len(items)} FD/RD account(s)."
            if items
            else "No fixed or recurring deposits found."
        ),
    }
