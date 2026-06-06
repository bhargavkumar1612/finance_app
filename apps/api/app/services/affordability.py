from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction, Liability
from app.services.spending import average_monthly_spending, income_filters


async def calculate_affordability(session: AsyncSession, user_id: UUID) -> dict:
    """
    Affordability from income (nw_impact) and spending (nw_impact), not raw debits.
    EMI burden from Liability rows only — no double-count with liability_payment txns.
    """
    three_months_ago = date.today() - timedelta(days=90)
    today = date.today()

    income_q = select(func.sum(Transaction.amount)).where(*income_filters(user_id, three_months_ago, today))
    income_res = await session.execute(income_q)
    total_income_3m = income_res.scalar_one_or_none() or Decimal(0)
    avg_monthly_income = float(total_income_3m / 3)

    avg_monthly_spend = await average_monthly_spending(session, user_id, three_months_ago, today)

    emi_q = select(func.sum(Liability.emi)).where(Liability.user_id == user_id)
    emi_res = await session.execute(emi_q)
    total_existing_emi = float(emi_res.scalar_one_or_none() or Decimal(0))

    max_allowable_emi = avg_monthly_income * 0.50
    safe_new_emi = max(0.0, max_allowable_emi - total_existing_emi)
    surplus = avg_monthly_income - avg_monthly_spend - total_existing_emi

    if avg_monthly_income == 0:
        risk_level = "unknown"
        message = "Could not find income in the last 3 months. Import a salary statement for accurate affordability."
    elif surplus < safe_new_emi:
        safe_new_emi = max(0.0, surplus)
        risk_level = "high"
        message = f"Your spending is high. Safe new EMI: ₹{safe_new_emi:,.2f} based on surplus."
    elif total_existing_emi > (avg_monthly_income * 0.40):
        risk_level = "medium"
        message = f"High existing debt. You can add EMI up to ₹{safe_new_emi:,.2f}."
    else:
        risk_level = "low"
        message = f"Finances look healthy. Comfortable EMI up to ₹{safe_new_emi:,.2f}."

    return {
        "monthly_income": avg_monthly_income,
        "monthly_spend": avg_monthly_spend,
        "existing_emi": total_existing_emi,
        "surplus": surplus,
        "safe_emi_estimate": safe_new_emi,
        "risk_level": risk_level,
        "message": message,
    }
