"""Compute per-account balances and credit/loan metrics from transactions."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Transaction
from app.services.account_types import HOLDINGS_TYPES, LOAN_TYPES, PRIMARY_TYPES
from app.services.investment_valuation import (
    compute_pnl,
    resolve_current_value,
    resolve_invested_amount,
)
from app.services.transaction_semantics import NwImpact


async def account_balance(session: AsyncSession, account_id: UUID, user_id: UUID) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
        )
    )
    return result.scalar_one() or Decimal(0)


async def liability_outstanding(session: AsyncSession, account_id: UUID, user_id: UUID) -> Decimal:
    """Outstanding debt on credit cards and loan accounts (spending minus payments)."""
    spend = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.nw_impact == NwImpact.spending.value,
        )
    )
    payments = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.nw_impact == NwImpact.liability_payment.value,
        )
    )
    spending = abs(spend.scalar_one() or Decimal(0))
    paid = payments.scalar_one() or Decimal(0)
    return max(spending - paid, Decimal(0))


async def compute_account_metrics(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {
        "balance": None,
        "invested_amount": None,
        "current_value": None,
        "pnl_amount": None,
        "pnl_percent": None,
        "credit_used": None,
        "credit_remaining": None,
        "outstanding": None,
        "amount_paid": None,
        "emi_paid_count": None,
        "emi_pending_count": None,
    }
    acct_type = account.account_type

    if acct_type in PRIMARY_TYPES or acct_type == "wallet" or acct_type in HOLDINGS_TYPES:
        balance_dec = await account_balance(session, account.id, user_id)
        balance = float(balance_dec)
        metrics["balance"] = balance
        if acct_type in HOLDINGS_TYPES:
            invested = await resolve_invested_amount(session, account, user_id)
            current = await resolve_current_value(session, account, user_id, balance)
            pnl_amount, pnl_percent = compute_pnl(invested, current)
            metrics["invested_amount"] = invested
            metrics["current_value"] = current
            metrics["pnl_amount"] = pnl_amount
            metrics["pnl_percent"] = pnl_percent
    elif acct_type == "credit_card":
        used = await liability_outstanding(session, account.id, user_id)
        metrics["credit_used"] = float(used)
        if account.credit_limit is not None:
            metrics["credit_remaining"] = float(max(account.credit_limit - used, Decimal(0)))
    elif acct_type in LOAN_TYPES:
        from app.services.loan_schedule import compute_loan_schedule

        schedule = await compute_loan_schedule(session, account, user_id)
        metrics["outstanding"] = schedule["outstanding"]
        metrics["amount_paid"] = schedule["amount_paid"]
        metrics["emi_paid_count"] = schedule["emi_paid_count"]
        metrics["emi_pending_count"] = schedule["emi_pending_count"]

    return metrics
