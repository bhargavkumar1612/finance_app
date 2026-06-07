"""Account UI grouping and contribution amounts — mirrors frontend accountDisplay.ts."""
from __future__ import annotations

from app.services.account_types import (
    CREDIT_CARD_TYPES,
    HOLDINGS_TYPES,
    LIABILITY_BALANCE_TYPES,
    LOAN_TYPES,
)

UI_GROUP_CASH_WALLETS = "cash_wallets"
UI_GROUP_INVESTMENTS = "investments"
UI_GROUP_CREDIT_CARDS = "credit_cards"
UI_GROUP_LOANS = "loans"


def account_balance_side(account_type: str) -> str:
    if account_type in LIABILITY_BALANCE_TYPES:
        return "liability"
    return "asset"


def account_ui_group(account_type: str) -> str:
    if account_type in CREDIT_CARD_TYPES:
        return UI_GROUP_CREDIT_CARDS
    if account_type in LOAN_TYPES:
        return UI_GROUP_LOANS
    if account_type in HOLDINGS_TYPES:
        return UI_GROUP_INVESTMENTS
    return UI_GROUP_CASH_WALLETS


def account_contribution_amount(
    account_type: str,
    *,
    balance: float | None = None,
    current_value: float | None = None,
    credit_used: float | None = None,
    outstanding: float | None = None,
) -> float:
    if account_type in CREDIT_CARD_TYPES:
        return float(credit_used or 0)
    if account_type in LOAN_TYPES:
        return float(outstanding or 0)
    if account_type in HOLDINGS_TYPES:
        if current_value is not None:
            return float(current_value)
        return float(balance or 0)
    return float(balance or 0)
