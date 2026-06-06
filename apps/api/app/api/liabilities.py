from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_async_session, Liability, User

router = APIRouter()

LIABILITY_TYPES = ("home_loan", "personal_loan", "cc", "other")


class CreateLiabilityRequest(BaseModel):
    liability_type: str = Field(..., description="home_loan | personal_loan | cc | other")
    name: str = Field(..., min_length=1)
    outstanding_amount: float = Field(..., ge=0)
    interest_rate: float | None = None
    emi: float | None = None
    due_day: int | None = Field(None, ge=1, le=31)


class LiabilityResponse(BaseModel):
    id: UUID
    liability_type: str
    name: str
    outstanding_amount: float
    interest_rate: float | None = None
    emi: float | None = None
    due_day: int | None = None


@router.post("/liabilities", response_model=LiabilityResponse)
async def create_liability(
    body: CreateLiabilityRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if body.liability_type not in LIABILITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"liability_type must be one of: {', '.join(LIABILITY_TYPES)}",
        )
    liability = Liability(
        user_id=user.id,
        liability_type=body.liability_type,
        name=body.name.strip(),
        outstanding_amount=Decimal(str(body.outstanding_amount)),
        interest_rate=Decimal(str(body.interest_rate)) if body.interest_rate is not None else None,
        emi=Decimal(str(body.emi)) if body.emi is not None else None,
        due_day=body.due_day,
    )
    session.add(liability)
    await session.commit()
    await session.refresh(liability)
    return LiabilityResponse(
        id=liability.id,
        liability_type=liability.liability_type,
        name=liability.name,
        outstanding_amount=float(liability.outstanding_amount),
        interest_rate=float(liability.interest_rate) if liability.interest_rate is not None else None,
        emi=float(liability.emi) if liability.emi is not None else None,
        due_day=liability.due_day,
    )


@router.get("/liabilities", response_model=list[LiabilityResponse])
async def list_liabilities(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Liability).where(Liability.user_id == user.id))
    return [
        LiabilityResponse(
            id=liability.id,
            liability_type=liability.liability_type,
            name=liability.name,
            outstanding_amount=float(liability.outstanding_amount),
            interest_rate=float(liability.interest_rate) if liability.interest_rate is not None else None,
            emi=float(liability.emi) if liability.emi is not None else None,
            due_day=liability.due_day,
        )
        for liability in result.scalars().all()
    ]
