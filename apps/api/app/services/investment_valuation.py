"""Invested vs current value and P&L for holdings accounts."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Transaction
from app.services.account_types import HOLDINGS_TYPES


async def sum_inflow_transactions(
    session: AsyncSession,
    account_id: UUID,
    user_id: UUID,
) -> Decimal:
    """Sum of positive amounts on the account (contributions / purchases)."""
    result = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
            Transaction.amount > 0,
        )
    )
    return result.scalar_one() or Decimal(0)


async def resolve_invested_amount(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
) -> float | None:
    if account.account_type not in HOLDINGS_TYPES:
        return None
    if account.invested_amount is not None:
        return float(account.invested_amount)
    inflows = await sum_inflow_transactions(session, account.id, user_id)
    if inflows > 0:
        return float(inflows)
    return None


async def resolve_current_value(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
    balance: float | None,
) -> float | None:
    if account.account_type not in HOLDINGS_TYPES:
        return None
    if account.current_value is not None:
        return float(account.current_value)
    return balance


def compute_pnl(
    invested: float | None,
    current: float | None,
) -> tuple[float | None, float | None]:
    if invested is None or current is None or invested <= 0:
        return None, None
    pnl_amount = current - invested
    pnl_percent = (pnl_amount / invested) * 100
    return pnl_amount, pnl_percent


def effective_holdings_value(current: float | None, balance: float | None) -> float:
    if current is not None:
        return current
    return balance or 0.0
