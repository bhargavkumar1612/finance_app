"""Hybrid net worth: primary balances + manual assets − CC/loan outstanding."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Asset, Transaction
from app.services.account_balances import account_balance, liability_outstanding
from app.services.investment_valuation import effective_holdings_value, resolve_current_value
from app.services.account_types import HOLDINGS_TYPES, LOAN_TYPES, PRIMARY_TYPES

async def compute_net_worth(session: AsyncSession, user_id: UUID) -> dict:
    accounts_result = await session.execute(
        select(Account).where(Account.user_id == user_id)
    )
    accounts = list(accounts_result.scalars().all())

    cash_assets = Decimal(0)
    investment_assets = Decimal(0)
    cc_liabilities = Decimal(0)
    loan_liabilities = Decimal(0)
    breakdown_accounts: list[dict] = []

    for acc in accounts:
        balance = await account_balance(session, acc.id, user_id)
        if acc.account_type in PRIMARY_TYPES:
            cash_assets += balance
            breakdown_accounts.append({
                "name": acc.name,
                "type": acc.account_type,
                "role": "primary",
                "balance": float(balance),
            })
        elif acc.account_type == "credit_card":
            outstanding = await liability_outstanding(session, acc.id, user_id)
            cc_liabilities += outstanding
            entry: dict = {
                "name": acc.name,
                "type": acc.account_type,
                "role": "derived",
                "outstanding": float(outstanding),
            }
            if acc.credit_limit is not None:
                entry["credit_limit"] = float(acc.credit_limit)
                entry["credit_remaining"] = float(max(acc.credit_limit - outstanding, Decimal(0)))
            breakdown_accounts.append(entry)
        elif acc.account_type == "wallet":
            cash_assets += balance
            breakdown_accounts.append({
                "name": acc.name,
                "type": acc.account_type,
                "role": "derived",
                "balance": float(balance),
            })
        elif acc.account_type in HOLDINGS_TYPES:
            balance = float(await account_balance(session, acc.id, user_id))
            current = await resolve_current_value(session, acc, user_id, balance)
            holdings_value = effective_holdings_value(current, balance)
            investment_assets += Decimal(str(holdings_value))
            inv_entry: dict = {
                "name": acc.name,
                "type": acc.account_type,
                "role": "investment",
                "balance": balance,
                "current_value": current,
            }
            if acc.institution:
                inv_entry["institution"] = acc.institution
            breakdown_accounts.append(inv_entry)
        elif acc.account_type in LOAN_TYPES:
            outstanding = await liability_outstanding(session, acc.id, user_id)
            loan_liabilities += outstanding
            loan_entry: dict = {
                "name": acc.name,
                "type": acc.account_type,
                "role": "loan",
                "outstanding": float(outstanding),
            }
            if acc.loan_type:
                loan_entry["loan_type"] = acc.loan_type
            if acc.sanctioned_amount is not None:
                loan_entry["sanctioned_amount"] = float(acc.sanctioned_amount)
            breakdown_accounts.append(loan_entry)

    ar = await session.execute(
        select(func.coalesce(func.sum(Asset.current_value), 0)).where(Asset.user_id == user_id)
    )
    manual_assets = ar.scalar_one() or Decimal(0)

    assets_total = cash_assets + investment_assets + manual_assets
    liabilities_total = cc_liabilities + loan_liabilities
    net_worth = assets_total - liabilities_total

    return {
        "net_worth": float(net_worth),
        "assets_total": float(assets_total),
        "liabilities_total": float(liabilities_total),
        "cash_and_primary": float(cash_assets),
        "investment_holdings": float(investment_assets),
        "manual_assets": float(manual_assets),
        "credit_card_outstanding": float(cc_liabilities),
        "loan_liabilities": float(loan_liabilities),
        "accounts": breakdown_accounts,
        "currency": "INR",
    }
