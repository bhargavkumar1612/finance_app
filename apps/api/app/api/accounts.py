from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_async_session, Account, RecurringBill, Transaction, User
from app.services.account_balances import compute_account_metrics
from app.services.account_types import (
    ACCOUNT_TYPES,
    BANK_DETAIL_TYPES,
    DUE_DAY_TYPES,
    DEMAT_TYPES,
    FOLIO_TYPES,
    HOLDINGS_TYPES,
    INVESTMENT_FD_TYPES,
    LIMIT_ACCOUNT_TYPES,
    LOAN_DETAIL_TYPES,
    LOAN_TYPES,
    OPENING_BALANCE_TYPES,
    PARENT_REQUIRED_TYPES,
    PRIMARY_TYPES,
    SANCTIONED_ACCOUNT_TYPES,
)
from app.services.bank_account_details import (
    apply_bank_fields,
    clear_bank_fields,
    normalize_ifsc,
    normalize_optional_text,
    validate_bank_details,
)
from app.services.investment_account_details import (
    apply_investment_fields,
    clear_investment_fields,
    validate_investment_details,
)
from app.services.loan_schedule import compute_loan_schedule
from app.services.mf_sip_schedule import compute_sip_schedule
from app.services.mf_investment_mode import (
    apply_investment_mode,
    clear_sip_schedule_fields,
    validate_investment_mode,
)
from app.services.initial_credit_used import read_initial_credit_used, upsert_initial_credit_used
from app.services.initial_loan_state import read_initial_emi_paid_count, upsert_initial_loan_state
from app.services.initial_sip_state import read_initial_sip_paid_count, upsert_initial_sip_state
from app.services.opening_balance import read_opening_balance, upsert_opening_balance

router = APIRouter()


class PaymentHistoryItem(BaseModel):
    date: str
    amount: float


class CreateAccountRequest(BaseModel):
    account_type: str = Field(..., description="bank | credit_card | wallet | cash | loan | mutual_fund | fixed_deposit | recurring_deposit | stock | epf")
    name: str = Field(..., min_length=1)
    institution: str | None = None
    loan_type: str | None = Field(None, description="home | personal | vehicle | education | other")
    loan_type_description: str | None = None
    credit_limit: float | None = Field(None, description="Credit limit for credit_card only")
    sanctioned_amount: float | None = Field(None, description="Sanctioned amount for loan accounts")
    interest_rate: float | None = None
    emi_amount: float | None = None
    tenure_months: int | None = Field(None, ge=1)
    start_date: date | None = None
    due_day: int | None = Field(None, ge=1, le=31, description="Statement due day (credit_card) or EMI due day (loan)")
    currency: str = "INR"
    parent_account_id: UUID | None = Field(
        None,
        description="Required for credit_card, loan, and liquid investment accounts; optional for online wallet",
    )
    opening_balance: float | None = Field(None, description="Starting balance for bank/cash/holdings accounts (incl. EPF)")
    initial_credit_used: float | None = Field(
        None,
        description="Starting amount owed on credit_card (creates a seed spending transaction)",
    )
    initial_credit_used_date: date | None = Field(
        None,
        description="As-of date for initial_credit_used (required when amount is set)",
    )
    initial_emi_paid_count: int | None = Field(
        None,
        ge=0,
        description="EMIs already paid before tracking (loan only; uses sanctioned as disbursed)",
    )
    account_number: str | None = Field(None, description="Bank account number (bank only)")
    ifsc_code: str | None = Field(None, description="IFSC code (bank only)")
    branch: str | None = Field(None, description="Branch name (bank only)")
    account_notes: str | None = Field(None, description="Other bank account notes (bank only)")
    folio_number: str | None = Field(None, description="Folio (MF/RD) or UAN (EPF)")
    demat_id: str | None = Field(None, description="Demat ID (stock only)")
    invested_amount: float | None = Field(None, description="Cost basis for holdings accounts")
    current_value: float | None = Field(None, description="Market value for holdings accounts")
    investment_mode: str | None = Field(
        None,
        description="mutual_fund only: one_time (lump sum) or sip (monthly installments)",
    )
    initial_sip_paid_count: int | None = Field(
        None,
        ge=0,
        description="SIP installments already paid before tracking (mutual_fund + sip only)",
    )


