"""Mutual fund SIP installment schedule from transfer transactions."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Transaction
from app.services.mf_investment_mode import is_sip_account
from app.services.opening_balance import OPENING_BALANCE_SOURCE
from app.services.transaction_semantics import NwImpact


async def _sip_installment_transactions(
    session: AsyncSession, account_id: UUID, user_id: UUID
) -> list[Transaction]:
    result = await session.execute(
        select(Transaction)
        .where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.nw_impact == NwImpact.transfer.value,
            Transaction.amount > 0,
            Transaction.source != OPENING_BALANCE_SOURCE,
        )
        .order_by(Transaction.transaction_date.asc(), Transaction.created_at.asc())
    )
    return list(result.scalars().all())


async def compute_sip_schedule(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
) -> dict:
    if not is_sip_account(account):
        return {
            "amount_invested": 0.0,
            "sip_paid_count": None,
            "sip_pending_count": None,
            "payment_history": [],
        }

    installments = await _sip_installment_transactions(session, account.id, user_id)
    amount_invested = sum((p.amount for p in installments), Decimal(0))

    sip_paid_count = len(installments)
    if account.emi_amount and account.emi_amount > 0:
        sip_paid_count = int(amount_invested // account.emi_amount)

    sip_pending_count: int | None = None
    if account.tenure_months is not None:
        sip_pending_count = max(account.tenure_months - sip_paid_count, 0)

    payment_history = [
        {"date": p.transaction_date.isoformat(), "amount": float(p.amount)}
        for p in installments
    ]

    return {
        "amount_invested": float(amount_invested),
        "sip_paid_count": sip_paid_count,
        "sip_pending_count": sip_pending_count,
        "payment_history": payment_history,
    }
