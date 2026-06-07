"""
Ledger agent: deterministic tools only (no creative math).
run(session, user_id, action, params) -> result dict.
"""
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction, Account, Asset, RecurringBill
from app.services.account_balances import compute_account_metrics, liability_outstanding
from app.services.loan_schedule import compute_loan_schedule
from app.services.opening_balance import read_opening_balance, upsert_opening_balance
from app.services.account_types import (
    ACCOUNT_TYPES,
    BANK_DETAIL_TYPES,
    DERIVED_TYPES,
    HOLDINGS_TYPES,
    INVESTMENT_TYPES,
    LIMIT_ACCOUNT_TYPES,
    LOAN_DETAIL_TYPES,
    LOAN_TYPES,
    OPENING_BALANCE_TYPES,
    PARENT_LINKABLE_TYPES,
    PARENT_REQUIRED_TYPES,
    PRIMARY_TYPES,
    SANCTIONED_ACCOUNT_TYPES,
)
from app.services.mf_investment_mode import is_sip_account
from app.services.bank_account_details import (
    apply_bank_fields,
    clear_bank_fields,
    normalize_ifsc,
    normalize_optional_text,
    validate_bank_details,
)
from app.services.net_worth import compute_net_worth
from app.services.spending import compute_period_spending, spending_filters, income_filters
from app.services.transaction_semantics import (
    NwImpact,
    classify_transaction,
    nw_impact_for_expense,
    nw_impact_for_income,
)

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
    if action == "portfolio_summary":
        return await _portfolio_summary(session, user_id)
    if action == "portfolio_pnl_drilldown":
        return await _portfolio_pnl_drilldown(session, user_id)
    if action == "sip_status_query":
        return await _sip_status_query(session, user_id)
    if action == "fd_maturity_query":
        return await _fd_maturity_query(session, user_id)
    if action == "upcoming_obligations":
        return await _upcoming_obligations(session, user_id)
    if action == "loan_emi_summary":
        return await _loan_emi_summary(session, user_id)
    if action == "propose_recurring_bill":
        return await _propose_recurring_bill(session, user_id, params, default_account_id)
    if action == "insert_recurring_bill":
        return await _insert_recurring_bill(session, user_id, params, default_account_id)
    if action == "propose_transfer":
        return await _propose_transfer(session, user_id, params, default_account_id)
    if action == "insert_transfer":
        return await _insert_transfer(session, user_id, params, default_account_id)
    if action == "vendor_spending_history":
        return await _vendor_spending_history(session, user_id, params)
    if action == "unusual_spending_alert":
        return await _unusual_spending_alert(session, user_id, params)
    if action == "create_account":
        return await _create_account(session, user_id, params)
    if action == "propose_account":
        return await _propose_account(session, user_id, params)
    if action == "insert_account":
        return await _create_account(session, user_id, params)
    if action == "explain_transaction":
        return await _explain_transaction(session, user_id, params)
    if action == "propose_recategorize":
        return await _propose_recategorize(session, user_id, params)
    if action == "insert_recategorize":
        return await _insert_recategorize(session, user_id, params)
    if action == "list_accounts":
        return await _list_accounts(session, user_id, params)
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
    target_emi = params.get("target_emi")
    hypothetical = params.get("hypothetical_monthly_income")
    return await calculate_affordability(
        session,
        user_id,
        target_emi=float(target_emi) if target_emi is not None else None,
        hypothetical_monthly_income=float(hypothetical) if hypothetical is not None else None,
    )


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
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type.in_(tuple(LOAN_TYPES)),
        )
    )
    rows = list(lr.scalars().all())
    total_debt = 0.0
    total_emi = 0.0
    for acc in rows:
        outstanding = await liability_outstanding(session, acc.id, user_id)
        total_debt += float(outstanding)
        total_emi += float(acc.emi_amount or 0)
    months = int(total_debt / total_emi) if total_emi > 0 else 0
    return {
        "total_debt": total_debt,
        "strategy": "Avalanche",
        "recommended_monthly_payment": total_emi,
        "months_to_payoff": months,
        "message": f"Total debt ₹{total_debt:,.0f} across {len(rows)} loan account(s).",
    }