class UpdateAccountRequest(BaseModel):
    name: str | None = Field(None, min_length=1)
    institution: str | None = None
    account_type: str | None = None
    loan_type: str | None = None
    loan_type_description: str | None = None
    credit_limit: float | None = None
    sanctioned_amount: float | None = None
    interest_rate: float | None = None
    emi_amount: float | None = None
    tenure_months: int | None = Field(None, ge=1)
    start_date: date | None = None
    due_day: int | None = Field(None, ge=1, le=31, description="Statement due day (credit_card) or EMI due day (loan)")
    currency: str | None = None
    parent_account_id: UUID | None = None
    opening_balance: float | None = Field(None, description="Starting balance for bank/cash/holdings accounts (incl. EPF)")
    initial_credit_used: float | None = Field(None, description="Starting amount owed on credit_card")
    initial_credit_used_date: date | None = Field(None, description="As-of date for initial_credit_used")
    initial_emi_paid_count: int | None = Field(None, ge=0, description="EMIs already paid (loan only)")
    account_number: str | None = Field(None, description="Bank account number (bank only)")
    ifsc_code: str | None = Field(None, description="IFSC code (bank only)")
    branch: str | None = Field(None, description="Branch name (bank only)")
    account_notes: str | None = Field(None, description="Other bank account notes (bank only)")
    folio_number: str | None = Field(None, description="Folio (MF/RD) or UAN (EPF)")
    demat_id: str | None = Field(None, description="Demat ID (stock only)")
    invested_amount: float | None = Field(None, description="Cost basis for holdings accounts")
    current_value: float | None = Field(None, description="Market value for holdings accounts")
    investment_mode: str | None = Field(
        None,
        description="mutual_fund only: one_time or sip",
    )
    initial_sip_paid_count: int | None = Field(
        None,
        ge=0,
        description="SIP installments already paid (mutual_fund + sip only)",
    )


class AccountResponse(BaseModel):
    id: UUID
    user_id: UUID
    account_type: str
    name: str
    institution: str | None
    loan_type: str | None = None
    loan_type_description: str | None = None
    credit_limit: float | None = None
    sanctioned_amount: float | None = None
    interest_rate: float | None = None
    emi_amount: float | None = None
    tenure_months: int | None = None
    start_date: date | None = None
    due_day: int | None = None
    currency: str
    parent_account_id: UUID | None = None
    transaction_count: int = 0
    balance: float | None = None
    invested_amount: float | None = None
    current_value: float | None = None
    pnl_amount: float | None = None
    pnl_percent: float | None = None
    credit_used: float | None = None
    credit_remaining: float | None = None
    outstanding: float | None = None
    amount_paid: float | None = None
    emi_paid_count: int | None = None
    emi_pending_count: int | None = None
    payment_history: list[PaymentHistoryItem] = Field(default_factory=list)
    opening_balance: float | None = None
    initial_credit_used: float | None = None
    initial_credit_used_date: date | None = None
    initial_emi_paid_count: int | None = None
    account_number: str | None = None
    ifsc_code: str | None = None
    branch: str | None = None
    account_notes: str | None = None
    folio_number: str | None = None
    demat_id: str | None = None
    investment_mode: str | None = None
    sip_paid_count: int | None = None
    sip_pending_count: int | None = None
    initial_sip_paid_count: int | None = None

    model_config = {"from_attributes": True}


def _decimal_opt(val: Decimal | None) -> float | None:
    return float(val) if val is not None else None


async def _account_response(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
    txn_count: int = 0,
) -> AccountResponse:
    metrics = await compute_account_metrics(session, account, user_id)
    payment_history: list[PaymentHistoryItem] = []
    emi_paid: int | None = None
    emi_pending: int | None = None
    sip_paid: int | None = None
    sip_pending: int | None = None

    if account.account_type in LOAN_TYPES:
        schedule = await compute_loan_schedule(session, account, user_id)
        payment_history = [
            PaymentHistoryItem(date=p["date"], amount=p["amount"]) for p in schedule["payment_history"]
        ]
        emi_paid = schedule["emi_paid_count"]
        emi_pending = schedule["emi_pending_count"]
    elif account.investment_mode == "sip" and account.account_type == "mutual_fund":
        schedule = await compute_sip_schedule(session, account, user_id)
        payment_history = [
            PaymentHistoryItem(date=p["date"], amount=p["amount"]) for p in schedule["payment_history"]
        ]
        sip_paid = schedule["sip_paid_count"]
        sip_pending = schedule["sip_pending_count"]

    opening = await read_opening_balance(session, account.id, user_id)
    initial_used, initial_used_date = await read_initial_credit_used(session, account.id, user_id)
    initial_emi_paid = await read_initial_emi_paid_count(
        session, account.id, user_id, account.emi_amount
    )
    initial_sip_paid = await read_initial_sip_paid_count(
        session, account.id, user_id, account.emi_amount
    )

    return AccountResponse(
        id=account.id,
        user_id=account.user_id,
        account_type=account.account_type,
        name=account.name,
        institution=account.institution,
        loan_type=account.loan_type,
        loan_type_description=account.loan_type_description,
        credit_limit=_decimal_opt(account.credit_limit),
        sanctioned_amount=_decimal_opt(account.sanctioned_amount),
        interest_rate=_decimal_opt(account.interest_rate),
        emi_amount=_decimal_opt(account.emi_amount),
        tenure_months=account.tenure_months,
        start_date=account.start_date,
        due_day=account.due_day,
        currency=account.currency or "INR",
        parent_account_id=account.parent_account_id,
        transaction_count=txn_count,
        balance=metrics["balance"],
        invested_amount=metrics["invested_amount"],
        current_value=metrics["current_value"],
        pnl_amount=metrics["pnl_amount"],
        pnl_percent=metrics["pnl_percent"],
        credit_used=metrics["credit_used"],
        credit_remaining=metrics["credit_remaining"],
        outstanding=metrics["outstanding"],
        amount_paid=metrics["amount_paid"],
        emi_paid_count=emi_paid,
        emi_pending_count=emi_pending,
        payment_history=payment_history,
        opening_balance=opening,
        initial_credit_used=initial_used,
        initial_credit_used_date=initial_used_date,
        initial_emi_paid_count=initial_emi_paid,
        account_number=account.account_number,
        ifsc_code=account.ifsc_code,
        branch=account.branch,
        account_notes=account.account_notes,
        folio_number=account.folio_number,
        demat_id=account.demat_id,
        investment_mode=account.investment_mode,
        sip_paid_count=sip_paid,
        sip_pending_count=sip_pending,
        initial_sip_paid_count=initial_sip_paid,
    )


