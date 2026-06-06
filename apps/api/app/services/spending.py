"""Shared spending queries — nw_impact=spending only."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction
from app.services.transaction_semantics import NwImpact

SPENDING_IMPACT = NwImpact.spending.value
INCOME_IMPACT = NwImpact.income.value
REFUND_IMPACT = NwImpact.refund.value


def spending_filters(user_id: UUID, start: date, end: date):
    return (
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
        Transaction.nw_impact == SPENDING_IMPACT,
    )


def income_filters(user_id: UUID, start: date, end: date):
    return (
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= end,
        Transaction.nw_impact.in_((INCOME_IMPACT, REFUND_IMPACT)),
    )


async def compute_period_spending(
    session: AsyncSession,
    user_id: UUID,
    start: date,
    end: date,
) -> dict:
    """Total and breakdown for spending-class transactions in a period."""
    base = spending_filters(user_id, start, end)

    cat_q = (
        select(Transaction.category, func.sum(Transaction.amount).label("total"))
        .where(*base)
        .group_by(Transaction.category)
    )
    cat_result = await session.execute(cat_q)
    by_category_raw = {(r.category or "Uncategorized"): float(r.total) for r in cat_result.all()}
    by_category = {k: abs(v) for k, v in by_category_raw.items()}
    total_spend = sum(by_category.values())

    yr_col = extract("year", Transaction.transaction_date)
    mo_col = extract("month", Transaction.transaction_date)
    month_q = (
        select(yr_col.label("yr"), mo_col.label("mo"), func.sum(Transaction.amount).label("total"))
        .where(*base)
        .group_by(yr_col, mo_col)
        .order_by(yr_col, mo_col)
    )
    month_result = await session.execute(month_q)
    by_month: list[dict] = []
    _MONTH_NAMES = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    for row in month_result.all():
        yr, mo = int(row.yr), int(row.mo)
        by_month.append({
            "month": f"{yr}-{mo:02d}",
            "label": f"{_MONTH_NAMES[mo]} {yr}",
            "amount": abs(float(row.total)),
        })

    count_q = select(func.count(Transaction.id)).where(*base)
    txn_count = (await session.execute(count_q)).scalar_one() or 0

    return {
        "total_spend": total_spend,
        "by_category": by_category,
        "by_month": by_month,
        "transaction_count": int(txn_count),
    }


async def average_monthly_spending(
    session: AsyncSession,
    user_id: UUID,
    start: date,
    end: date,
) -> float:
    result = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(*spending_filters(user_id, start, end))
    )
    total = result.scalar_one() or Decimal(0)
    days = max((end - start).days, 1)
    months = days / 30.0
    return float(abs(total) / Decimal(str(max(months, 1))))