async def _investment_allocation(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    from app.services.portfolio_summary import compute_investment_allocation
    return await compute_investment_allocation(session, user_id)


async def _portfolio_summary(session: AsyncSession, user_id: UUID) -> dict:
    from app.services.portfolio_summary import compute_portfolio_summary
    return await compute_portfolio_summary(session, user_id)


async def _portfolio_pnl_drilldown(session: AsyncSession, user_id: UUID) -> dict:
    from app.services.portfolio_summary import compute_pnl_drilldown
    return await compute_pnl_drilldown(session, user_id)


async def _sip_status_query(session: AsyncSession, user_id: UUID) -> dict:
    from app.services.portfolio_summary import compute_sip_status
    return await compute_sip_status(session, user_id)


async def _fd_maturity_query(session: AsyncSession, user_id: UUID) -> dict:
    from app.services.portfolio_summary import compute_fd_maturity
    return await compute_fd_maturity(session, user_id)


async def _upcoming_obligations(session: AsyncSession, user_id: UUID) -> dict:
    from app.services.obligations import compute_upcoming_obligations
    return await compute_upcoming_obligations(session, user_id)


async def _loan_emi_summary(session: AsyncSession, user_id: UUID) -> dict:
    from app.services.obligations import compute_loan_emi_summary
    return await compute_loan_emi_summary(session, user_id)


async def _resolve_investment_account(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
) -> Account:
    account_id = (
        params.get("to_account_id")
        or params.get("investment_account_id")
        or params.get("account_id")
    )
    if account_id is not None:
        try:
            account_id = UUID(account_id) if isinstance(account_id, str) else account_id
        except Exception:
            account_id = None
    if account_id is not None:
        result = await session.execute(
            select(Account).where(
                Account.id == account_id,
                Account.user_id == user_id,
                Account.account_type.in_(tuple(HOLDINGS_TYPES)),
            )
        )
        account = result.scalar_one_or_none()
        if account:
            return account
        raise LedgerError("Investment account not found or not yours.")

    result = await session.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type.in_(tuple(HOLDINGS_TYPES)),
        )
    )
    accounts = list(result.scalars().all())
    if not accounts:
        raise LedgerError("No investment account found. Create a mutual fund or SIP account first.")

    name_hint = (
        params.get("investment_name")
        or params.get("mf_name")
        or params.get("account_name")
        or ""
    ).strip()
    if name_hint:
        lower = name_hint.lower()
        matches = [a for a in accounts if lower in (a.name or "").lower()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(a.name for a in matches)
            raise LedgerError(f"Multiple accounts match '{name_hint}': {names}. Be more specific.")

    sip_accounts = [a for a in accounts if is_sip_account(a)]
    if len(sip_accounts) == 1:
        return sip_accounts[0]
    if len(accounts) == 1:
        return accounts[0]
    names = ", ".join(a.name for a in accounts)
    raise LedgerError(f"Which investment account? You have: {names}")


async def _resolve_parent_bank(
    session: AsyncSession,
    user_id: UUID,
    investment_account: Account,
) -> Account:
    if not investment_account.parent_account_id:
        raise LedgerError(
            f"{investment_account.name} has no linked bank account. "
            "Link a parent bank account before recording a transfer."
        )
    result = await session.execute(
        select(Account).where(
            Account.id == investment_account.parent_account_id,
            Account.user_id == user_id,
        )
    )
    parent = result.scalar_one_or_none()
    if not parent:
        raise LedgerError("Linked parent bank account not found.")
    if parent.account_type not in PRIMARY_TYPES:
        raise LedgerError("Parent account must be a bank or cash account.")
    return parent


async def _propose_transfer(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> dict:
    amount = params.get("amount")
    if amount is None:
        raise LedgerError("Amount is required. Say e.g. 'record SIP 5000 for HDFC MF'.")
    try:
        amount_decimal = abs(Decimal(str(amount)))
    except Exception:
        raise LedgerError("Invalid amount.")
    if amount_decimal <= 0:
        raise LedgerError("Amount must be greater than zero.")

    investment = await _resolve_investment_account(session, user_id, params)
    parent = await _resolve_parent_bank(session, user_id, investment)
    transaction_date = _parse_date(params.get("transaction_date")) or date.today()
    merchant = f"SIP — {investment.name}"

    legs = [
        {
            "account_id": str(parent.id),
            "account_name": parent.name,
            "amount": float(-amount_decimal),
            "nw_impact": NwImpact.transfer.value,
            "merchant": merchant,
            "category": "Investments",
            "transaction_date": transaction_date.isoformat(),
        },
        {
            "account_id": str(investment.id),
            "account_name": investment.name,
            "amount": float(amount_decimal),
            "nw_impact": NwImpact.transfer.value,
            "merchant": merchant,
            "category": "Investments",
            "transaction_date": transaction_date.isoformat(),
        },
    ]
    summary = (
        f"Record SIP transfer ₹{amount_decimal:,.0f} from {parent.name} "
        f"to {investment.name} on {transaction_date}?"
    )
    return {
        "preview": True,
        "summary": summary,
        "legs": legs,
        "amount": float(amount_decimal),
        "from_account_id": str(parent.id),
        "to_account_id": str(investment.id),
        "transaction_date": transaction_date.isoformat(),
        "merchant": merchant,
    }


async def _insert_transfer(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> dict:
    legs = params.get("legs")
    if not legs or len(legs) < 2:
        preview = await _propose_transfer(session, user_id, params, default_account_id)
        legs = preview["legs"]

    transaction_date = _parse_date(params.get("transaction_date")) or _parse_date(legs[0].get("transaction_date")) or date.today()
    created_ids: list[str] = []
    txns: list[Transaction] = []

    for leg in legs:
        account_id = leg.get("account_id")
        if not account_id:
            raise LedgerError("Missing account_id in transfer leg.")
        try:
            account_uuid = UUID(account_id) if isinstance(account_id, str) else account_id
        except Exception:
            raise LedgerError("Invalid account_id in transfer leg.")
        result = await session.execute(
            select(Account).where(Account.id == account_uuid, Account.user_id == user_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise LedgerError("Transfer account not found or not yours.")
        amount_decimal = Decimal(str(leg.get("amount")))
        if amount_decimal == 0:
            raise LedgerError("Transfer leg amount cannot be zero.")
        txn = Transaction(
            user_id=user_id,
            account_id=account.id,
            amount=amount_decimal,
            currency=params.get("currency", "INR"),
            transaction_date=transaction_date,
            merchant=leg.get("merchant") or params.get("merchant"),
            category=leg.get("category") or "Investments",
            source=params.get("source", "ai_extracted"),
            nw_impact=NwImpact.transfer.value,
        )
        session.add(txn)
        txns.append(txn)

    await session.commit()
    for txn in txns:
        await session.refresh(txn)
        created_ids.append(str(txn.id))

    investment_name = legs[1].get("account_name", "investment")
    amount_abs = abs(float(legs[1].get("amount", 0)))
    summary = (
        f"Recorded SIP transfer ₹{amount_abs:,.0f} to {investment_name} "
        f"on {transaction_date}."
    )
    return {
        "created_ids": created_ids,
        "created_id": created_ids[-1] if created_ids else None,
        "legs": legs,
        "summary": summary,
        "message": summary,
        "transaction_date": transaction_date.isoformat(),
        "committed": True,
    }


async def _propose_recurring_bill(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> dict:
    name = (params.get("name") or params.get("merchant") or "").strip()
    if not name:
        raise LedgerError("Bill name is required. Say e.g. 'add recurring bill Netflix 499'.")
    amount = params.get("amount")
    if amount is None:
        raise LedgerError("Amount is required for recurring bill.")
    try:
        amount_decimal = -abs(Decimal(str(amount)))
    except Exception:
        raise LedgerError("Invalid amount.")
    account = await _resolve_account(session, user_id, params, default_account_id)
    frequency = (params.get("frequency") or "monthly").strip().lower()
    if frequency not in ("monthly", "weekly"):
        raise LedgerError("frequency must be monthly or weekly.")
    due_day = params.get("due_day")
    weekday = params.get("weekday")
    category = params.get("category")
    return {
        "name": name,
        "amount": float(amount_decimal),
        "frequency": frequency,
        "due_day": int(due_day) if due_day is not None else None,
        "weekday": int(weekday) if weekday is not None else None,
        "category": category,
        "account_id": str(account.id),
        "account_name": account.name,
        "preview": True,
        "summary": (
            f"Add recurring bill “{name}” ₹{abs(amount_decimal):,.0f} "
            f"({frequency}) from {account.name}?"
        ),
    }


async def _insert_recurring_bill(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
    default_account_id: UUID | None,
) -> dict:
    name = (params.get("name") or "").strip()
    if not name:
        raise LedgerError("Bill name is required.")
    amount = params.get("amount")
    if amount is None:
        raise LedgerError("Amount is required.")
    amount_decimal = -abs(Decimal(str(amount)))
    account = await _resolve_account(session, user_id, params, default_account_id)
    frequency = (params.get("frequency") or "monthly").strip().lower()
    if frequency not in ("monthly", "weekly"):
        raise LedgerError("frequency must be monthly or weekly.")
    bill = RecurringBill(
        user_id=user_id,
        account_id=account.id,
        name=name,
        amount=amount_decimal,
        frequency=frequency,
        due_day=int(params["due_day"]) if params.get("due_day") is not None else None,
        weekday=int(params["weekday"]) if params.get("weekday") is not None else None,
        category=params.get("category"),
        is_active=True,
    )
    session.add(bill)
    await session.commit()
    await session.refresh(bill)
    summary = f"Added recurring bill “{name}” ₹{abs(amount_decimal):,.0f} ({frequency})."
    return {
        "created_id": str(bill.id),
        "name": name,
        "amount": float(amount_decimal),
        "frequency": frequency,
        "account_id": str(account.id),
        "account_name": account.name,
        "summary": summary,
        "message": summary,
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


async def _account_dict(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
    txn_count: int = 0,
) -> dict:
    metrics = await compute_account_metrics(session, account, user_id)
    result = {
        "id": str(account.id),
        "account_type": account.account_type,
        "name": account.name,
        "institution": account.institution,
        "loan_type": account.loan_type,
        "loan_type_description": account.loan_type_description,
        "credit_limit": float(account.credit_limit) if account.credit_limit is not None else None,
        "sanctioned_amount": float(account.sanctioned_amount) if account.sanctioned_amount is not None else None,
        "emi_amount": float(account.emi_amount) if account.emi_amount is not None else None,
        "tenure_months": account.tenure_months,
        "currency": account.currency or "INR",
        "parent_account_id": str(account.parent_account_id) if account.parent_account_id else None,
        "transaction_count": txn_count,
        "balance": metrics["balance"],
        "credit_used": metrics["credit_used"],
        "credit_remaining": metrics["credit_remaining"],
        "outstanding": metrics["outstanding"],
        "amount_paid": metrics["amount_paid"],
        "opening_balance": await read_opening_balance(session, account.id, user_id),
        "account_number": account.account_number,
        "ifsc_code": account.ifsc_code,
        "branch": account.branch,
        "account_notes": account.account_notes,
    }
    if account.account_type in LOAN_TYPES:
        schedule = await compute_loan_schedule(session, account, user_id)
        result["emi_paid_count"] = schedule["emi_paid_count"]
        result["emi_pending_count"] = schedule["emi_pending_count"]
        result["payment_history"] = schedule["payment_history"]
    return result


async def _create_account(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    params = await _auto_resolve_parent(session, user_id, params)
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
    if account_type in PARENT_REQUIRED_TYPES:
        if parent_uuid is None:
            raise LedgerError("credit_card, loan, and liquid investment accounts require parent_account_id (linked bank/cash).")
        pres = await session.execute(
            select(Account).where(Account.id == parent_uuid, Account.user_id == user_id)
        )
        parent = pres.scalar_one_or_none()
        if not parent or parent.account_type not in PRIMARY_TYPES:
            raise LedgerError("parent_account_id must reference a bank or cash account.")
    elif parent_uuid is not None:
        if account_type not in PARENT_LINKABLE_TYPES:
            raise LedgerError("parent_account_id applies only to derived accounts.")
        pres = await session.execute(
            select(Account).where(Account.id == parent_uuid, Account.user_id == user_id)
        )
        parent = pres.scalar_one_or_none()
        if not parent or parent.account_type not in PRIMARY_TYPES:
            raise LedgerError("parent_account_id must reference a bank or cash account.")
    elif account_type in PRIMARY_TYPES:
        pass
    institution = params.get("institution")
    institution = institution.strip() if isinstance(institution, str) and institution.strip() else None
    credit_limit = params.get("credit_limit")
    if credit_limit is not None:
        if account_type not in LIMIT_ACCOUNT_TYPES:
            raise LedgerError("credit_limit applies only to credit_card accounts.")
        try:
            credit_limit = Decimal(str(credit_limit))
            if credit_limit < 0:
                raise ValueError
        except Exception:
            raise LedgerError("Invalid credit_limit.")
    else:
        credit_limit = None
    sanctioned = params.get("sanctioned_amount")
    if sanctioned is not None:
        if account_type not in SANCTIONED_ACCOUNT_TYPES:
            raise LedgerError("sanctioned_amount applies only to loan accounts.")
        try:
            sanctioned = Decimal(str(sanctioned))
            if sanctioned < 0:
                raise ValueError
        except Exception:
            raise LedgerError("Invalid sanctioned_amount.")
    else:
        sanctioned = None
    opening_balance = params.get("opening_balance")
    if opening_balance is not None:
        if account_type not in OPENING_BALANCE_TYPES:
            raise LedgerError("opening_balance applies only to bank, cash, holdings, and EPF accounts.")
        try:
            opening_balance = float(opening_balance)
            if opening_balance < 0:
                raise ValueError
        except Exception:
            raise LedgerError("Invalid opening_balance.")
    loan_type = params.get("loan_type")
    loan_type_description = params.get("loan_type_description")
    if loan_type is not None:
        if account_type not in LOAN_TYPES:
            raise LedgerError("loan_type applies only to loan accounts.")
        loan_type = str(loan_type).strip().lower()
        if loan_type not in LOAN_DETAIL_TYPES:
            raise LedgerError(f"loan_type must be one of: {', '.join(LOAN_DETAIL_TYPES)}")
    else:
        loan_type = None
    if account_type in LOAN_TYPES and loan_type == "other":
        if not loan_type_description or not str(loan_type_description).strip():
            raise LedgerError("loan_type_description is required when loan_type is other.")
    emi_amount = params.get("emi_amount")
    emi_dec = Decimal(str(emi_amount)) if emi_amount is not None else None
    interest_rate = params.get("interest_rate")
    ir_dec = Decimal(str(interest_rate)) if interest_rate is not None else None
    tenure_months = params.get("tenure_months")
    due_day = params.get("due_day")
    currency = (params.get("currency") or "INR").strip().upper()
    account_number = params.get("account_number")
    ifsc_code = params.get("ifsc_code")
    branch = params.get("branch")
    account_notes = params.get("account_notes")
    try:
        validate_bank_details(
            account_type,
            account_number=account_number,
            ifsc_code=ifsc_code,
            branch=branch,
            account_notes=account_notes,
        )
    except ValueError as exc:
        raise LedgerError(str(exc)) from exc
    account = Account(
        user_id=user_id,
        account_type=account_type,
        name=name,
        institution=institution,
        loan_type=loan_type,
        loan_type_description=str(loan_type_description).strip() if loan_type_description else None,
        credit_limit=credit_limit,
        sanctioned_amount=sanctioned,
        interest_rate=ir_dec,
        emi_amount=emi_dec,
        tenure_months=int(tenure_months) if tenure_months is not None else None,
        due_day=int(due_day) if due_day is not None else None,
        currency=currency,
        parent_account_id=parent_uuid,
        account_number=normalize_optional_text(account_number),
        ifsc_code=normalize_ifsc(ifsc_code),
        branch=normalize_optional_text(branch),
        account_notes=normalize_optional_text(account_notes),
    )
    if account_type not in BANK_DETAIL_TYPES:
        clear_bank_fields(account)
    session.add(account)
    await session.flush()
    if opening_balance is not None and opening_balance > 0:
        await upsert_opening_balance(session, account, user_id, opening_balance)
    await session.commit()
    await session.refresh(account)
    txn_count_result = await session.execute(
        select(func.count(Transaction.id)).where(
            Transaction.account_id == account.id, Transaction.user_id == user_id
        )
    )
    txn_count = int(txn_count_result.scalar_one() or 0)
    acc = await _account_dict(session, account, user_id, txn_count)
    limit_note = ""
    if credit_limit and account_type == "credit_card":
        limit_note = f" (limit ₹{float(credit_limit):,.0f})"
    elif sanctioned and account_type in LOAN_TYPES:
        limit_note = f" (sanctioned ₹{float(sanctioned):,.0f})"
    return {
        **acc,
        "created_id": acc["id"],
        "message": f"Added {account_type.replace('_', ' ')} account “{name}”{limit_note}.",
    }


async def _auto_resolve_parent(session: AsyncSession, user_id: UUID, params: dict) -> dict:
    """For investment accounts without parent_account_id, auto-find the first bank account."""
    if params.get("parent_account_id"):
        return params
    account_type = (params.get("account_type") or "bank").lower()
    if account_type not in PARENT_REQUIRED_TYPES:
        return params
    result = await session.execute(
        select(Account)
        .where(Account.user_id == user_id, Account.account_type == "bank")
        .order_by(Account.created_at.asc())
        .limit(1)
    )
    bank = result.scalar_one_or_none()
    if bank:
        return {**params, "parent_account_id": str(bank.id)}
    return params


async def _propose_account(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
) -> dict:
    params = await _auto_resolve_parent(session, user_id, params)
    account_type = (params.get("account_type") or "bank").strip().lower()
    name = (params.get("name") or "").strip()
    if account_type not in ACCOUNT_TYPES:
        raise LedgerError(f"account_type must be one of: {', '.join(ACCOUNT_TYPES)}")
    investment_mode = params.get("investment_mode")
    emi_amount = params.get("emi_amount")
    display_name = name or "(name required)"
    summary_parts = [f'{account_type.replace("_", " ")} \u201c{display_name}\u201d']
    if investment_mode:
        summary_parts.append(f"mode={investment_mode}")
    if emi_amount:
        summary_parts.append(f"SIP ₹{float(emi_amount):,.0f}/mo")
    if params.get("loan_type"):
        summary_parts.append(f"type={params['loan_type']}")
    if params.get("emi_amount") and account_type in LOAN_TYPES:
        summary_parts.append(f"EMI ₹{float(params['emi_amount']):,.0f}")
    summary = f"Create account: {' · '.join(summary_parts)}?"
    return {
        "preview": True,
        "summary": summary,
        "account_type": account_type,
        "name": name,
        **{k: params[k] for k in (
            "institution", "loan_type", "credit_limit", "sanctioned_amount",
            "emi_amount", "tenure_months", "interest_rate", "due_day",
            "start_date", "investment_mode", "opening_balance",
            "parent_account_id", "currency",
        ) if params.get(k) is not None},
    }


async def _explain_transaction(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
) -> dict:
    merchant = params.get("merchant") or params.get("description")
    limit = int(params.get("limit") or 5)

    q = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(limit)
    )
    if merchant:
        lower = merchant.lower()
        q = q.where(Transaction.merchant.ilike(f"%{lower}%"))

    result = await session.execute(q)
    rows = result.scalars().all()
    if not rows:
        msg = f"No transactions found{f' for {merchant}' if merchant else ''}."
        return {"transactions": [], "message": msg}

    items = [
        {
            "id": str(t.id),
            "date": t.transaction_date.isoformat(),
            "merchant": t.merchant,
            "category": t.category,
            "amount": float(t.amount),
            "nw_impact": t.nw_impact,
            "account_id": str(t.account_id),
        }
        for t in rows
    ]
    msg = f"Found {len(items)} transaction(s)" + (f" for {merchant}" if merchant else "") + "."
    return {"transactions": items, "message": msg}


async def _propose_recategorize(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
) -> dict:
    transaction_id = params.get("transaction_id")
    merchant = params.get("merchant") or params.get("description")
    new_category = (params.get("new_category") or params.get("category") or "").strip()
    if not new_category:
        raise LedgerError("New category is required. Say e.g. 'recategorize Netflix to Entertainment'.")

    if transaction_id:
        try:
            tid = UUID(str(transaction_id))
        except Exception:
            raise LedgerError("Invalid transaction_id.")
        result = await session.execute(
            select(Transaction).where(Transaction.id == tid, Transaction.user_id == user_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise LedgerError("Transaction not found.")
    elif merchant:
        result = await session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id, Transaction.merchant.ilike(f"%{merchant.lower()}%"))
            .order_by(Transaction.transaction_date.desc())
            .limit(1)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise LedgerError(f"No transactions found for '{merchant}'.")
    else:
        raise LedgerError("Specify a merchant name or transaction_id to recategorize.")

    summary = (
        f'Recategorize \u201c{txn.merchant or "transaction"}\u201d '
        f"from {txn.category or 'uncategorized'} \u2192 {new_category} "
        f"(\u20b9{abs(float(txn.amount)):,.0f} on {txn.transaction_date})?"
    )
    return {
        "preview": True,
        "transaction_id": str(txn.id),
        "merchant": txn.merchant,
        "old_category": txn.category,
        "new_category": new_category,
        "amount": float(txn.amount),
        "transaction_date": txn.transaction_date.isoformat(),
        "summary": summary,
    }


async def _insert_recategorize(
    session: AsyncSession,
    user_id: UUID,
    params: dict,
) -> dict:
    transaction_id = params.get("transaction_id")
    if not transaction_id:
        raise LedgerError("transaction_id is required to recategorize.")
    try:
        tid = UUID(str(transaction_id))
    except Exception:
        raise LedgerError("Invalid transaction_id.")
    result = await session.execute(
        select(Transaction).where(Transaction.id == tid, Transaction.user_id == user_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise LedgerError("Transaction not found.")
    new_category = (params.get("new_category") or params.get("category") or "").strip()
    if not new_category:
        raise LedgerError("New category is required.")
    old_category = txn.category
    txn.category = new_category
    await session.commit()
    await session.refresh(txn)
    summary = f'Recategorized \u201c{txn.merchant or "transaction"}\u201d to {new_category}.'
    return {
        "transaction_id": str(txn.id),
        "merchant": txn.merchant,
        "old_category": old_category,
        "new_category": new_category,
        "amount": float(txn.amount),
        "summary": summary,
        "message": summary,
    }


async def _list_accounts(session: AsyncSession, user_id: UUID, params: dict | None = None) -> dict:
    params = params or {}
    q = select(Account).where(Account.user_id == user_id)
    account_type_filter = params.get("account_type")
    if account_type_filter:
        q = q.where(Account.account_type == str(account_type_filter).strip().lower())
    result = await session.execute(q.order_by(Account.created_at.asc()))
    accounts = result.scalars().all()
    counts_result = await session.execute(
        select(Transaction.account_id, func.count(Transaction.id))
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.account_id)
    )
    counts = {row[0]: int(row[1]) for row in counts_result.all()}
    items = [await _account_dict(session, a, user_id, counts.get(a.id, 0)) for a in accounts]
    type_label = account_type_filter.replace("_", " ").upper() if account_type_filter else None
    if not items:
        if type_label:
            return {
                "accounts": [],
                "message": f"You don't have any {type_label} accounts yet. Add one from Accounts or ask me to create one.",
            }
        return {"accounts": [], "message": "You have no accounts yet. Add one from Accounts or ask me to create one."}
    lines = []
    for a in items:
        label = a["account_type"].replace("_", " ")
        if a.get("loan_type"):
            label = f"{label} ({a['loan_type']})"
        inst = f" ({a['institution']})" if a.get("institution") else ""
        extra = ""
        if a.get("balance") is not None:
            extra = f", balance ₹{a['balance']:,.0f}"
        elif a.get("credit_used") is not None:
            parts = [f"used ₹{a['credit_used']:,.0f}"]
            if a.get("credit_remaining") is not None:
                parts.append(f"remaining ₹{a['credit_remaining']:,.0f}")
            extra = ", " + " · ".join(parts)
        elif a.get("outstanding") is not None:
            extra = f", outstanding ₹{a['outstanding']:,.0f}"
        txns = a.get("transaction_count", 0)
        lines.append(f"• {a['name']}{inst} — {label}{extra} — {txns} transactions")
    header = f"Your {type_label} accounts:" if type_label else "Your accounts:"
    return {"accounts": items, "message": header + "\n" + "\n".join(lines)}


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
    if "loan_type" in params:
        lt = params.get("loan_type")
        if lt is None:
            account.loan_type = None
        else:
            lt = str(lt).strip().lower()
            if account.account_type not in LOAN_TYPES:
                raise LedgerError("loan_type applies only to loan accounts.")
            if lt not in LOAN_DETAIL_TYPES:
                raise LedgerError(f"loan_type must be one of: {', '.join(LOAN_DETAIL_TYPES)}")
            account.loan_type = lt
    if "sanctioned_amount" in params:
        sa = params.get("sanctioned_amount")
        account.sanctioned_amount = None if sa is None else Decimal(str(sa))
    if "emi_amount" in params:
        em = params.get("emi_amount")
        account.emi_amount = None if em is None else Decimal(str(em))
    if "interest_rate" in params:
        ir = params.get("interest_rate")
        account.interest_rate = None if ir is None else Decimal(str(ir))
    if "tenure_months" in params:
        account.tenure_months = params.get("tenure_months")
    if "loan_type_description" in params:
        desc = params.get("loan_type_description")
        account.loan_type_description = desc.strip() if isinstance(desc, str) and desc.strip() else None
    if params.get("currency"):
        account.currency = str(params["currency"]).strip().upper()
    bank_fields_set = {k for k in ("account_number", "ifsc_code", "branch", "account_notes") if k in params}
    if bank_fields_set:
        try:
            apply_bank_fields(
                account,
                account_number=params.get("account_number"),
                ifsc_code=params.get("ifsc_code"),
                branch=params.get("branch"),
                account_notes=params.get("account_notes"),
                fields_set=bank_fields_set,
            )
            validate_bank_details(
                account.account_type,
                account_number=account.account_number,
                ifsc_code=account.ifsc_code,
                branch=account.branch,
                account_notes=account.account_notes,
            )
        except ValueError as exc:
            raise LedgerError(str(exc)) from exc
    if account.account_type not in LIMIT_ACCOUNT_TYPES:
        account.credit_limit = None
    if account.account_type not in SANCTIONED_ACCOUNT_TYPES:
        account.sanctioned_amount = None
        account.interest_rate = None
        account.emi_amount = None
        account.tenure_months = None
        account.loan_type = None
        account.loan_type_description = None
    if account.account_type not in BANK_DETAIL_TYPES:
        clear_bank_fields(account)
    if account.credit_limit is not None and account.credit_limit < 0:
        raise LedgerError("credit_limit cannot be negative.")
    if "opening_balance" in params:
        ob = params.get("opening_balance")
        if ob is not None:
            if account.account_type not in OPENING_BALANCE_TYPES:
                raise LedgerError("opening_balance applies only to bank, cash, holdings, and EPF accounts.")
            try:
                ob = float(ob)
                if ob < 0:
                    raise ValueError
            except Exception:
                raise LedgerError("Invalid opening_balance.")
        await upsert_opening_balance(session, account, user_id, ob)
    await session.commit()
    await session.refresh(account)
    txn_count = await session.execute(
        select(func.count(Transaction.id)).where(
            Transaction.account_id == account.id, Transaction.user_id == user_id
        )
    )
    acc = await _account_dict(session, account, user_id, int(txn_count.scalar_one() or 0))
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
