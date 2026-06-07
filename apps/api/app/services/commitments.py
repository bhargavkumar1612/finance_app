"""Monthly committed outflows — shared by obligations hub and affordability."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, RecurringBill
from app.services.account_balances import liability_outstanding
from app.services.account_types import LOAN_TYPES
from app.services.mf_investment_mode import is_sip_account


async def monthly_loan_emis(session: AsyncSession, user_id: UUID) -> float:
    result = await session.execute(
        select(func.coalesce(func.sum(Account.emi_amount), 0)).where(
            Account.user_id == user_id,
            Account.account_type.in_(tuple(LOAN_TYPES)),
            Account.emi_amount.isnot(None),
            Account.emi_amount > 0,
        )
    )
    return float(result.scalar_one() or 0)


async def monthly_sip_emis(session: AsyncSession, user_id: UUID) -> float:
    result = await session.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == "mutual_fund",
        )
    )
    total = 0.0
    for acc in result.scalars().all():
        if is_sip_account(acc) and acc.emi_amount:
            total += float(acc.emi_amount)
    return total


async def monthly_recurring_bills(session: AsyncSession, user_id: UUID) -> float:
    result = await session.execute(
        select(RecurringBill).where(
            RecurringBill.user_id == user_id,
            RecurringBill.is_active.is_(True),
        )
    )
    total = 0.0
    for bill in result.scalars().all():
        amt = abs(float(bill.amount))
        if bill.frequency == "weekly":
            total += amt * 4.33
        else:
            total += amt
    return round(total, 2)


async def monthly_cc_commitments(session: AsyncSession, user_id: UUID) -> float:
    """CC commitment heuristic: outstanding balance (glossary fallback)."""
    result = await session.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == "credit_card",
        )
    )
    total = 0.0
    for acc in result.scalars().all():
        outstanding = await liability_outstanding(session, acc.id, user_id)
        total += float(outstanding)
    return round(total, 2)


async def monthly_commitments_breakdown(session: AsyncSession, user_id: UUID) -> dict:
    loan_emis = await monthly_loan_emis(session, user_id)
    sip_emis = await monthly_sip_emis(session, user_id)
    recurring_bills = await monthly_recurring_bills(session, user_id)
    cc_commitments = await monthly_cc_commitments(session, user_id)
    total = loan_emis + sip_emis + recurring_bills + cc_commitments
    return {
        "loan_emis": loan_emis,
        "sip_emis": sip_emis,
        "recurring_bills": recurring_bills,
        "cc_commitments": cc_commitments,
        "total_commitments": round(total, 2),
    }