async def _txn_counts(session: AsyncSession, user_id: UUID) -> dict[UUID, int]:
    result = await session.execute(
        select(Transaction.account_id, func.count(Transaction.id))
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.account_id)
    )
    return {row[0]: int(row[1]) for row in result.all()}


def _validate_account_type(account_type: str) -> None:
    if account_type not in ACCOUNT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"account_type must be one of: {', '.join(ACCOUNT_TYPES)}",
        )


def _normalize_loan_type(account_type: str, loan_type: str | None) -> str | None:
    if loan_type is None:
        return None
    if account_type not in LOAN_TYPES:
        raise HTTPException(status_code=400, detail="loan_type applies only to loan accounts")
    return loan_type.strip().lower()


def _validate_loan_type(account_type: str, loan_type: str | None, loan_type_description: str | None) -> None:
    if loan_type is not None and loan_type not in LOAN_DETAIL_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"loan_type must be one of: {', '.join(LOAN_DETAIL_TYPES)}",
        )
    if account_type in LOAN_TYPES and loan_type == "other":
        if not loan_type_description or not loan_type_description.strip():
            raise HTTPException(
                status_code=400,
                detail="loan_type_description is required when loan_type is other",
            )


def _validate_credit_limit(account_type: str, credit_limit: float | None) -> None:
    if credit_limit is not None and credit_limit < 0:
        raise HTTPException(status_code=400, detail="credit_limit cannot be negative")
    if credit_limit is not None and account_type not in LIMIT_ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="credit_limit applies only to credit_card accounts")


def _validate_sanctioned_amount(account_type: str, sanctioned_amount: float | None) -> None:
    if sanctioned_amount is not None and sanctioned_amount < 0:
        raise HTTPException(status_code=400, detail="sanctioned_amount cannot be negative")
    if sanctioned_amount is not None and account_type not in SANCTIONED_ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="sanctioned_amount applies only to loan accounts")


def _validate_investment_valuation(
    account_type: str,
    invested_amount: float | None,
    current_value: float | None,
) -> None:
    if invested_amount is not None and invested_amount < 0:
        raise HTTPException(status_code=400, detail="invested_amount cannot be negative")
    if current_value is not None and current_value < 0:
        raise HTTPException(status_code=400, detail="current_value cannot be negative")
    if invested_amount is not None and account_type not in HOLDINGS_TYPES:
        raise HTTPException(
            status_code=400,
            detail="invested_amount applies only to holdings accounts",
        )
    if current_value is not None and account_type not in HOLDINGS_TYPES:
        raise HTTPException(
            status_code=400,
            detail="current_value applies only to holdings accounts",
        )


def _seed_investment_valuation_on_create(
    account: Account,
    *,
    opening_balance: float | None,
    invested_amount: float | None,
    current_value: float | None,
) -> None:
    if account.account_type not in HOLDINGS_TYPES:
        return
    if invested_amount is not None:
        account.invested_amount = Decimal(str(invested_amount))
    elif opening_balance is not None and opening_balance > 0:
        account.invested_amount = Decimal(str(opening_balance))
    if current_value is not None:
        account.current_value = Decimal(str(current_value))
    elif opening_balance is not None and opening_balance > 0:
        account.current_value = Decimal(str(opening_balance))
    elif invested_amount is not None:
        account.current_value = Decimal(str(invested_amount))


def _apply_investment_valuation(
    account: Account,
    *,
    invested_amount: float | None,
    current_value: float | None,
    fields_set: set[str],
) -> None:
    if account.account_type not in HOLDINGS_TYPES:
        return
    if invested_amount is not None:
        account.invested_amount = Decimal(str(invested_amount))
    elif "invested_amount" in fields_set:
        account.invested_amount = None
    if current_value is not None:
        account.current_value = Decimal(str(current_value))
    elif "current_value" in fields_set:
        account.current_value = None


