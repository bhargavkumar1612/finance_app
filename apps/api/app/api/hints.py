"""Proactive data-quality hints for UI surfaces (Accounts, chat)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import User, get_async_session
from app.services.missing_data import check_missing_data

router = APIRouter()


class HintsResponse(BaseModel):
    hints: list[str]


@router.get("/hints", response_model=HintsResponse)
async def get_proactive_hints(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user),
) -> HintsResponse:
    hints = await check_missing_data(session, user.id)
    return HintsResponse(hints=hints)
