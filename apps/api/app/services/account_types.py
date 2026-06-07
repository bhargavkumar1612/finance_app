"""Shared account type constants — single source of truth."""
from __future__ import annotations

ACCOUNT_TYPES = (
    "bank",
    "credit_card",
    "wallet",
    "cash",
    "loan",
    "mutual_fund",
    "fixed_deposit",
    "recurring_deposit",
    "stock",
    "epf",
)

PRIMARY_TYPES = frozenset({"bank", "cash"})
BANK_DETAIL_TYPES = frozenset({"bank"})
INVESTMENT_TYPES = frozenset({"mutual_fund", "fixed_deposit", "recurring_deposit", "stock"})
RETIREMENT_TYPES = frozenset({"epf"})
HOLDINGS_TYPES = INVESTMENT_TYPES | RETIREMENT_TYPES
INVESTMENT_FD_TYPES = frozenset({"fixed_deposit", "recurring_deposit"})
FOLIO_TYPES = frozenset({"mutual_fund", "recurring_deposit", "epf"})
DEMAT_TYPES = frozenset({"stock"})
DERIVED_LIABILITY_TYPES = frozenset({"credit_card", "wallet", "loan"})
DERIVED_TYPES = DERIVED_LIABILITY_TYPES | INVESTMENT_TYPES
PARENT_REQUIRED_TYPES = frozenset({"credit_card", "loan"}) | INVESTMENT_TYPES
PARENT_LINKABLE_TYPES = DERIVED_TYPES
OPENING_BALANCE_TYPES = PRIMARY_TYPES | HOLDINGS_TYPES
INITIAL_CREDIT_USED_TYPES = frozenset({"credit_card"})
LOAN_TYPES = frozenset({"loan"})
LOAN_DETAIL_TYPES = ("home", "personal", "vehicle", "education", "other")
LIMIT_ACCOUNT_TYPES = frozenset({"credit_card"})
SANCTIONED_ACCOUNT_TYPES = frozenset({"loan"})
DUE_DAY_TYPES = frozenset({"credit_card", "loan"})
SIP_SCHEDULE_TYPES = frozenset({"mutual_fund"})
INVESTMENT_MODES = frozenset({"one_time", "sip"})

LEGACY_LOAN_ACCOUNT_TYPES = frozenset({"home_loan", "personal_loan", "other_loan"})
LEGACY_LOAN_TYPE_MAP = {
    "home_loan": "home",
    "personal_loan": "personal",
    "other_loan": "other",
}

# UI grouping — mirrors apps/web/lib/accountDisplay.ts and net_worth.py
CASH_WALLET_TYPES = frozenset({"bank", "cash", "wallet"})
CREDIT_CARD_TYPES = frozenset({"credit_card"})
ASSET_UI_GROUPS = {
    "cash_wallets": CASH_WALLET_TYPES,
    "investments": HOLDINGS_TYPES,
}
LIABILITY_UI_GROUPS = {
    "credit_cards": CREDIT_CARD_TYPES,
    "loans": LOAN_TYPES,
}
LIABILITY_BALANCE_TYPES = CREDIT_CARD_TYPES | LOAN_TYPES
