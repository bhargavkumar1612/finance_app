"""Hybrid net worth: primary balances + manual assets − CC outstanding − manual liabilities."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Asset, Liability, Transaction
from app.services.transaction_semantics import NwImpact

PRIMARY_TYPES = ("bank", "cash")


async def _account_balance(session: AsyncSession, account_id: UUID, user_id: UUID) -> Decimal:
    result = await session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
        )
    )
    return result.scalar_one() or Decimal(0)


async def _cc_outstanding(session: AsyncSession, account_id: UUID, user_id: UUID) -> Decimal:
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


async def compute_net_worth(session: AsyncSession, user_id: UUID) -> dict:
    accounts_result = await session.execute(
        select(Account).where(Account.user_id == user_id)
    )
    accounts = list(accounts_result.scalars().all())

    cash_assets = Decimal(0)
    cc_liabilities = Decimal(0)
    breakdown_accounts: list[dict] = []

    for acc in accounts:
        balance = await _account_balance(session, acc.id, user_id)
        if acc.account_type in PRIMARY_TYPES:
            cash_assets += balance
            breakdown_accounts.append({
                "name": acc.name,
                "type": acc.account_type,
                "role": "primary",
                "balance": float(balance),
            })
        elif acc.account_type == "credit_card":
            outstanding = await _cc_outstanding(session, acc.id, user_id)
            cc_liabilities += outstanding
            breakdown_accounts.append({
                "name": acc.name,
                "type": acc.account_type,
                "role": "derived",
                "outstanding": float(outstanding),
            })
        elif acc.account_type == "wallet":
            cash_assets += balance
            breakdown_accounts.append({
                "name": acc.name,
                "type": acc.account_type,
                "role": "derived",
                "balance": float(balance),
            })

    ar = await session.execute(
        select(func.coalesce(func.sum(Asset.current_value), 0)).where(Asset.user_id == user_id)
    )
    manual_assets = ar.scalar_one() or Decimal(0)

    lr = await session.execute(
        select(func.coalesce(func.sum(Liability.outstanding_amount), 0)).where(Liability.user_id == user_id)
    )
    loan_liabilities = lr.scalar_one() or Decimal(0)

    assets_total = cash_assets + manual_assets
    liabilities_total = cc_liabilities + loan_liabilities
    net_worth = assets_total - liabilities_total

    return {
        "net_worth": float(net_worth),
        "assets_total": float(assets_total),
        "liabilities_total": float(liabilities_total),
        "cash_and_primary": float(cash_assets),
        "manual_assets": float(manual_assets),
        "credit_card_outstanding": float(cc_liabilities),
        "loan_liabilities": float(loan_liabilities),
        "accounts": breakdown_accounts,
        "currency": "INR",
    }
