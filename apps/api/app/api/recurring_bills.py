"""Recurring bills (rent / EMI): CRUD, due suggestions, confirm → transaction."""
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_async_session, Account, RecurringBill, Transaction, User
from app.services.recurring_suggestions import list_due_suggestions
from app.services.transaction_semantics import classify_transaction

router = APIRouter()


class RecurringBillCreate(BaseModel):
    account_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    amount: Decimal = Field(..., description="Expense as negative (e.g. rent -25000)")
    frequency: str = Field(..., pattern="^(monthly|weekly)$")
    due_day: int | None = Field(None, ge=1, le=31, description="Day of month for monthly bills")
    weekday: int | None = Field(None, ge=0, le=6, description="0=Monday … 6=Sunday for weekly")
    category: str | None = None


class RecurringBillUpdate(BaseModel):
    account_id: UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    amount: Decimal | None = None
    frequency: str | None = Field(None, pattern="^(monthly|weekly)$")
    due_day: int | None = Field(None, ge=1, le=31)
    weekday: int | None = Field(None, ge=0, le=6)
    category: str | None = None
    is_active: bool | None = None


class RecurringBillResponse(BaseModel):
    id: UUID
    account_id: UUID
    name: str
    amount: Decimal
    frequency: str
    due_day: int | None
    weekday: int | None
    category: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ConfirmRecurringRequest(BaseModel):
    """Use suggested_date from GET /recurring-bills/suggestions unless user edits."""
    transaction_date: date


@router.get("/recurring-bills/suggestions")
async def get_recurring_suggestions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    rows = await list_due_suggestions(session, user.id)
    return {"suggestions": rows}


@router.get("/recurring-bills", response_model=list[RecurringBillResponse])
async def list_recurring_bills(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    res = await session.execute(
        select(RecurringBill).where(RecurringBill.user_id == user.id).order_by(RecurringBill.created_at.desc())
    )
    return list(res.scalars().all())


@router.post("/recurring-bills", response_model=RecurringBillResponse)
async def create_recurring_bill(
    body: RecurringBillCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if body.frequency == "monthly" and body.due_day is None:
        raise HTTPException(status_code=400, detail="monthly bills require due_day (1–31)")
    if body.frequency == "weekly" and body.weekday is None:
        raise HTTPException(status_code=400, detail="weekly bills require weekday (0=Mon … 6=Sun)")
    acc = await session.execute(select(Account).where(Account.id == body.account_id, Account.user_id == user.id))
    if acc.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if body.amount == 0:
        raise HTTPException(status_code=400, detail="amount cannot be zero")
    bill = RecurringBill(
        user_id=user.id,
        account_id=body.account_id,
        name=body.name.strip(),
        amount=body.amount,
        frequency=body.frequency,
        due_day=body.due_day,
        weekday=body.weekday,
        category=body.category.strip() if body.category else None,
    )
    session.add(bill)
    await session.commit()
    await session.refresh(bill)
    return bill


@router.patch("/recurring-bills/{bill_id}", response_model=RecurringBillResponse)
async def update_recurring_bill(
    bill_id: UUID,
    body: RecurringBillUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    res = await session.execute(select(RecurringBill).where(RecurringBill.id == bill_id, RecurringBill.user_id == user.id))
    bill = res.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Recurring bill not found")
    if body.account_id is not None:
        r = await session.execute(select(Account).where(Account.id == body.account_id, Account.user_id == user.id))
        if r.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Account not found")
        bill.account_id = body.account_id
    if body.name is not None:
        bill.name = body.name.strip()
    if body.amount is not None:
        if body.amount == 0:
            raise HTTPException(status_code=400, detail="amount cannot be zero")
        bill.amount = body.amount
    if body.frequency is not None:
        bill.frequency = body.frequency
    if body.due_day is not None:
        bill.due_day = body.due_day
    if body.weekday is not None:
        bill.weekday = body.weekday
    if body.category is not None:
        bill.category = body.category.strip() or None
    if body.is_active is not None:
        bill.is_active = body.is_active
    await session.commit()
    await session.refresh(bill)
    return bill


@router.delete("/recurring-bills/{bill_id}", status_code=204)
async def delete_recurring_bill(
    bill_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    res = await session.execute(select(RecurringBill).where(RecurringBill.id == bill_id, RecurringBill.user_id == user.id))
    bill = res.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Recurring bill not found")
    await session.delete(bill)
    await session.commit()


@router.post("/recurring-bills/{bill_id}/confirm")
async def confirm_recurring_bill(
    bill_id: UUID,
    body: ConfirmRecurringRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    res = await session.execute(select(RecurringBill).where(RecurringBill.id == bill_id, RecurringBill.user_id == user.id))
    bill = res.scalar_one_or_none()
    if not bill or not bill.is_active:
        raise HTTPException(status_code=404, detail="Recurring bill not found")
    if body.transaction_date > date.today():
        raise HTTPException(status_code=400, detail="Transaction date cannot be in the future")

    # Billing period guard: avoid duplicate post for same cycle
    if bill.frequency == "monthly":
        y, m = body.transaction_date.year, body.transaction_date.month
        dup = await session.execute(
            select(Transaction.id).where(
                Transaction.user_id == user.id,
                Transaction.recurring_bill_id == bill.id,
                extract("year", Transaction.transaction_date) == y,
                extract("month", Transaction.transaction_date) == m,
            ).limit(1)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Already recorded for this billing month")
    else:
        from app.services.recurring_suggestions import _monday_of_iso_week

        mon = _monday_of_iso_week(body.transaction_date)
        sun = mon + timedelta(days=6)
        dup_w = await session.execute(
            select(Transaction.id).where(
                Transaction.user_id == user.id,
                Transaction.recurring_bill_id == bill.id,
                Transaction.transaction_date >= mon,
                Transaction.transaction_date <= sun,
            ).limit(1)
        )
        if dup_w.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Already recorded for this billing week")

    acc = await session.get(Account, bill.account_id)
    impact = classify_transaction(
        bill.amount,
        category=bill.category,
        merchant=bill.name,
        account_type=acc.account_type if acc else None,
    ).value
    txn = Transaction(
        user_id=user.id,
        account_id=bill.account_id,
        amount=bill.amount,
        currency="INR",
        transaction_date=body.transaction_date,
        merchant=bill.name,
        category=bill.category,
        source="recurring",
        recurring_bill_id=bill.id,
        nw_impact=impact,
    )
    session.add(txn)
    await session.commit()
    await session.refresh(txn)
    return {
        "id": str(txn.id),
        "amount": str(txn.amount),
        "transaction_date": txn.transaction_date.isoformat(),
        "account_id": str(txn.account_id),
        "recurring_bill_id": str(bill.id),
    }
