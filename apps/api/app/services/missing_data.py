from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction, Liability, RecurringBill
from app.services.transaction_semantics import NwImpact


async def check_missing_data(session: AsyncSession, user_id: UUID) -> list[str]:
    """Rule-based hints for missing income, rent spending, or EMI logs."""
    hints = []
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    income_q = select(Transaction.id).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_of_month,
        Transaction.nw_impact.in_((NwImpact.income.value, NwImpact.refund.value)),
    ).limit(1)
    if not (await session.execute(income_q)).scalar_one_or_none():
        hints.append("Add this month's salary")

    rent_q = select(Transaction.id).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_of_month,
        Transaction.nw_impact == NwImpact.spending.value,
        (
            Transaction.category.ilike("%rent%")
            | Transaction.category.ilike("%housing%")
            | Transaction.raw_description.ilike("%rent%")
        ),
    ).limit(1)
    if not (await session.execute(rent_q)).scalar_one_or_none():
        hints.append("Log your rent payment")

    liability_q = select(Liability.name).where(Liability.user_id == user_id, Liability.emi > 0)
    for liability_name in (await session.execute(liability_q)).scalars().all():
        emi_q = select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_of_month,
            Transaction.nw_impact == NwImpact.liability_payment.value,
            (
                Transaction.merchant.ilike(f"%{liability_name}%")
                | Transaction.raw_description.ilike(f"%{liability_name}%")
            ),
        ).limit(1)
        if not (await session.execute(emi_q)).scalar_one_or_none():
            hints.append(f"Log EMI for {liability_name}")

    return hints[:2]
