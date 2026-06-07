"""Financial persona CRUD — user-editable copilot profile."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_async_session
from app.db.models import User
from app.services.persona_store import get_persona, upsert_persona

router = APIRouter()


class PersonaResponse(BaseModel):
    body: str = ""
    traits: dict = Field(default_factory=dict)
    updated_at: str | None = None


class PersonaUpdate(BaseModel):
    body: str | None = None
    traits: dict | None = None


@router.get("/persona", response_model=PersonaResponse)
async def read_persona(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    data = await get_persona(session, user.id)
    return PersonaResponse(**data)


@router.put("/persona", response_model=PersonaResponse)
async def update_persona(
    payload: PersonaUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    data = await upsert_persona(
        session,
        user.id,
        body=payload.body,
        traits=payload.traits,
    )
    return PersonaResponse(**data)
