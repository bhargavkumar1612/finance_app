from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction
from app.services.commitments import monthly_commitments_breakdown
from app.services.net_worth import compute_net_worth
from app.services.spending import average_monthly_spending, income_filters


async def calculate_affordability(session: AsyncSession, user_id: UUID) -> dict:
    """
    Affordability from income (nw_impact) and spending (nw_impact), not raw debits.
    EMI burden from loan account emi_amount rows — no double-count with liability_payment txns.
    """
    three_months_ago = date.today() - timedelta(days=90)
    today = date.today()

    income_q = select(func.sum(Transaction.amount)).where(*income_filters(user_id, three_months_ago, today))
    income_res = await session.execute(income_q)
    total_income_3m = income_res.scalar_one_or_none() or Decimal(0)
    avg_monthly_income = float(total_income_3m / 3)

    avg_monthly_spend = await average_monthly_spending(session, user_id, three_months_ago, today)

    commitments = await monthly_commitments_breakdown(session, user_id)
    total_commitments = commitments["total_commitments"]
    loan_emis = commitments["loan_emis"]

    max_allowable_emi = avg_monthly_income * 0.50
    safe_new_emi = max(0.0, max_allowable_emi - total_commitments)
    surplus = avg_monthly_income - avg_monthly_spend - total_commitments

    nw_data = await compute_net_worth(session, user_id)
    net_worth = float(nw_data.get("net_worth", 0))

    if avg_monthly_income == 0:
        risk_level = "unknown"
        message = "Could not find income in the last 3 months. Import a salary statement for accurate affordability."
    elif surplus < safe_new_emi:
        safe_new_emi = max(0.0, surplus)
        risk_level = "high"
        message = (
            f"After spending and all commitments (₹{total_commitments:,.0f}/mo), "
            f"safe new EMI: ₹{safe_new_emi:,.2f}."
        )
    elif total_commitments > (avg_monthly_income * 0.40):
        risk_level = "medium"
        message = (
            f"Commitments use ₹{total_commitments:,.0f}/mo of income. "
            f"You can add EMI up to ₹{safe_new_emi:,.2f}."
        )
    else:
        risk_level = "low"
        message = (
            f"Finances look healthy after ₹{total_commitments:,.0f}/mo commitments. "
            f"Comfortable EMI up to ₹{safe_new_emi:,.2f}."
        )

    return {
        "monthly_income": avg_monthly_income,
        "monthly_spend": avg_monthly_spend,
        "existing_emi": loan_emis,
        "commitments": commitments,
        "total_commitments": total_commitments,
        "surplus": surplus,
        "safe_emi_estimate": safe_new_emi,
        "risk_level": risk_level,
        "net_worth": net_worth,
        "message": message,
    }
