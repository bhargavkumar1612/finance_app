from datetime import date
from uuid import UUID

from sqlalchemy import select, String, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction, Liability

async def check_missing_data(session: AsyncSession, user_id: UUID) -> list[str]:
    """
    Rule-based engine to check if essential data or recurring transactions 
    are missing for the current month.
    """
    hints = []
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    # 1. Check for missing salary / income this month
    income_q = select(Transaction.id).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_of_month,
        Transaction.amount > 0,
        (
            Transaction.category.ilike('%salary%') | 
            Transaction.raw_description.ilike('%salary%') | 
            Transaction.merchant.ilike('%salary%')
        )
    ).limit(1)
    
    income_res = await session.execute(income_q)
    if not income_res.scalar_one_or_none():
        hints.append("Add this month's salary")

    # 2. Check for missing rent
    rent_q = select(Transaction.id).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_of_month,
        Transaction.amount < 0,
        (
            Transaction.category.ilike('%rent%') | 
            Transaction.raw_description.ilike('%rent%') | 
            Transaction.merchant.ilike('%rent%')
        )
    ).limit(1)
    
    rent_res = await session.execute(rent_q)
    if not rent_res.scalar_one_or_none():
        hints.append("Log your rent payment")

    # 3. Check for unlogged EMIs against known liabilities
    liability_q = select(Liability.name).where(
        Liability.user_id == user_id,
        Liability.emi > 0
    )
    liability_res = await session.execute(liability_q)
    liabilities = liability_res.scalars().all()
    
    for liability_name in liabilities:
        emi_q = select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_of_month,
            (
                Transaction.merchant.ilike(f'%{liability_name}%') |
                Transaction.raw_description.ilike(f'%{liability_name}%') |
                Transaction.category.ilike('%emi%')
            )
        ).limit(1)
        res = await session.execute(emi_q)
        if not res.scalar_one_or_none():
            hints.append(f"Log EMI for {liability_name}")

    # Limit to top 2 hints to avoid overwhelming the user
    return hints[:2]
