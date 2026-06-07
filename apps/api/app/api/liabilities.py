from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_async_session, Account, User
from app.services.account_types import LOAN_TYPES

router = APIRouter()

DEPRECATION_MSG = (
    "The /v1/liabilities API is deprecated. Create and manage loans via POST /v1/accounts "
    "with account_type=loan."
)


@router.post("/liabilities")
async def create_liability_deprecated():
    raise HTTPException(status_code=410, detail=DEPRECATION_MSG)


@router.get("/liabilities")
async def list_liabilities_deprecated(
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return loan accounts migrated from liabilities for backward-compatible reads."""
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</v1/accounts>; rel="successor-version"'
    result = await session.execute(
        select(Account).where(
            Account.user_id == user.id,
            Account.account_type.in_(tuple(LOAN_TYPES)),
        )
    )
    loans = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "liability_type": a.loan_type or "other",
            "name": a.name,
            "outstanding_amount": None,
            "interest_rate": float(a.interest_rate) if a.interest_rate else None,
            "emi": float(a.emi_amount) if a.emi_amount else None,
            "due_day": a.due_day,
            "_deprecated": True,
            "_message": DEPRECATION_MSG,
        }
        for a in loans
    ]
