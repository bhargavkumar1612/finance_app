"""Seed pre-tracked SIP installments when onboarding mid-plan."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Transaction
from app.services.mf_investment_mode import is_sip_account
from app.services.transaction_semantics import NwImpact

INITIAL_SIP_PAID_SOURCE = "initial_sip_paid"
PAID_MERCHANT = "Initial SIP installments"


async def _get_seed_txn(
    session: AsyncSession, account_id: UUID, user_id: UUID
) -> Transaction | None:
    result = await session.execute(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.source == INITIAL_SIP_PAID_SOURCE,
        )
    )
    return result.scalar_one_or_none()


async def read_initial_sip_paid_count(
    session: AsyncSession, account_id: UUID, user_id: UUID, emi_amount: Decimal | None
) -> int | None:
    paid = await _get_seed_txn(session, account_id, user_id)
    if paid is None:
        return None
    if emi_amount and emi_amount > 0:
        return int(paid.amount // emi_amount)
    return None


async def upsert_initial_sip_state(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
    initial_sip_paid_count: int | None,
) -> None:
    existing = await _get_seed_txn(session, account.id, user_id)
    if not is_sip_account(account):
        if existing:
            await session.delete(existing)
        return

    if initial_sip_paid_count is None:
        if existing:
            await session.delete(existing)
        return

    if initial_sip_paid_count < 0:
        raise ValueError("initial_sip_paid_count cannot be negative")

    if initial_sip_paid_count > 0:
        if account.emi_amount is None or account.emi_amount <= 0:
            raise ValueError("emi_amount is required when initial_sip_paid_count is greater than zero")

    if account.tenure_months is not None and initial_sip_paid_count > account.tenure_months:
        raise ValueError("initial_sip_paid_count cannot exceed tenure_months")

    as_of = account.start_date or date.today()
    emi = account.emi_amount or Decimal(0)

    if initial_sip_paid_count == 0:
        if existing:
            await session.delete(existing)
        return

    amount = emi * Decimal(initial_sip_paid_count)
    if existing:
        existing.amount = amount
        existing.transaction_date = as_of
        existing.merchant = PAID_MERCHANT
        existing.category = "Investments"
        existing.nw_impact = NwImpact.transfer.value
        existing.source = INITIAL_SIP_PAID_SOURCE
    else:
        session.add(
            Transaction(
                user_id=user_id,
                account_id=account.id,
                amount=amount,
                currency=account.currency or "INR",
                transaction_date=as_of,
                merchant=PAID_MERCHANT,
                category="Investments",
                source=INITIAL_SIP_PAID_SOURCE,
                nw_impact=NwImpact.transfer.value,
            )
        )
