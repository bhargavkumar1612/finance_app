"""Classify transactions by net-worth impact — single source of truth."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional


class NwImpact(str, Enum):
    spending = "spending"
    income = "income"
    transfer = "transfer"
    liability_payment = "liability_payment"
    refund = "refund"
    unknown = "unknown"


PRIMARY_ACCOUNT_TYPES = frozenset({"bank", "cash"})
DERIVED_ACCOUNT_TYPES = frozenset({"credit_card", "wallet"})

# Category label (lower) -> nw_impact when amount sign alone is ambiguous
_CATEGORY_NW: dict[str, NwImpact] = {
    "income": NwImpact.income,
    "housing": NwImpact.spending,
    "food": NwImpact.spending,
    "transport": NwImpact.spending,
    "shopping": NwImpact.spending,
    "groceries": NwImpact.spending,
    "utilities": NwImpact.spending,
    "entertainment": NwImpact.spending,
    "health": NwImpact.spending,
    "emi": NwImpact.liability_payment,
    "investments": NwImpact.transfer,
    "bills": NwImpact.liability_payment,
    "insurance": NwImpact.spending,
    "tax": NwImpact.spending,
}

_REFUND_KEYWORDS = ("refund", "reversal", "rev-", "cancelled", "chargeback", "cr-refund")
_INCOME_KEYWORDS = ("salary", "neft cr-salary", "freelance", "imps cr", "neft cr-")
_EMI_KEYWORDS = ("home loan emi", "ach dr-hdfc home", "loan emi", "emi", "bajaj finance", "muthoot")
_SIP_KEYWORDS = ("mf sip", "sbi mf", "mutual fund", "ach dr-sbi mf")
_BILLPAY_KEYWORDS = ("billpay", "credit card hdfc", "credit card payment", "cc payment")
_TRANSFER_KEYWORDS = (
    "neft dr-self", "imps-self", "transfer to", "trf to", "self transfer",
    "own account", "sweep",
)


def _text_blob(merchant: str | None, raw_description: str | None, category: str | None) -> str:
    parts = [str(merchant or ""), str(raw_description or ""), str(category or "")]
    return " ".join(parts).lower()


def classify_transaction(
    amount: Decimal | float,
    *,
    category: str | None = None,
    merchant: str | None = None,
    raw_description: str | None = None,
    account_type: str | None = None,
) -> NwImpact:
    """
    Determine nw_impact from narration, category, amount sign, and account type.
    Rule order: refund → income → liability/transfer keywords → category map → account type → sign fallback.
    """
    amt = Decimal(str(amount))
    text = _text_blob(merchant, raw_description, category)
    acct = (account_type or "").lower()

    if any(kw in text for kw in _REFUND_KEYWORDS):
        return NwImpact.refund

    if any(kw in text for kw in _INCOME_KEYWORDS) and amt > 0:
        return NwImpact.income

    if any(kw in text for kw in _BILLPAY_KEYWORDS):
        return NwImpact.liability_payment

    if any(kw in text for kw in _EMI_KEYWORDS):
        return NwImpact.liability_payment

    if any(kw in text for kw in _SIP_KEYWORDS):
        return NwImpact.transfer

    if any(kw in text for kw in _TRANSFER_KEYWORDS):
        return NwImpact.transfer

    if category:
        cat_key = category.strip().lower()
        if cat_key in _CATEGORY_NW:
            return _CATEGORY_NW[cat_key]

    if acct == "credit_card":
        if amt < 0:
            return NwImpact.spending
        if amt > 0:
            return NwImpact.liability_payment

    if amt > 0:
        if category and category.lower() == "income":
            return NwImpact.income
        return NwImpact.refund if any(kw in text for kw in _REFUND_KEYWORDS) else NwImpact.income

    if amt < 0:
        return NwImpact.spending

    return NwImpact.unknown


def nw_impact_for_expense(amount: Decimal, **kwargs) -> NwImpact:
    """Chat/manual expense — always spending unless overridden."""
    negative = -abs(amount)
    impact = classify_transaction(negative, **kwargs)
    if impact in (NwImpact.income, NwImpact.refund):
        return NwImpact.spending
    return impact


def nw_impact_for_income(amount: Decimal, **kwargs) -> NwImpact:
    """Chat/manual income — always income."""
    positive = abs(amount)
    return classify_transaction(positive, category=kwargs.get("category") or "Income", **kwargs)
