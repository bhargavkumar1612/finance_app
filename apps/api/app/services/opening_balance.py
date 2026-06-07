"""Opening balance transactions for primary accounts."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Transaction
from app.services.account_types import OPENING_BALANCE_TYPES
from app.services.transaction_semantics import NwImpact

OPENING_BALANCE_SOURCE = "opening_balance"
OPENING_BALANCE_MERCHANT = "Opening balance"
OPENING_BALANCE_CATEGORY = "Transfer"


async def get_opening_balance_txn(
    session: AsyncSession, account_id: UUID, user_id: UUID
) -> Transaction | None:
    result = await session.execute(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.source == OPENING_BALANCE_SOURCE,
        )
    )
    return result.scalar_one_or_none()


async def read_opening_balance(
    session: AsyncSession, account_id: UUID, user_id: UUID
) -> float | None:
    txn = await get_opening_balance_txn(session, account_id, user_id)
    if txn is None:
        return None
    amt = float(txn.amount)
    return amt if amt > 0 else None


async def upsert_opening_balance(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
    amount: float | None,
) -> None:
    if account.account_type not in OPENING_BALANCE_TYPES:
        raise ValueError("opening_balance applies only to bank, cash, investment, and EPF accounts")

    existing = await get_opening_balance_txn(session, account.id, user_id)

    if amount is None or amount <= 0:
        if existing:
            await session.delete(existing)
        return

    dec_amount = Decimal(str(amount))
    if existing:
        existing.amount = dec_amount
        existing.transaction_date = date.today()
        existing.merchant = OPENING_BALANCE_MERCHANT
        existing.category = OPENING_BALANCE_CATEGORY
        existing.nw_impact = NwImpact.transfer.value
        existing.source = OPENING_BALANCE_SOURCE
    else:
        session.add(
            Transaction(
                user_id=user_id,
                account_id=account.id,
                amount=dec_amount,
                currency=account.currency or "INR",
                transaction_date=date.today(),
                merchant=OPENING_BALANCE_MERCHANT,
                category=OPENING_BALANCE_CATEGORY,
                source=OPENING_BALANCE_SOURCE,
                nw_impact=NwImpact.transfer.value,
            )
        )
