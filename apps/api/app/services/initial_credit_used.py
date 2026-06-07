"""Initial credit used seed transaction for credit card accounts."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Transaction
from app.services.account_types import INITIAL_CREDIT_USED_TYPES
from app.services.transaction_semantics import NwImpact

INITIAL_CREDIT_USED_SOURCE = "initial_credit_used"
INITIAL_CREDIT_USED_MERCHANT = "Initial credit used"
INITIAL_CREDIT_USED_CATEGORY = "Credit card"


async def get_initial_credit_used_txn(
    session: AsyncSession, account_id: UUID, user_id: UUID
) -> Transaction | None:
    result = await session.execute(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.source == INITIAL_CREDIT_USED_SOURCE,
        )
    )
    return result.scalar_one_or_none()


async def read_initial_credit_used(
    session: AsyncSession, account_id: UUID, user_id: UUID
) -> tuple[float | None, date | None]:
    txn = await get_initial_credit_used_txn(session, account_id, user_id)
    if txn is None:
        return None, None
    return abs(float(txn.amount)), txn.transaction_date


async def upsert_initial_credit_used(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
    amount: float | None,
    as_of_date: date | None,
) -> None:
    if account.account_type not in INITIAL_CREDIT_USED_TYPES:
        existing = await get_initial_credit_used_txn(session, account.id, user_id)
        if existing:
            await session.delete(existing)
        return

    existing = await get_initial_credit_used_txn(session, account.id, user_id)

    if amount is None or amount <= 0:
        if existing:
            await session.delete(existing)
        return

    if as_of_date is None:
        raise ValueError("initial_credit_used_date is required when initial_credit_used is set")

    dec_amount = -Decimal(str(amount))
    if existing:
        existing.amount = dec_amount
        existing.transaction_date = as_of_date
        existing.merchant = INITIAL_CREDIT_USED_MERCHANT
        existing.category = INITIAL_CREDIT_USED_CATEGORY
        existing.nw_impact = NwImpact.spending.value
        existing.source = INITIAL_CREDIT_USED_SOURCE
    else:
        session.add(
            Transaction(
                user_id=user_id,
                account_id=account.id,
                amount=dec_amount,
                currency=account.currency or "INR",
                transaction_date=as_of_date,
                merchant=INITIAL_CREDIT_USED_MERCHANT,
                category=INITIAL_CREDIT_USED_CATEGORY,
                source=INITIAL_CREDIT_USED_SOURCE,
                nw_impact=NwImpact.spending.value,
            )
        )
