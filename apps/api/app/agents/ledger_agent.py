"""
Ledger agent: deterministic tools only (no creative math).
run(session, user_id, action, params) -> result dict.
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction, Account, Asset, Liability, RecurringBill
from app.services.net_worth import compute_net_worth
from app.services.spending import compute_period_spending, spending_filters, income_filters
from app.services.transaction_semantics import (
    NwImpact,
    classify_transaction,
    nw_impact_for_expense,
    nw_impact_for_income,
)

ACCOUNT_TYPES = ("bank", "credit_card", "wallet", "cash")


class LedgerError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def run(
    session: AsyncSession,
    user_id: UUID,
    action: str,
    params: dict,
    default_account_id: UUID | None = None,
) -> dict:
    """
    Execute one Ledger action. Raises LedgerError on validation failure.
    default_account_id: used for insert_transaction when params don't have account_id.
    """
    if action == "propose_transaction":
        return await _propose_transaction(session, user_id, params, default_account_id)
    if action == "propose_income":
        return await _propose_income(session, user_id, params, default_account_id)
    if action == "insert_transaction":
        return await _insert_transaction(session, user_id, params, default_account_id)
    if action == "insert_income":
        return await _insert_income(session, user_id, params, default_account_id)
    if action == "fetch_transactions":
        return await _fetch_transactions(session, user_id, params)
    if action == "compute_net_worth":
        return await _compute_net_worth(session, user_id)
    if action == "compute_monthly_spend":
        return await _compute_monthly_spend(session, user_id, params)
    if action == "compute_affordability":
        return await _compute_affordability(session, user_id, params)
    
    # Phase 4 Analytical Tools
    if action == "analyze_category_spending":
        return await _analyze_category_spending(session, user_id, params)
    if action == "list_recurring_bills":
        return await _list_recurring_bills(session, user_id)
    if action == "track_subscriptions":
        return await _list_recurring_bills(session, user_id)
    if action == "analyze_cash_flow":
        return await _analyze_cash_flow(session, user_id, params)
    if action == "get_top_expenses":
        return await _get_top_expenses(session, user_id, params)
    if action == "budget_vs_actual":
        return await _budget_vs_actual(session, user_id, params)
    if action == "project_future_balance":
        return await _project_future_balance(session, user_id, params)
    if action == "debt_payoff_planner":
        return await _debt_payoff_planner(session, user_id, params)
    if action == "investment_allocation":
        return await _investment_allocation(session, user_id, params)
    if action == "vendor_spending_history":
        return await _vendor_spending_history(session, user_id, params)
    if action == "unusual_spending_alert":
        return await _unusual_spending_alert(session, user_id, params)
    if action == "create_account":
        return await _create_account(session, user_id, params)
    if action == "list_accounts":
        return await _list_accounts(session, user_id)
    if action == "update_account":
        return await _update_account(session, user_id, params)
    if action == "delete_account":
        return await _delete_account(session, user_id, params)

    raise LedgerError(f"Unknown action: {action}")


def _parse_date(v: str | None) -> date | None:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).split("T")[0])
    except Exception:
        return None


async def _resolve_account(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> Account:
    account_id = params.get("account_id")
    if account_id is not None:
        try:
            account_id = UUID(account_id) if isinstance(account_id, str) else account_id
        except Exception:
            account_id = None
    if account_id is None:
        account_id = default_account_id
    if account_id is None:
        raise LedgerError("No account selected. Create an account first (e.g. Cash) and try again.")
    result = await session.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise LedgerError("Account not found or not yours.")
    return account


async def _propose_transaction(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> dict:
    account = await _resolve_account(session, user_id, params, default_account_id)
    amount = params.get("amount")
    if amount is None:
        raise LedgerError("Missing amount for add expense. Say e.g. 'add 500 for Swiggy'.")
    try:
        amount_decimal = -abs(Decimal(str(amount)))
    except Exception:
        raise LedgerError("Invalid amount.")
    transaction_date = _parse_date(params.get("transaction_date")) or date.today()
    merchant = params.get("merchant")
    category = params.get("category")
    impact = nw_impact_for_expense(
        amount_decimal,
        category=category,
        merchant=merchant,
        raw_description=params.get("raw_description"),
        account_type=account.account_type,
    )
    return {
        "amount": float(amount_decimal),
        "merchant": merchant,
        "category": category,
        "transaction_date": transaction_date.isoformat(),
        "account_id": str(account.id),
        "account_name": account.name,
        "nw_impact": impact.value,
        "preview": True,
        "summary": f"Add expense ₹{abs(amount_decimal)}"
        + (f" for {merchant}" if merchant else "")
        + f" on {transaction_date}?",
    }


async def _propose_income(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> dict:
    account = await _resolve_account(session, user_id, params, default_account_id)
    amount = params.get("amount")
    if amount is None:
        raise LedgerError("Missing amount for income. Say e.g. 'add salary 125000'.")
    try:
        amount_decimal = abs(Decimal(str(amount)))
    except Exception:
        raise LedgerError("Invalid amount.")
    transaction_date = _parse_date(params.get("transaction_date")) or date.today()
    merchant = params.get("merchant") or "Income"
    category = params.get("category") or "Income"
    impact = nw_impact_for_income(
        amount_decimal,
        category=category,
        merchant=merchant,
        raw_description=params.get("raw_description"),
        account_type=account.account_type,
    )
    return {
        "amount": float(amount_decimal),
        "merchant": merchant,
        "category": category,
        "transaction_date": transaction_date.isoformat(),
        "account_id": str(account.id),
        "account_name": account.name,
        "nw_impact": impact.value,
        "preview": True,
        "summary": f"Add income ₹{amount_decimal} on {transaction_date}?",
    }


async def _insert_transaction(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> dict:
    amount = params.get("amount")
    if amount is None:
        raise LedgerError("Missing amount for add expense. Say e.g. 'add 500 for Swiggy'.")
    try:
        amount_decimal = Decimal(str(amount))
    except Exception:
        raise LedgerError("Invalid amount.")
    if amount_decimal >= 0:
        amount_decimal = -abs(amount_decimal)
    transaction_date = _parse_date(params.get("transaction_date")) or date.today()
    account = await _resolve_account(session, user_id, params, default_account_id)
    nw = params.get("nw_impact")
    if nw:
        impact = NwImpact(nw)
    else:
        impact = nw_impact_for_expense(
            amount_decimal,
            category=params.get("category"),
            merchant=params.get("merchant"),
            raw_description=params.get("raw_description"),
            account_type=account.account_type,
        )
    txn = Transaction(
        user_id=user_id,
        account_id=account.id,
        amount=amount_decimal,
        currency=params.get("currency", "INR"),
        transaction_date=transaction_date,
        merchant=params.get("merchant"),
        category=params.get("category"),
        subcategory=params.get("subcategory"),
        raw_description=params.get("raw_description"),
        source=params.get("source", "ai_extracted"),
        confidence=params.get("confidence"),
        nw_impact=impact.value,
    )
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    summary = f"Recorded expense of ₹{abs(amount_decimal)}"
    if txn.merchant:
        summary += f" for {txn.merchant}"
    summary += f" on {transaction_date}."
    return {
        "created_id": str(txn.id),
        "summary": summary,
        "transaction_date": transaction_date.isoformat(),
        "amount": float(amount_decimal),
        "merchant": txn.merchant,
        "category": txn.category,
        "nw_impact": txn.nw_impact,
    }


async def _insert_income(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> dict:
    amount = params.get("amount")
    if amount is None:
        raise LedgerError("Missing amount for income.")
    amount_decimal = abs(Decimal(str(amount)))
    params = {**params, "amount": float(amount_decimal), "source": params.get("source", "ai_extracted")}
    account = await _resolve_account(session, user_id, params, default_account_id)
    transaction_date = _parse_date(params.get("transaction_date")) or date.today()
    impact = NwImpact(params["nw_impact"]) if params.get("nw_impact") else nw_impact_for_income(
        amount_decimal,
        category=params.get("category") or "Income",
        merchant=params.get("merchant"),
        account_type=account.account_type,
    )
    txn = Transaction(
        user_id=user_id,
        account_id=account.id,
        amount=amount_decimal,
        currency=params.get("currency", "INR"),
        transaction_date=transaction_date,
        merchant=params.get("merchant") or "Income",
        category=params.get("category") or "Income",
        source=params.get("source", "ai_extracted"),
        nw_impact=impact.value,
    )
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    summary = f"Recorded income of ₹{amount_decimal} on {transaction_date}."
    return {
        "created_id": str(txn.id),
        "summary": summary,
        "transaction_date": transaction_date.isoformat(),
        "amount": float(amount_decimal),
        "merchant": txn.merchant,
        "category": txn.category,
        "nw_impact": txn.nw_impact,
    }


async def _fetch_transactions(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
) -> dict:
    limit = min(int(params.get("limit", 50)), 200)
    from_date = _parse_date(params.get("from_date"))
    to_date = _parse_date(params.get("to_date"))
    q = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.transaction_date.desc())
    if from_date:
        q = q.where(Transaction.transaction_date >= from_date)
    if to_date:
        q = q.where(Transaction.transaction_date <= to_date)
    q = q.limit(limit)
    result = await session.execute(q)
    rows = result.scalars().all()
    total = sum(1 for _ in rows)
    items = [
        {
            "id": str(t.id),
            "amount": float(t.amount),
            "transaction_date": t.transaction_date.isoformat(),
            "merchant": t.merchant,
            "category": t.category,
        }
        for t in rows
    ]
    return {"transactions": items, "count": total}


async def _compute_net_worth(session: AsyncSession, user_id: UUID) -> dict:
    return await compute_net_worth(session, user_id)


def _spend_period_bounds(period: str, today: date | None = None) -> tuple[date, date, str]:
    """Return (start, end, human label) for a spending analysis period."""
    today = today or date.today()
    if period == "last_month":
        if today.month == 1:
            start = date(today.year - 1, 12, 1)
            end = date(today.year - 1, 12, 31)
        else:
            start = date(today.year, today.month - 1, 1)
            end = date(today.year, today.month, 1) - timedelta(days=1)
        label = start.strftime("%B %Y")
    elif period == "last_12_months":
        start = today - timedelta(days=365)
        end = today
        label = "Last 12 months"
    elif period == "this_year":
        start = date(today.year, 1, 1)
        end = today
        label = f"Year {today.year}"
    elif period == "last_year":
        start = date(today.year - 1, 1, 1)
        end = date(today.year - 1, 12, 31)
        label = f"Year {today.year - 1}"
    else:
        start = date(today.year, today.month, 1)
        end = today
        label = today.strftime("%B %Y")
    return start, end, label


_MONTH_NAMES = (
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


async def _compute_monthly_spend(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
) -> dict:
    period = params.get("period", "this_month")
    start, end, period_label = _spend_period_bounds(period)
    stats = await compute_period_spending(session, user_id, start, end)
    return {
        **stats,
        "period": f"{period_label} ({start.isoformat()} to {end.isoformat()})",
        "period_label": period_label,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


async def _compute_affordability(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
) -> dict:
    from app.services.affordability import calculate_affordability
    return await calculate_affordability(session, user_id)


# ----- Phase 4 Analytical Methods -----

async def _analyze_category_spending(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    category = params.get("category", "General")
    period = params.get("period", "this_month")
    start, end, period_label = _spend_period_bounds(period)
    filters = (
        *spending_filters(user_id, start, end),
        Transaction.category.ilike(f"%{category}%"),
    )
    q = (
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.transaction_date.desc())
        .limit(50)
    )
    result = await session.execute(q)
    rows = result.scalars().all()
    total = sum(abs(float(t.amount)) for t in rows)
    return {
        "category": category,
        "period": period_label,
        "total": total,
        "transactions": [
            {"date": t.transaction_date.isoformat(), "merchant": t.merchant, "amount": abs(float(t.amount))}
            for t in rows
        ],
        "message": f"Spending in {category} for {period_label}: ₹{total:,.2f}.",
    }


async def _list_recurring_bills(session: AsyncSession, user_id: UUID) -> dict:
    result = await session.execute(
        select(RecurringBill).where(RecurringBill.user_id == user_id, RecurringBill.is_active.is_(True))
    )
    bills = list(result.scalars().all())
    items = [
        {
            "service": b.name,
            "name": b.name,
            "amount": float(abs(b.amount)),
            "frequency": b.frequency,
            "category": b.category,
        }
        for b in bills
    ]
    total_monthly = sum(i["amount"] for i in items if i["frequency"] == "monthly")
    return {
        "subscriptions": items,
        "recurring_bills": items,
        "total_monthly": total_monthly,
        "message": f"Found {len(items)} active recurring bill(s)." if items else "No recurring bills defined yet.",
    }


async def _analyze_cash_flow(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    period = params.get("period", "this_month")
    start, end, period_label = _spend_period_bounds(period)
    inc = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(*income_filters(user_id, start, end))
    )
    spend = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(*spending_filters(user_id, start, end))
    )
    total_income = float(inc.scalar_one() or 0)
    total_spending = abs(float(spend.scalar_one() or 0))
    net = total_income - total_spending
    rate = (net / total_income * 100) if total_income else 0
    return {
        "period": period_label,
        "total_income": total_income,
        "total_expense": total_spending,
        "total_spending": total_spending,
        "net_cash_flow": net,
        "savings_rate_pct": round(rate, 1),
        "message": f"Cash flow for {period_label}: income ₹{total_income:,.0f}, spending ₹{total_spending:,.0f}.",
    }


async def _get_top_expenses(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    limit = int(params.get("limit", 5))
    period = params.get("period", "this_month")
    start, end, period_label = _spend_period_bounds(period)
    q = (
        select(Transaction.merchant, func.sum(Transaction.amount).label("total"))
        .where(*spending_filters(user_id, start, end))
        .group_by(Transaction.merchant)
        .order_by(func.sum(Transaction.amount))
        .limit(limit)
    )
    result = await session.execute(q)
    expenses = [
        {"merchant": r.merchant or "Unknown", "amount": abs(float(r.total)), "date": end.isoformat()}
        for r in result.all()
    ]
    return {
        "period": period_label,
        "expenses": expenses,
        "message": f"Top {len(expenses)} merchants by spending in {period_label}.",
    }


async def _budget_vs_actual(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    return {
        "message": "Envelope budgeting (YNAB-style) is coming in a later phase. Use spending analysis for now.",
        "coming_soon": True,
    }


async def _project_future_balance(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    nw = await compute_net_worth(session, user_id)
    cash = nw.get("cash_and_primary", 0)
    bill_result = await session.execute(
        select(func.coalesce(func.sum(RecurringBill.amount), 0)).where(
            RecurringBill.user_id == user_id, RecurringBill.is_active.is_(True)
        )
    )
    upcoming = abs(float(bill_result.scalar_one() or 0))
    projected = cash - upcoming
    return {
        "current_balance": cash,
        "projected_eom_balance": projected,
        "upcoming_bills": upcoming,
        "message": f"Projected primary balance after recurring bills: ₹{projected:,.0f}.",
    }


async def _debt_payoff_planner(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    lr = await session.execute(
        select(Liability).where(Liability.user_id == user_id)
    )
    rows = list(lr.scalars().all())
    total_debt = sum(float(l.outstanding_amount) for l in rows)
    total_emi = sum(float(l.emi or 0) for l in rows)
    months = int(total_debt / total_emi) if total_emi > 0 else 0
    return {
        "total_debt": total_debt,
        "strategy": "Avalanche",
        "recommended_monthly_payment": total_emi,
        "months_to_payoff": months,
        "message": f"Total debt ₹{total_debt:,.0f} across {len(rows)} liability/liabilities.",
    }


async def _investment_allocation(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    ar = await session.execute(select(Asset).where(Asset.user_id == user_id))
    assets = list(ar.scalars().all())
    total = sum(float(a.current_value) for a in assets)
    allocation: dict[str, float] = {}
    for a in assets:
        label = (a.asset_type or "other").replace("_", " ").title()
        pct = (float(a.current_value) / total * 100) if total else 0
        allocation[label] = round(allocation.get(label, 0) + pct, 1)
    return {
        "total_invested": total,
        "allocation": allocation,
        "message": "Portfolio allocation from recorded assets." if assets else "Add assets to see allocation.",
    }


async def _vendor_spending_history(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    merchant = params.get("merchant_name") or params.get("merchant") or "Unknown"
    q = (
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.nw_impact == NwImpact.spending.value,
            Transaction.merchant.ilike(f"%{merchant}%"),
        )
    )
    result = await session.execute(q)
    rows = list(result.scalars().all())
    lifetime = sum(abs(float(t.amount)) for t in rows)
    avg = lifetime / len(rows) if rows else 0
    return {
        "merchant": merchant,
        "lifetime_spend": lifetime,
        "transaction_count": len(rows),
        "average_transaction": avg,
        "message": f"₹{lifetime:,.0f} at {merchant} across {len(rows)} spending transaction(s).",
    }


async def _unusual_spending_alert(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    start, end, _ = _spend_period_bounds("this_month")
    q = (
        select(Transaction.merchant, func.avg(func.abs(Transaction.amount)).label("avg_amt"))
        .where(*spending_filters(user_id, start - timedelta(days=90), start))
        .group_by(Transaction.merchant)
    )
    baselines = {r.merchant: float(r.avg_amt) for r in (await session.execute(q)).all() if r.merchant}
    month_q = select(Transaction).where(*spending_filters(user_id, start, end))
    anomalies = []
    for t in (await session.execute(month_q)).scalars().all():
        base = baselines.get(t.merchant, 0)
        amt = abs(float(t.amount))
        if base > 0 and amt > base * 2.5:
            anomalies.append({
                "merchant": t.merchant,
                "amount": amt,
                "date": t.transaction_date.isoformat(),
                "reason": f"Above typical ₹{base:,.0f} at this merchant",
            })
    return {
        "alerts_found": len(anomalies),
        "anomalies": anomalies[:5],
        "message": f"Detected {len(anomalies)} unusual spending transaction(s) this month.",
    }


def _account_dict(account: Account, txn_count: int = 0) -> dict:
    return {
        "id": str(account.id),
        "account_type": account.account_type,
        "name": account.name,
        "institution": account.institution,
        "credit_limit": float(account.credit_limit) if account.credit_limit is not None else None,
        "currency": account.currency or "INR",
        "parent_account_id": str(account.parent_account_id) if account.parent_account_id else None,
        "transaction_count": txn_count,
    }


async def _create_account(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    account_type = (params.get("account_type") or "bank").strip().lower()
    name = (params.get("name") or "").strip()
    if not name:
        raise LedgerError("Account name is required. Say e.g. 'add HDFC savings account'.")
    if account_type not in ACCOUNT_TYPES:
        raise LedgerError(f"account_type must be one of: {', '.join(ACCOUNT_TYPES)}")
    parent_id = params.get("parent_account_id")
    parent_uuid = None
    if parent_id:
        try:
            parent_uuid = UUID(str(parent_id))
        except Exception:
            raise LedgerError("Invalid parent_account_id.")
    if account_type in ("credit_card", "wallet"):
        if parent_uuid is None:
            raise LedgerError("credit_card and wallet accounts require parent_account_id (linked bank/cash).")
        pres = await session.execute(
            select(Account).where(Account.id == parent_uuid, Account.user_id == user_id)
        )
        parent = pres.scalar_one_or_none()
        if not parent or parent.account_type not in ("bank", "cash"):
            raise LedgerError("parent_account_id must reference a bank or cash account.")
    elif parent_uuid is not None:
        raise LedgerError("parent_account_id applies only to credit_card or wallet accounts.")
    institution = params.get("institution")
    institution = institution.strip() if isinstance(institution, str) and institution.strip() else None
    credit_limit = params.get("credit_limit")
    if credit_limit is not None:
        if account_type != "credit_card":
            raise LedgerError("credit_limit applies only to credit_card accounts.")
        try:
            credit_limit = Decimal(str(credit_limit))
            if credit_limit < 0:
                raise ValueError
        except Exception:
            raise LedgerError("Invalid credit_limit.")
    else:
        credit_limit = None
    currency = (params.get("currency") or "INR").strip().upper()
    account = Account(
        user_id=user_id,
        account_type=account_type,
        name=name,
        institution=institution,
        credit_limit=credit_limit,
        currency=currency,
        parent_account_id=parent_uuid,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    acc = _account_dict(account, 0)
    limit_note = f" (limit ₹{float(credit_limit):,.0f})" if credit_limit else ""
    return {
        **acc,
        "created_id": acc["id"],
        "message": f"Added {account_type.replace('_', ' ')} account “{name}”{limit_note}.",
    }


async def _list_accounts(session: AsyncSession, user_id: UUID) -> dict:
    result = await session.execute(
        select(Account).where(Account.user_id == user_id).order_by(Account.created_at.asc())
    )
    accounts = result.scalars().all()
    counts_result = await session.execute(
        select(Transaction.account_id, func.count(Transaction.id))
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.account_id)
    )
    counts = {row[0]: int(row[1]) for row in counts_result.all()}
    items = [_account_dict(a, counts.get(a.id, 0)) for a in accounts]
    if not items:
        return {"accounts": [], "message": "You have no accounts yet. Add one from Accounts or ask me to create one."}
    lines = []
    for a in items:
        label = a["account_type"].replace("_", " ")
        inst = f" ({a['institution']})" if a.get("institution") else ""
        limit = ""
        if a.get("credit_limit") is not None:
            limit = f", limit ₹{a['credit_limit']:,.0f}"
        txns = a.get("transaction_count", 0)
        lines.append(f"• {a['name']}{inst} — {label}{limit} — {txns} transactions")
    return {"accounts": items, "message": "Your accounts:\n" + "\n".join(lines)}


async def _update_account(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    account_id = params.get("account_id")
    if not account_id:
        raise LedgerError("account_id is required to update an account.")
    try:
        aid = UUID(str(account_id))
    except Exception:
        raise LedgerError("Invalid account_id.")
    result = await session.execute(
        select(Account).where(Account.id == aid, Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise LedgerError("Account not found.")
    if params.get("name"):
        account.name = str(params["name"]).strip()
    if params.get("institution") is not None:
        inst = params.get("institution")
        account.institution = inst.strip() if isinstance(inst, str) and inst.strip() else None
    if params.get("account_type"):
        at = str(params["account_type"]).strip().lower()
        if at not in ACCOUNT_TYPES:
            raise LedgerError(f"account_type must be one of: {', '.join(ACCOUNT_TYPES)}")
        account.account_type = at
    if "credit_limit" in params:
        cl = params.get("credit_limit")
        if cl is None:
            account.credit_limit = None
        else:
            account.credit_limit = Decimal(str(cl))
    if params.get("currency"):
        account.currency = str(params["currency"]).strip().upper()
    if account.account_type != "credit_card":
        account.credit_limit = None
    elif account.credit_limit is not None and account.credit_limit < 0:
        raise LedgerError("credit_limit cannot be negative.")
    await session.commit()
    await session.refresh(account)
    txn_count = await session.execute(
        select(func.count(Transaction.id)).where(
            Transaction.account_id == account.id, Transaction.user_id == user_id
        )
    )
    acc = _account_dict(account, int(txn_count.scalar_one() or 0))
    return {**acc, "message": f"Updated account “{account.name}”."}


async def _delete_account(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    account_id = params.get("account_id")
    if not account_id:
        raise LedgerError("account_id is required to delete an account.")
    try:
        aid = UUID(str(account_id))
    except Exception:
        raise LedgerError("Invalid account_id.")
    result = await session.execute(
        select(Account).where(Account.id == aid, Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise LedgerError("Account not found.")
    name = account.name
    txn_count = await session.execute(
        select(func.count(Transaction.id)).where(
            Transaction.account_id == aid, Transaction.user_id == user_id
        )
    )
    if (txn_count.scalar_one() or 0) > 0:
        raise LedgerError(
            "This account has transactions. Delete them first from Transactions, then remove the account."
        )
    bill_count = await session.execute(
        select(func.count(RecurringBill.id)).where(
            RecurringBill.account_id == aid, RecurringBill.user_id == user_id
        )
    )
    if (bill_count.scalar_one() or 0) > 0:
        raise LedgerError("This account is linked to recurring bills. Remove those first.")
    await session.delete(account)
    await session.commit()
    return {"deleted_id": str(aid), "name": name, "message": f"Deleted account “{name}”."}
