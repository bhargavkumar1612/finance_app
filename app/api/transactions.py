from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import os
from uuid import UUID

from app.db import get_async_session, Transaction, User, Account

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

    model_config = {"json_schema_extra": {"example": {"amount": -450, "transaction_date": "2026-02-26", "account_id": "..."}}}


class TransactionResponse(BaseModel):
    id: UUID
    amount: Decimal
    transaction_date: date
    account_id: UUID
    currency: str
    merchant: str | None = None
    category: str | None = None
    source: str

    model_config = {"from_attributes": True}


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
    )
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    return txn


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
    limit: int = 100,
):
    result = await session.execute(
        select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.transaction_date.desc()).limit(limit)
    )
    rows = result.scalars().all()
    return list(rows)
