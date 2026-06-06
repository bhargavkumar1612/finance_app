from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID

from app.db import get_async_session, Transaction, User, Account
from app.ingestion.deduper import fingerprint_for_transaction, remove_fingerprints, clear_import_fingerprints
from app.services.transaction_semantics import classify_transaction

router = APIRouter()


class CreateTransactionRequest(BaseModel):
    amount: Decimal = Field(..., description="Debit as negative, credit as positive")
    transaction_date: date
    account_id: UUID
    currency: str = "INR"
    merchant: str | None = None
    category: str | None = None
    subcategory: str | None = None
    raw_description: str | None = None
    nw_impact: str | None = None

    model_config = {"json_schema_extra": {"example": {"amount": -450, "transaction_date": "2026-02-26", "account_id": "..."}}}


class TransactionResponse(BaseModel):
    id: UUID
    amount: Decimal
    transaction_date: date
    account_id: UUID
    account_name: str | None = None
    account_type: str | None = None
    currency: str
    merchant: str | None = None
    category: str | None = None
    subcategory: str | None = None
    raw_description: str | None = None
    source: str
    nw_impact: str


def _transaction_response(
    txn: Transaction,
    account_name: str | None = None,
    account_type: str | None = None,
) -> TransactionResponse:
    return TransactionResponse(
        id=txn.id,
        amount=txn.amount,
        transaction_date=txn.transaction_date,
        account_id=txn.account_id,
        account_name=account_name,
        account_type=account_type,
        currency=txn.currency,
        merchant=txn.merchant,
        category=txn.category,
        subcategory=txn.subcategory,
        raw_description=txn.raw_description,
        source=txn.source,
        nw_impact=txn.nw_impact,
    )


from app.api.auth import get_current_user


@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    body: CreateTransactionRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Account).where(Account.id == body.account_id, Account.user_id == user.id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not owned by user")
        
    # Guardrails: Date and Value validation
    if body.transaction_date > date.today():
        raise HTTPException(status_code=400, detail="Transaction date cannot be in the future.")
    if body.amount == 0:
        raise HTTPException(status_code=400, detail="Transaction amount cannot be zero.")

    impact = body.nw_impact
    if not impact:
        impact = classify_transaction(
            body.amount,
            category=body.category,
            merchant=body.merchant,
            raw_description=body.raw_description,
            account_type=account.account_type,
        ).value

    txn = Transaction(
        user_id=user.id,
        account_id=body.account_id,
        amount=body.amount,
        currency=body.currency,
        transaction_date=body.transaction_date,
        merchant=body.merchant,
        category=body.category,
        subcategory=body.subcategory,
        raw_description=body.raw_description,
        source="manual",
        confidence=None,
        nw_impact=impact,
    )
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    acc = await session.get(Account, body.account_id)
    return _transaction_response(
        txn,
        account_name=acc.name if acc else None,
        account_type=acc.account_type if acc else None,
    )


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
    limit: int = 500,
):
    cap = min(max(limit, 1), 2000)
    result = await session.execute(
        select(Transaction, Account.name, Account.account_type)
        .join(Account, Transaction.account_id == Account.id)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.transaction_date.desc())
        .limit(cap)
    )
    return [
        _transaction_response(txn, account_name=name, account_type=atype)
        for txn, name, atype in result.all()
    ]


class BulkDeleteTransactionsRequest(BaseModel):
    ids: list[UUID] = Field(..., min_length=1, max_length=500)


class BulkDeleteTransactionsResponse(BaseModel):
    deleted: int
    not_found: list[str] = Field(default_factory=list)


class DeleteAllTransactionsResponse(BaseModel):
    deleted: int


class UpdateTransactionRequest(BaseModel):
    amount: Decimal | None = None
    transaction_date: date | None = None
    merchant: str | None = None
    category: str | None = None
    subcategory: str | None = None
    raw_description: str | None = None


@router.put("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    body: UpdateTransactionRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user.id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if body.amount is not None:
        if body.amount == 0:
            raise HTTPException(status_code=400, detail="Transaction amount cannot be zero.")
        txn.amount = body.amount
    if body.transaction_date is not None:
        if body.transaction_date > date.today():
            raise HTTPException(status_code=400, detail="Transaction date cannot be in the future.")
        txn.transaction_date = body.transaction_date
    if body.merchant is not None:
        txn.merchant = body.merchant
    if body.category is not None:
        txn.category = body.category
    if body.subcategory is not None:
        txn.subcategory = body.subcategory
    if body.raw_description is not None:
        txn.raw_description = body.raw_description
    acc = await session.get(Account, txn.account_id)
    if body.amount is not None or body.category is not None or body.merchant is not None or body.raw_description is not None:
        txn.nw_impact = classify_transaction(
            txn.amount,
            category=txn.category,
            merchant=txn.merchant,
            raw_description=txn.raw_description,
            account_type=acc.account_type if acc else None,
        ).value

    await session.commit()
    await session.refresh(txn)
    acc = await session.get(Account, txn.account_id)
    return _transaction_response(
        txn,
        account_name=acc.name if acc else None,
        account_type=acc.account_type if acc else None,
    )


@router.delete("/transactions/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    fp = fingerprint_for_transaction(
        txn.transaction_date, txn.amount, txn.merchant, str(txn.account_id)
    )
    await session.delete(txn)
    await remove_fingerprints(session, user.id, [fp])
    await session.commit()


@router.post("/transactions/bulk-delete", response_model=BulkDeleteTransactionsResponse)
async def bulk_delete_transactions(
    body: BulkDeleteTransactionsRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    unique_ids = list(dict.fromkeys(body.ids))
    result = await session.execute(
        select(Transaction.id).where(
            Transaction.user_id == user.id,
            Transaction.id.in_(unique_ids),
        )
    )
    found_ids = {row[0] for row in result.all()}
    not_found = [str(i) for i in unique_ids if i not in found_ids]

    if found_ids:
        txns = await session.execute(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.id.in_(found_ids),
            )
        )
        fps = [
            fingerprint_for_transaction(t.transaction_date, t.amount, t.merchant, str(t.account_id))
            for t in txns.scalars().all()
        ]
        await session.execute(
            delete(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.id.in_(found_ids),
            )
        )
        await remove_fingerprints(session, user.id, fps)
        await session.commit()

    return BulkDeleteTransactionsResponse(deleted=len(found_ids), not_found=not_found)


@router.post("/transactions/delete-all", response_model=DeleteAllTransactionsResponse)
async def delete_all_transactions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete every transaction for the current user."""
    result = await session.execute(
        delete(Transaction).where(Transaction.user_id == user.id).returning(Transaction.id)
    )
    deleted_ids = result.all()
    await clear_import_fingerprints(session, user.id)
    await session.commit()
    return DeleteAllTransactionsResponse(deleted=len(deleted_ids))
