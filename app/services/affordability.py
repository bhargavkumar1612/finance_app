from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction, Liability

async def calculate_affordability(session: AsyncSession, user_id: UUID) -> dict:
    """
    Calculates affordability metrics deterministically (no LLM math).
    
    Heuristics (Indian context):
    1. Maximum Total EMI should not exceed 50% of monthly average income.
    2. Safe new EMI = (50% of Income) - Existing EMIs.
    3. If monthly spend + new EMI > Income, it's high risk.
    """
    
    # Calculate average income (past 3 months of positive transactions)
    three_months_ago = date.today() - timedelta(days=90)
    
    income_q = select(func.sum(Transaction.amount)).where(
        Transaction.user_id == user_id,
        Transaction.amount > 0,
        Transaction.transaction_date >= three_months_ago
    )
    income_res = await session.execute(income_q)
    total_income_3m = income_res.scalar_one_or_none() or Decimal(0)
    avg_monthly_income = float(total_income_3m / 3)
    
    # Calculate average spend (past 3 months of negative transactions)
    spend_q = select(func.sum(Transaction.amount)).where(
        Transaction.user_id == user_id,
        Transaction.amount < 0,
        Transaction.transaction_date >= three_months_ago
    )
    spend_res = await session.execute(spend_q)
    total_spend_3m = abs(spend_res.scalar_one_or_none() or Decimal(0))
    avg_monthly_spend = float(total_spend_3m / 3)
    
    # Calculate existing EMIs
    emi_q = select(func.sum(Liability.emi)).where(
        Liability.user_id == user_id
    )
    emi_res = await session.execute(emi_q)
    total_existing_emi = float(emi_res.scalar_one_or_none() or Decimal(0))
    
    # Affordability Formulas
    max_allowable_emi = avg_monthly_income * 0.50
    safe_new_emi = max(0.0, max_allowable_emi - total_existing_emi)
    
    surplus = avg_monthly_income - avg_monthly_spend - total_existing_emi
    
    # Risk Bucketing
    if avg_monthly_income == 0:
        risk_level = "unknown"
        message = "Could not find any income transactions in the last 3 months. Upload a salary account statement for accurate affordability."
    elif surplus < safe_new_emi:
        # Cap the safe EMI to the actual cash surplus if they spend too much
        safe_new_emi = max(0.0, surplus)
        risk_level = "high"
        message = f"Your expenses are high. You can safely afford an EMI of ₹{safe_new_emi:,.2f} based on current surplus."
    elif total_existing_emi > (avg_monthly_income * 0.40):
        risk_level = "medium"
        message = f"You already have high debt. You can safely add an EMI of up to ₹{safe_new_emi:,.2f}."
    else:
        risk_level = "low"
        message = f"Your finances look healthy. You can comfortably afford an EMI of up to ₹{safe_new_emi:,.2f}."
        
    return {
        "monthly_income": avg_monthly_income,
        "monthly_spend": avg_monthly_spend,
        "existing_emi": total_existing_emi,
        "surplus": surplus,
        "safe_emi_estimate": safe_new_emi,
        "risk_level": risk_level,
        "message": message
    }
