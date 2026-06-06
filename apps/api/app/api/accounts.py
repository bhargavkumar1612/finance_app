from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_async_session, Account, RecurringBill, Transaction, User

router = APIRouter()

ACCOUNT_TYPES = ("bank", "credit_card", "wallet", "cash")


class CreateAccountRequest(BaseModel):
    account_type: str = Field(..., description="bank | credit_card | wallet | cash")
    name: str = Field(..., min_length=1)
    institution: str | None = None
    credit_limit: float | None = Field(None, description="Credit limit for credit_card accounts")
    currency: str = "INR"
    parent_account_id: UUID | None = Field(None, description="Required for credit_card and wallet")


class UpdateAccountRequest(BaseModel):
    name: str | None = Field(None, min_length=1)
    institution: str | None = None
    account_type: str | None = None
    credit_limit: float | None = None
    currency: str | None = None
    parent_account_id: UUID | None = None


class AccountResponse(BaseModel):
    id: UUID
    user_id: UUID
    account_type: str
    name: str
    institution: str | None
    credit_limit: float | None = None
    currency: str
    parent_account_id: UUID | None = None
    transaction_count: int = 0

    model_config = {"from_attributes": True}


def _account_response(account: Account, txn_count: int = 0) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        user_id=account.user_id,
        account_type=account.account_type,
        name=account.name,
        institution=account.institution,
        credit_limit=float(account.credit_limit) if account.credit_limit is not None else None,
        currency=account.currency or "INR",
        parent_account_id=account.parent_account_id,
        transaction_count=txn_count,
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


def _validate_credit_limit(account_type: str, credit_limit: float | None) -> None:
    if credit_limit is not None and credit_limit < 0:
        raise HTTPException(status_code=400, detail="credit_limit cannot be negative")
    if account_type != "credit_card" and credit_limit is not None:
        raise HTTPException(
            status_code=400,
            detail="credit_limit applies only to credit_card accounts",
        )


def _validate_parent_account(
    account_type: str,
    parent_account_id: UUID | None,
) -> None:
    if account_type in ("credit_card", "wallet") and parent_account_id is None:
        raise HTTPException(
            status_code=400,
            detail="parent_account_id is required for credit_card and wallet accounts",
        )
    if account_type in ("bank", "cash") and parent_account_id is not None:
        raise HTTPException(
            status_code=400,
            detail="parent_account_id applies only to credit_card or wallet accounts",
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
    if not parent or parent.account_type not in ("bank", "cash"):
        raise HTTPException(
            status_code=400,
            detail="parent_account_id must reference a bank or cash account",
        )
    return parent_account_id


@router.post("/accounts", response_model=AccountResponse)
async def create_account(
    body: CreateAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    _validate_account_type(body.account_type)
    _validate_credit_limit(body.account_type, body.credit_limit)
    parent_id = await _resolve_parent(session, user.id, body.account_type, body.parent_account_id)
    account = Account(
        user_id=user.id,
        account_type=body.account_type,
        name=body.name.strip(),
        institution=body.institution.strip() if body.institution else None,
        credit_limit=Decimal(str(body.credit_limit)) if body.credit_limit is not None else None,
        currency=(body.currency or "INR").strip().upper(),
        parent_account_id=parent_id,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return _account_response(account, 0)


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
    return [_account_response(a, counts.get(a.id, 0)) for a in rows]


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await _get_owned_account(session, user.id, account_id)
    counts = await _txn_counts(session, user.id)
    return _account_response(account, counts.get(account.id, 0))


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    body: UpdateAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await _get_owned_account(session, user.id, account_id)
    if body.account_type is not None:
        _validate_account_type(body.account_type)
        account.account_type = body.account_type
    if body.name is not None:
        account.name = body.name.strip()
    if body.institution is not None:
        account.institution = body.institution.strip() or None
    if body.credit_limit is not None:
        account.credit_limit = Decimal(str(body.credit_limit))
    elif "credit_limit" in body.model_fields_set:
        account.credit_limit = None
    if body.currency is not None:
        account.currency = body.currency.strip().upper()
    if body.parent_account_id is not None or "parent_account_id" in body.model_fields_set:
        new_type = account.account_type if body.account_type is None else body.account_type
        pid = body.parent_account_id if "parent_account_id" in body.model_fields_set else account.parent_account_id
        account.parent_account_id = await _resolve_parent(session, user.id, new_type, pid)
    new_type = account.account_type
    limit_val = float(account.credit_limit) if account.credit_limit is not None else None
    _validate_credit_limit(new_type, limit_val)
    if new_type != "credit_card":
        account.credit_limit = None
    await session.commit()
    await session.refresh(account)
    counts = await _txn_counts(session, user.id)
    return _account_response(account, counts.get(account.id, 0))


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