def _validate_opening_balance(account_type: str, opening_balance: float | None) -> None:
    if opening_balance is not None and opening_balance < 0:
        raise HTTPException(status_code=400, detail="opening_balance cannot be negative")
    if opening_balance is not None and account_type not in OPENING_BALANCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="opening_balance applies only to bank, cash, holdings, and EPF accounts",
        )


def _validate_initial_credit_used(
    account_type: str,
    initial_credit_used: float | None,
    initial_credit_used_date: date | None,
) -> None:
    if initial_credit_used is not None and initial_credit_used < 0:
        raise HTTPException(status_code=400, detail="initial_credit_used cannot be negative")
    if initial_credit_used is not None and account_type != "credit_card":
        raise HTTPException(
            status_code=400,
            detail="initial_credit_used applies only to credit_card accounts",
        )
    if initial_credit_used_date is not None and account_type != "credit_card":
        raise HTTPException(
            status_code=400,
            detail="initial_credit_used_date applies only to credit_card accounts",
        )
    if initial_credit_used is not None and initial_credit_used > 0 and initial_credit_used_date is None:
        raise HTTPException(
            status_code=400,
            detail="initial_credit_used_date is required when initial_credit_used is set",
        )


def _validate_initial_emi_paid_count(
    account_type: str,
    initial_emi_paid_count: int | None,
    *,
    sanctioned_amount: float | Decimal | None,
    emi_amount: float | Decimal | None,
    tenure_months: int | None,
) -> None:
    if initial_emi_paid_count is not None and account_type != "loan":
        raise HTTPException(
            status_code=400,
            detail="initial_emi_paid_count applies only to loan accounts",
        )
    if initial_emi_paid_count is None:
        return
    if initial_emi_paid_count < 0:
        raise HTTPException(status_code=400, detail="initial_emi_paid_count cannot be negative")
    if sanctioned_amount is None or float(sanctioned_amount) <= 0:
        raise HTTPException(
            status_code=400,
            detail="sanctioned_amount is required when initial_emi_paid_count is set",
        )
    if initial_emi_paid_count > 0 and (emi_amount is None or float(emi_amount) <= 0):
        raise HTTPException(
            status_code=400,
            detail="emi_amount is required when initial_emi_paid_count is greater than zero",
        )
    if tenure_months is not None and initial_emi_paid_count > tenure_months:
        raise HTTPException(
            status_code=400,
            detail="initial_emi_paid_count cannot exceed tenure_months",
        )


