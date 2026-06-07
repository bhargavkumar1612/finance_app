"""Seed loan disbursement + pre-paid EMIs when onboarding mid-tenure."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Transaction
from app.services.account_types import LOAN_TYPES
from app.services.transaction_semantics import NwImpact

INITIAL_LOAN_DISBURSEMENT_SOURCE = "initial_loan_disbursement"
INITIAL_LOAN_PAID_SOURCE = "initial_loan_paid"
DISBURSEMENT_MERCHANT = "Initial loan disbursement"
PAID_MERCHANT = "Initial EMIs paid"


async def _get_seed_txn(
    session: AsyncSession, account_id: UUID, user_id: UUID, source: str
) -> Transaction | None:
    result = await session.execute(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.source == source,
        )
    )
    return result.scalar_one_or_none()


async def _clear_loan_seeds(session: AsyncSession, account_id: UUID, user_id: UUID) -> None:
    for source in (INITIAL_LOAN_DISBURSEMENT_SOURCE, INITIAL_LOAN_PAID_SOURCE):
        txn = await _get_seed_txn(session, account_id, user_id, source)
        if txn:
            await session.delete(txn)


async def read_initial_emi_paid_count(
    session: AsyncSession, account_id: UUID, user_id: UUID, emi_amount: Decimal | None
) -> int | None:
    paid = await _get_seed_txn(session, account_id, user_id, INITIAL_LOAN_PAID_SOURCE)
    if paid is None:
        disbursement = await _get_seed_txn(session, account_id, user_id, INITIAL_LOAN_DISBURSEMENT_SOURCE)
        return 0 if disbursement is not None else None
    if emi_amount and emi_amount > 0:
        return int(paid.amount // emi_amount)
    return None


async def upsert_initial_loan_state(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
    initial_emi_paid_count: int | None,
) -> None:
    if account.account_type not in LOAN_TYPES:
        await _clear_loan_seeds(session, account.id, user_id)
        return

    if initial_emi_paid_count is None:
        await _clear_loan_seeds(session, account.id, user_id)
        return

    if initial_emi_paid_count < 0:
        raise ValueError("initial_emi_paid_count cannot be negative")

    if account.sanctioned_amount is None or account.sanctioned_amount <= 0:
        raise ValueError("sanctioned_amount is required when initial_emi_paid_count is set")

    if initial_emi_paid_count > 0:
        if account.emi_amount is None or account.emi_amount <= 0:
            raise ValueError("emi_amount is required when initial_emi_paid_count is greater than zero")

    if account.tenure_months is not None and initial_emi_paid_count > account.tenure_months:
        raise ValueError("initial_emi_paid_count cannot exceed tenure_months")

    as_of = account.start_date or date.today()
    sanctioned = account.sanctioned_amount
    emi = account.emi_amount or Decimal(0)

    disbursement = await _get_seed_txn(session, account.id, user_id, INITIAL_LOAN_DISBURSEMENT_SOURCE)
    dec_disbursement = -sanctioned
    if disbursement:
        disbursement.amount = dec_disbursement
        disbursement.transaction_date = as_of
        disbursement.merchant = DISBURSEMENT_MERCHANT
        disbursement.category = "Loan"
        disbursement.nw_impact = NwImpact.spending.value
        disbursement.source = INITIAL_LOAN_DISBURSEMENT_SOURCE
    else:
        session.add(
            Transaction(
                user_id=user_id,
                account_id=account.id,
                amount=dec_disbursement,
                currency=account.currency or "INR",
                transaction_date=as_of,
                merchant=DISBURSEMENT_MERCHANT,
                category="Loan",
                source=INITIAL_LOAN_DISBURSEMENT_SOURCE,
                nw_impact=NwImpact.spending.value,
            )
        )

    paid = await _get_seed_txn(session, account.id, user_id, INITIAL_LOAN_PAID_SOURCE)
    if initial_emi_paid_count == 0:
        if paid:
            await session.delete(paid)
        return

    dec_paid = emi * Decimal(initial_emi_paid_count)
    if paid:
        paid.amount = dec_paid
        paid.transaction_date = as_of
        paid.merchant = PAID_MERCHANT
        paid.category = "Loan"
        paid.nw_impact = NwImpact.liability_payment.value
        paid.source = INITIAL_LOAN_PAID_SOURCE
    else:
        session.add(
            Transaction(
                user_id=user_id,
                account_id=account.id,
                amount=dec_paid,
                currency=account.currency or "INR",
                transaction_date=as_of,
                merchant=PAID_MERCHANT,
                category="Loan",
                source=INITIAL_LOAN_PAID_SOURCE,
                nw_impact=NwImpact.liability_payment.value,
            )
        )
