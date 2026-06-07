"""Optional investment reference metadata — folio (MF/RD) and demat (stock)."""
from __future__ import annotations

from app.db.models import Account
from app.services.bank_account_details import normalize_optional_text
from app.services.account_types import DEMAT_TYPES, FOLIO_TYPES


def validate_investment_details(
    account_type: str,
    *,
    folio_number: str | None,
    demat_id: str | None,
) -> None:
    if folio_number is not None and account_type not in FOLIO_TYPES:
        raise ValueError("folio_number applies only to mutual_fund, recurring_deposit, and epf accounts")
    if demat_id is not None and account_type not in DEMAT_TYPES:
        raise ValueError("demat_id applies only to stock accounts")


def apply_investment_fields(
    account: Account,
    *,
    folio_number: str | None,
    demat_id: str | None,
    fields_set: set[str],
) -> None:
    if folio_number is not None or "folio_number" in fields_set:
        account.folio_number = normalize_optional_text(folio_number)
    if demat_id is not None or "demat_id" in fields_set:
        account.demat_id = normalize_optional_text(demat_id)


def clear_investment_fields(account: Account) -> None:
    account.folio_number = None
    account.demat_id = None