async def _apply_initial_loan_state(
    session: AsyncSession,
    account: Account,
    user_id: UUID,
    initial_emi_paid_count: int | None,
) -> None:
    if account.account_type != "loan":
        await upsert_initial_loan_state(session, account, user_id, None)
        return
    try:
        await upsert_initial_loan_state(session, account, user_id, initial_emi_paid_count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _validate_initial_sip_paid_count(
    account_type: str,
    investment_mode: str | None,
    initial_sip_paid_count: int | None,
    *,
    emi_amount: float | Decimal | None,
    tenure_months: int | None,
) -> None:
    if initial_sip_paid_count is not None and (
        account_type != "mutual_fund" or investment_mode != "sip"
    ):
        raise HTTPException(
            status_code=400,
            detail="initial_sip_paid_count applies only to SIP mutual fund accounts",
        )
    if initial_sip_paid_count is None:
        return
    if initial_sip_paid_count < 0:
        raise HTTPException(status_code=400, detail="initial_sip_paid_count cannot be negative")
    if initial_sip_paid_count > 0 and (emi_amount is None or float(emi_amount) <= 0):
        raise HTTPException(
            status_code=400,
            detail="emi_amount is required when initial_sip_paid_count is greater than zero",
        )
    if tenure_months is not None and initial_sip_paid_count > tenure_months:
        raise HTTPException(
            status_code=400,
            detail="initial_sip_paid_count cannot exceed tenure_months",
        )


def _validate_investment_mode_api(
    account_type: str,
    investment_mode: str | None,
    *,
    emi_amount: float | Decimal | None = None,
    due_day: int | None = None,
    start_date: date | None = None,
    tenure_months: int | None = None,
) -> None:
    try:
        validate_investment_mode(
            account_type,
            investment_mode,
            emi_amount=emi_amount,
            due_day=due_day,
            start_date=start_date,
            tenure_months=tenure_months,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _validate_due_day(
    account_type: str,
    due_day: int | None,
    *,
    investment_mode: str | None = None,
) -> None:
    allowed = account_type in DUE_DAY_TYPES or (
        account_type == "mutual_fund" and investment_mode == "sip"
    )
    if due_day is not None and not allowed:
        raise HTTPException(
            status_code=400,
            detail="due_day applies only to credit_card, loan, and SIP mutual fund accounts",
        )


def _validate_emi_amount_for_type(
    account_type: str,
    emi_amount: float | Decimal | None,
    *,
    investment_mode: str | None = None,
) -> None:
    if emi_amount is None:
        return
    allowed = account_type in LOAN_TYPES or (
        account_type == "mutual_fund" and investment_mode == "sip"
    )
    if not allowed:
        raise HTTPException(
            status_code=400,
            detail="emi_amount applies only to loan or SIP mutual fund accounts",
        )


def _validate_loan_start_date(
    account_type: str,
    *,
    emi_amount: float | Decimal | None,
    tenure_months: int | None,
    start_date: date | None,
) -> None:
    if account_type not in LOAN_TYPES:
        return
    has_emi = emi_amount is not None and float(emi_amount) > 0
    has_tenure = tenure_months is not None and tenure_months > 0
    if has_emi and has_tenure and start_date is None:
        raise HTTPException(
            status_code=400,
            detail="start_date is required when emi_amount and tenure_months are set",
        )


def _validate_bank_details_api(
    account_type: str,
    *,
    account_number: str | None,
    ifsc_code: str | None,
    branch: str | None,
    account_notes: str | None,
) -> None:
    try:
        validate_bank_details(
            account_type,
            account_number=account_number,
            ifsc_code=ifsc_code,
            branch=branch,
            account_notes=account_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _validate_investment_details_api(
    account_type: str,
    *,
    folio_number: str | None,
    demat_id: str | None,
) -> None:
    try:
        validate_investment_details(
            account_type,
            folio_number=folio_number,
            demat_id=demat_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _apply_investment_fields_api(
    account: Account,
    *,
    folio_number: str | None,
    demat_id: str | None,
    fields_set: set[str],
) -> None:
    apply_investment_fields(
        account,
        folio_number=folio_number,
        demat_id=demat_id,
        fields_set=fields_set,
    )


def _apply_bank_fields_api(
    account: Account,
    *,
    account_number: str | None,
    ifsc_code: str | None,
    branch: str | None,
    account_notes: str | None,
    fields_set: set[str],
) -> None:
    try:
        apply_bank_fields(
            account,
            account_number=account_number,
            ifsc_code=ifsc_code,
            branch=branch,
            account_notes=account_notes,
            fields_set=fields_set,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _validate_parent_account(account_type: str, parent_account_id: UUID | None) -> None:
    if account_type in PARENT_REQUIRED_TYPES and parent_account_id is None:
        raise HTTPException(
            status_code=400,
            detail="parent_account_id is required for credit_card, loan, and liquid investment accounts",
        )
    if account_type in PRIMARY_TYPES and parent_account_id is not None:
        raise HTTPException(
            status_code=400,
            detail="parent_account_id applies only to derived accounts",
        )


async def _resolve_parent(
    session: AsyncSession,
    user_id: UUID,
    account_type: str,
    parent_account_id: UUID | None,
) -> UUID | None:
    _validate_parent_account(account_type, parent_account_id)
    if parent_account_id is None:
        return None
    result = await session.execute(
        select(Account).where(Account.id == parent_account_id, Account.user_id == user_id)
    )
    parent = result.scalar_one_or_none()
    if not parent or parent.account_type not in PRIMARY_TYPES:
        raise HTTPException(
            status_code=400,
            detail="parent_account_id must reference a bank or cash account",
        )
    return parent_account_id


def _apply_loan_fields(
    account: Account,
    *,
    loan_type: str | None,
    loan_type_description: str | None,
    sanctioned_amount: float | None,
    interest_rate: float | None,
    emi_amount: float | None,
    tenure_months: int | None,
    start_date: date | None,
    due_day: int | None,
    fields_set: set[str],
) -> None:
    if loan_type is not None or "loan_type" in fields_set:
        account.loan_type = loan_type
    if loan_type_description is not None or "loan_type_description" in fields_set:
        account.loan_type_description = loan_type_description.strip() if loan_type_description else None
    if sanctioned_amount is not None:
        account.sanctioned_amount = Decimal(str(sanctioned_amount))
    elif "sanctioned_amount" in fields_set:
        account.sanctioned_amount = None
    if interest_rate is not None:
        account.interest_rate = Decimal(str(interest_rate))
    elif "interest_rate" in fields_set:
        account.interest_rate = None
    if emi_amount is not None:
        account.emi_amount = Decimal(str(emi_amount))
    elif "emi_amount" in fields_set:
        account.emi_amount = None
    if tenure_months is not None:
        account.tenure_months = tenure_months
    elif "tenure_months" in fields_set:
        account.tenure_months = None
    if start_date is not None or "start_date" in fields_set:
        account.start_date = start_date
    if due_day is not None:
        account.due_day = due_day
    elif "due_day" in fields_set:
        account.due_day = None


def _clear_incompatible_fields(account: Account) -> None:
    if account.account_type not in LIMIT_ACCOUNT_TYPES:
        account.credit_limit = None
    if account.account_type not in SANCTIONED_ACCOUNT_TYPES:
        account.sanctioned_amount = None
        account.loan_type = None
        account.loan_type_description = None
        if account.account_type != "mutual_fund" or account.investment_mode != "sip":
            account.emi_amount = None
    if account.account_type not in DUE_DAY_TYPES and not (
        account.account_type == "mutual_fund" and account.investment_mode == "sip"
    ):
        account.due_day = None
    if account.account_type == "mutual_fund":
        account.interest_rate = None
        if account.investment_mode != "sip":
            account.investment_mode = account.investment_mode or "one_time"
            clear_sip_schedule_fields(account)
    elif account.account_type not in LOAN_TYPES and account.account_type not in INVESTMENT_FD_TYPES:
        account.interest_rate = None
        account.tenure_months = None
        account.start_date = None
        account.investment_mode = None
    elif account.account_type in INVESTMENT_FD_TYPES:
        account.emi_amount = None
        account.due_day = None
        account.loan_type = None
        account.loan_type_description = None
        account.sanctioned_amount = None
        account.investment_mode = None
    else:
        account.investment_mode = None
    if account.account_type not in BANK_DETAIL_TYPES:
        clear_bank_fields(account)
    if account.account_type not in FOLIO_TYPES and account.account_type not in DEMAT_TYPES:
        clear_investment_fields(account)
    elif account.account_type in FOLIO_TYPES:
        account.demat_id = None
    elif account.account_type in DEMAT_TYPES:
        account.folio_number = None
    if account.account_type not in HOLDINGS_TYPES:
        account.invested_amount = None
        account.current_value = None


@router.post("/accounts", response_model=AccountResponse)
async def create_account(
    body: CreateAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    _validate_account_type(body.account_type)
    _validate_credit_limit(body.account_type, body.credit_limit)
    _validate_sanctioned_amount(body.account_type, body.sanctioned_amount)
    loan_type = _normalize_loan_type(body.account_type, body.loan_type)
    _validate_loan_type(body.account_type, loan_type, body.loan_type_description)
    _validate_opening_balance(body.account_type, body.opening_balance)
    _validate_investment_valuation(body.account_type, body.invested_amount, body.current_value)
    _validate_initial_credit_used(
        body.account_type,
        body.initial_credit_used,
        body.initial_credit_used_date,
    )
    _validate_initial_emi_paid_count(
        body.account_type,
        body.initial_emi_paid_count,
        sanctioned_amount=body.sanctioned_amount,
        emi_amount=body.emi_amount,
        tenure_months=body.tenure_months,
    )
    mf_mode = body.investment_mode
    if body.account_type == "mutual_fund" and mf_mode is None:
        mf_mode = "one_time"
    _validate_investment_mode_api(
        body.account_type,
        mf_mode,
        emi_amount=body.emi_amount,
        due_day=body.due_day,
        start_date=body.start_date,
        tenure_months=body.tenure_months,
    )
    _validate_emi_amount_for_type(body.account_type, body.emi_amount, investment_mode=mf_mode)
    _validate_initial_sip_paid_count(
        body.account_type,
        mf_mode,
        body.initial_sip_paid_count,
        emi_amount=body.emi_amount,
        tenure_months=body.tenure_months,
    )
    _validate_due_day(body.account_type, body.due_day, investment_mode=mf_mode)
    _validate_loan_start_date(
        body.account_type,
        emi_amount=body.emi_amount,
        tenure_months=body.tenure_months,
        start_date=body.start_date,
    )
    _validate_bank_details_api(
        body.account_type,
        account_number=body.account_number,
        ifsc_code=body.ifsc_code,
        branch=body.branch,
        account_notes=body.account_notes,
    )
    _validate_investment_details_api(
        body.account_type,
        folio_number=body.folio_number,
        demat_id=body.demat_id,
    )
    parent_id = await _resolve_parent(session, user.id, body.account_type, body.parent_account_id)
    account = Account(
        user_id=user.id,
        account_type=body.account_type,
        name=body.name.strip(),
        institution=body.institution.strip() if body.institution else None,
        loan_type=loan_type,
        loan_type_description=body.loan_type_description.strip()
        if body.loan_type_description
        else None,
        credit_limit=Decimal(str(body.credit_limit)) if body.credit_limit is not None else None,
        sanctioned_amount=Decimal(str(body.sanctioned_amount))
        if body.sanctioned_amount is not None
        else None,
        interest_rate=Decimal(str(body.interest_rate)) if body.interest_rate is not None else None,
        emi_amount=Decimal(str(body.emi_amount)) if body.emi_amount is not None else None,
        tenure_months=body.tenure_months,
        start_date=body.start_date,
        due_day=body.due_day,
        currency=(body.currency or "INR").strip().upper(),
        parent_account_id=parent_id,
        account_number=normalize_optional_text(body.account_number),
        ifsc_code=normalize_ifsc(body.ifsc_code),
        branch=normalize_optional_text(body.branch),
        account_notes=normalize_optional_text(body.account_notes),
        folio_number=normalize_optional_text(body.folio_number),
        demat_id=normalize_optional_text(body.demat_id),
        investment_mode=mf_mode if body.account_type == "mutual_fund" else None,
    )
    _clear_incompatible_fields(account)
    _seed_investment_valuation_on_create(
        account,
        opening_balance=body.opening_balance,
        invested_amount=body.invested_amount,
        current_value=body.current_value,
    )
    session.add(account)
    await session.flush()
    if body.opening_balance is not None and body.opening_balance > 0:
        await upsert_opening_balance(session, account, user.id, body.opening_balance)
    if body.initial_credit_used is not None and body.initial_credit_used > 0:
        await upsert_initial_credit_used(
            session,
            account,
            user.id,
            body.initial_credit_used,
            body.initial_credit_used_date,
        )
    if body.initial_emi_paid_count is not None:
        await _apply_initial_loan_state(session, account, user.id, body.initial_emi_paid_count)
    if body.initial_sip_paid_count is not None:
        await upsert_initial_sip_state(session, account, user.id, body.initial_sip_paid_count)
    await session.commit()
    await session.refresh(account)
    counts = await _txn_counts(session, user.id)
    return await _account_response(session, account, user.id, counts.get(account.id, 0))


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Account).where(Account.user_id == user.id).order_by(Account.created_at.asc())
    )
    rows = result.scalars().all()
    counts = await _txn_counts(session, user.id)
    return [await _account_response(session, a, user.id, counts.get(a.id, 0)) for a in rows]


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await _get_owned_account(session, user.id, account_id)
    counts = await _txn_counts(session, user.id)
    return await _account_response(session, account, user.id, counts.get(account.id, 0))


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    body: UpdateAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await _get_owned_account(session, user.id, account_id)
    fields_set = body.model_fields_set
    if body.account_type is not None:
        _validate_account_type(body.account_type)
        account.account_type = body.account_type
    if body.name is not None:
        account.name = body.name.strip()
    if body.institution is not None:
        account.institution = body.institution.strip() or None
    if body.credit_limit is not None:
        account.credit_limit = Decimal(str(body.credit_limit))
    elif "credit_limit" in fields_set:
        account.credit_limit = None

    new_type = account.account_type
    raw_loan_type = body.loan_type if "loan_type" in fields_set else account.loan_type
    loan_type = _normalize_loan_type(new_type, raw_loan_type) if raw_loan_type or new_type in LOAN_TYPES else None
    raw_desc = body.loan_type_description if "loan_type_description" in fields_set else account.loan_type_description
    _validate_loan_type(new_type, loan_type, raw_desc)
    _apply_loan_fields(
        account,
        loan_type=loan_type if "loan_type" in fields_set or new_type in LOAN_TYPES else account.loan_type,
        loan_type_description=raw_desc,
        sanctioned_amount=body.sanctioned_amount,
        interest_rate=body.interest_rate,
        emi_amount=body.emi_amount,
        tenure_months=body.tenure_months,
        start_date=body.start_date,
        due_day=body.due_day,
        fields_set=fields_set,
    )
    _apply_bank_fields_api(
        account,
        account_number=body.account_number if "account_number" in fields_set else account.account_number,
        ifsc_code=body.ifsc_code if "ifsc_code" in fields_set else account.ifsc_code,
        branch=body.branch if "branch" in fields_set else account.branch,
        account_notes=body.account_notes if "account_notes" in fields_set else account.account_notes,
        fields_set=fields_set,
    )
    _validate_bank_details_api(
        new_type,
        account_number=account.account_number,
        ifsc_code=account.ifsc_code,
        branch=account.branch,
        account_notes=account.account_notes,
    )
    _apply_investment_fields_api(
        account,
        folio_number=body.folio_number if "folio_number" in fields_set else account.folio_number,
        demat_id=body.demat_id if "demat_id" in fields_set else account.demat_id,
        fields_set=fields_set,
    )
    if "investment_mode" in fields_set:
        try:
            apply_investment_mode(account, body.investment_mode, fields_set)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    _validate_investment_details_api(
        new_type,
        folio_number=account.folio_number,
        demat_id=account.demat_id,
    )

    if body.currency is not None:
        account.currency = body.currency.strip().upper()
    if body.parent_account_id is not None or "parent_account_id" in fields_set:
        pid = body.parent_account_id if "parent_account_id" in fields_set else account.parent_account_id
        account.parent_account_id = await _resolve_parent(session, user.id, new_type, pid)

    limit_val = float(account.credit_limit) if account.credit_limit is not None else None
    sanctioned_val = float(account.sanctioned_amount) if account.sanctioned_amount is not None else None
    _validate_credit_limit(account.account_type, limit_val)
    _validate_sanctioned_amount(account.account_type, sanctioned_val)
    if "opening_balance" in fields_set:
        _validate_opening_balance(account.account_type, body.opening_balance)
        if account.account_type in OPENING_BALANCE_TYPES:
            await upsert_opening_balance(session, account, user.id, body.opening_balance)
    if "invested_amount" in fields_set or "current_value" in fields_set:
        _validate_investment_valuation(
            account.account_type,
            body.invested_amount if "invested_amount" in fields_set else None,
            body.current_value if "current_value" in fields_set else None,
        )
        _apply_investment_valuation(
            account,
            invested_amount=body.invested_amount if "invested_amount" in fields_set else None,
            current_value=body.current_value if "current_value" in fields_set else None,
            fields_set=fields_set,
        )
    if "initial_credit_used" in fields_set or "initial_credit_used_date" in fields_set:
        existing_used, existing_date = await read_initial_credit_used(session, account.id, user.id)
        used = body.initial_credit_used if "initial_credit_used" in fields_set else existing_used
        used_date = (
            body.initial_credit_used_date if "initial_credit_used_date" in fields_set else existing_date
        )
        _validate_initial_credit_used(account.account_type, used, used_date)
        if account.account_type == "credit_card":
            await upsert_initial_credit_used(session, account, user.id, used, used_date)
    loan_seed_fields = {
        "initial_emi_paid_count",
        "sanctioned_amount",
        "emi_amount",
        "tenure_months",
        "start_date",
    }
    if "initial_emi_paid_count" in fields_set:
        _validate_initial_emi_paid_count(
            account.account_type,
            body.initial_emi_paid_count,
            sanctioned_amount=account.sanctioned_amount,
            emi_amount=account.emi_amount,
            tenure_months=account.tenure_months,
        )
        await _apply_initial_loan_state(session, account, user.id, body.initial_emi_paid_count)
    elif loan_seed_fields.intersection(fields_set) and account.account_type == "loan":
        existing_paid = await read_initial_emi_paid_count(
            session, account.id, user.id, account.emi_amount
        )
        if existing_paid is not None:
            await _apply_initial_loan_state(session, account, user.id, existing_paid)
    sip_seed_fields = {
        "initial_sip_paid_count",
        "emi_amount",
        "tenure_months",
        "start_date",
        "investment_mode",
    }
    if "initial_sip_paid_count" in fields_set:
        _validate_initial_sip_paid_count(
            account.account_type,
            account.investment_mode,
            body.initial_sip_paid_count,
            emi_amount=account.emi_amount,
            tenure_months=account.tenure_months,
        )
        await upsert_initial_sip_state(session, account, user.id, body.initial_sip_paid_count)
    elif sip_seed_fields.intersection(fields_set) and account.investment_mode == "sip":
        existing_sip_paid = await read_initial_sip_paid_count(
            session, account.id, user.id, account.emi_amount
        )
        if existing_sip_paid is not None:
            await upsert_initial_sip_state(session, account, user.id, existing_sip_paid)
    _clear_incompatible_fields(account)
    if account.account_type != "credit_card":
        await upsert_initial_credit_used(session, account, user.id, None, None)
    if account.account_type != "loan":
        await _apply_initial_loan_state(session, account, user.id, None)
    if account.investment_mode != "sip":
        await upsert_initial_sip_state(session, account, user.id, None)
    _validate_investment_mode_api(
        account.account_type,
        account.investment_mode,
        emi_amount=account.emi_amount,
        due_day=account.due_day,
        start_date=account.start_date,
        tenure_months=account.tenure_months,
    )
    _validate_emi_amount_for_type(
        account.account_type,
        float(account.emi_amount) if account.emi_amount is not None else None,
        investment_mode=account.investment_mode,
    )
    _validate_due_day(account.account_type, account.due_day, investment_mode=account.investment_mode)
    _validate_loan_start_date(
        account.account_type,
        emi_amount=account.emi_amount,
        tenure_months=account.tenure_months,
        start_date=account.start_date,
    )
    await session.commit()
    await session.refresh(account)
    counts = await _txn_counts(session, user.id)
    return await _account_response(session, account, user.id, counts.get(account.id, 0))


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await _get_owned_account(session, user.id, account_id)
    txn_count = await session.execute(
        select(func.count(Transaction.id)).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user.id,
        )
    )
    if (txn_count.scalar_one() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Account has transactions. Delete or move them before removing this account.",
        )
    bill_count = await session.execute(
        select(func.count(RecurringBill.id)).where(
            RecurringBill.account_id == account_id,
            RecurringBill.user_id == user.id,
        )
    )
    if (bill_count.scalar_one() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Account is linked to recurring bills. Remove those bills first.",
        )
    await session.delete(account)
    await session.commit()


async def _get_owned_account(
    session: AsyncSession, user_id: UUID, account_id: UUID
) -> Account:
    result = await session.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account
