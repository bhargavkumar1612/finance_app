"""Loan EMI schedule metrics from transactions."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Transaction
from app.services.account_balances import liability_outstanding
from app.services.transaction_semantics import NwImpact


async def _payment_transactions(
    session: AsyncSession, account_id: UUID, user_id: UUID
) -> list[Transaction]:
    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.nw_impact == NwImpact.liability_payment.value,
        )
        .order_by(Transaction.transaction_date.asc(), Transaction.created_at.asc())
    )
    return list(result.scalars().all())


async def compute_loan_schedule(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
) -> dict:
    outstanding = await liability_outstanding(session, account.id, user_id)
    payments = await _payment_transactions(session, account.id, user_id)
    amount_paid = sum((p.amount for p in payments), Decimal(0))

    emi_paid_count = len(payments)
    if account.emi_amount and account.emi_amount > 0:
        emi_paid_count = int(amount_paid // account.emi_amount)

    emi_pending_count: int | None = None
    if account.tenure_months is not None:
        emi_pending_count = max(account.tenure_months - emi_paid_count, 0)

    payment_history = [
        {"date": p.transaction_date.isoformat(), "amount": float(p.amount)}
        for p in payments
    ]

    return {
        "outstanding": float(outstanding),
        "amount_paid": float(amount_paid),
        "emi_paid_count": emi_paid_count,
        "emi_pending_count": emi_pending_count,
        "payment_history": payment_history,
    }
