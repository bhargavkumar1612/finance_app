import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session, Account, User
from app.api.auth import get_current_user

router = APIRouter()


class CreateAccountRequest(BaseModel):
    account_type: str = Field(..., description="bank | credit_card | wallet | cash")
    name: str
    institution: str | None = None


class AccountResponse(BaseModel):
    id: UUID
    user_id: UUID
    account_type: str
    name: str
    institution: str | None

    model_config = {"from_attributes": True}


@router.post("/accounts", response_model=AccountResponse)
async def create_account(
    body: CreateAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if body.account_type not in ("bank", "credit_card", "wallet", "cash"):
        raise HTTPException(status_code=400, detail="account_type must be one of: bank, credit_card, wallet, cash")
    account = Account(
        user_id=user.id,
        account_type=body.account_type,
        name=body.name,
        institution=body.institution,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Account).where(Account.user_id == user.id))
    rows = result.scalars().all()
    return list(rows)
