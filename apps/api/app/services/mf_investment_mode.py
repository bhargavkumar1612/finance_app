"""Mutual fund investment mode — one-time lump sum vs monthly SIP."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.db.models import Account
from app.services.account_types import INVESTMENT_MODES, SIP_SCHEDULE_TYPES


def normalize_investment_mode(mode: str | None) -> str | None:
    if mode is None:
        return None
    normalized = mode.strip().lower()
    if normalized not in INVESTMENT_MODES:
        raise ValueError(f"investment_mode must be one of: {', '.join(sorted(INVESTMENT_MODES))}")
    return normalized


def is_sip_account(account: Account) -> bool:
    return account.account_type in SIP_SCHEDULE_TYPES and account.investment_mode == "sip"


def validate_investment_mode(
    account_type: str,
    investment_mode: str | None,
    *,
    emi_amount: float | Decimal | None = None,
    due_day: int | None = None,
    start_date: date | None = None,
    tenure_months: int | None = None,
) -> None:
    if investment_mode is not None and account_type not in SIP_SCHEDULE_TYPES:
        raise ValueError("investment_mode applies only to mutual_fund accounts")
    if account_type not in SIP_SCHEDULE_TYPES:
        return
    if investment_mode is None:
        return
    mode = normalize_investment_mode(investment_mode)
    if mode == "one_time":
        if emi_amount is not None and float(emi_amount) > 0:
            raise ValueError("emi_amount applies only to SIP mutual fund accounts")
        if due_day is not None:
            raise ValueError("due_day applies only to SIP mutual fund accounts when mode is sip")
        return
    if mode == "sip":
        if emi_amount is None or float(emi_amount) <= 0:
            raise ValueError("emi_amount is required for SIP mutual fund accounts")
        if due_day is None:
            raise ValueError("due_day is required for SIP mutual fund accounts")
        if start_date is None:
            raise ValueError("start_date is required for SIP mutual fund accounts")
        if tenure_months is not None and tenure_months <= 0:
            raise ValueError("tenure_months must be positive when set")


def apply_investment_mode(
    account: Account,
    investment_mode: str | None,
    fields_set: set[str],
) -> None:
    if investment_mode is not None or "investment_mode" in fields_set:
        account.investment_mode = normalize_investment_mode(investment_mode) if investment_mode else None


def clear_sip_schedule_fields(account: Account) -> None:
    account.emi_amount = None
    account.due_day = None
    account.start_date = None
    account.tenure_months = None
