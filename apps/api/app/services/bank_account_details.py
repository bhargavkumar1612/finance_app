"""Optional bank account metadata — account number, IFSC, branch, notes."""
from __future__ import annotations

import re

from app.db.models import Account
from app.services.account_types import BANK_DETAIL_TYPES

_IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def normalize_ifsc(ifsc_code: str | None) -> str | None:
    if ifsc_code is None:
        return None
    normalized = ifsc_code.strip().upper()
    if not normalized:
        return None
    if not _IFSC_PATTERN.match(normalized):
        raise ValueError("ifsc_code must be a valid 11-character IFSC")
    return normalized


def validate_bank_details(
    account_type: str,
    *,
    account_number: str | None,
    ifsc_code: str | None,
    branch: str | None,
    account_notes: str | None,
) -> None:
    for field_name, value in (
        ("account_number", account_number),
        ("ifsc_code", ifsc_code),
        ("branch", branch),
        ("account_notes", account_notes),
    ):
        if value is not None and account_type not in BANK_DETAIL_TYPES:
            raise ValueError(f"{field_name} applies only to bank accounts")
    if ifsc_code is not None:
        normalize_ifsc(ifsc_code)


def apply_bank_fields(
    account: Account,
    *,
    account_number: str | None,
    ifsc_code: str | None,
    branch: str | None,
    account_notes: str | None,
    fields_set: set[str],
) -> None:
    if account_number is not None or "account_number" in fields_set:
        account.account_number = normalize_optional_text(account_number)
    if ifsc_code is not None or "ifsc_code" in fields_set:
        account.ifsc_code = normalize_ifsc(ifsc_code) if ifsc_code else None
    if branch is not None or "branch" in fields_set:
        account.branch = normalize_optional_text(branch)
    if account_notes is not None or "account_notes" in fields_set:
        account.account_notes = normalize_optional_text(account_notes)


def clear_bank_fields(account: Account) -> None:
    account.account_number = None
    account.ifsc_code = None
    account.branch = None
    account.account_notes = None
