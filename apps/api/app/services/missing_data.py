from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, RecurringBill, Transaction
from app.services.account_types import LOAN_TYPES
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

    loan_q = select(Account.name).where(
        Account.user_id == user_id,
        Account.account_type.in_(tuple(LOAN_TYPES)),
        Account.emi_amount.isnot(None),
        Account.emi_amount > 0,
    )
    for loan_name in (await session.execute(loan_q)).scalars().all():
        emi_q = select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_of_month,
            Transaction.nw_impact == NwImpact.liability_payment.value,
            (
                Transaction.merchant.ilike(f"%{loan_name}%")
                | Transaction.raw_description.ilike(f"%{loan_name}%")
            ),
        ).limit(1)
        if not (await session.execute(emi_q)).scalar_one_or_none():
            hints.append(f"Log EMI for {loan_name}")

    return hints[:2]
