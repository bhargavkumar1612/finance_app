"""CRUD for per-user financial persona (ADR 002)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserFinancialPersona


async def get_persona(session: AsyncSession, user_id: UUID) -> dict:
    result = await session.execute(
        select(UserFinancialPersona).where(UserFinancialPersona.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"body": "", "traits": {}, "updated_at": None}
    return {
        "body": row.body or "",
        "traits": row.traits or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


async def upsert_persona(
    session: AsyncSession,
    user_id: UUID,
    *,
    body: str | None = None,
    traits: dict | None = None,
) -> dict:
    result = await session.execute(
        select(UserFinancialPersona).where(UserFinancialPersona.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserFinancialPersona(user_id=user_id)
        session.add(row)
    if body is not None:
        row.body = body.strip()
    if traits is not None:
        row.traits = traits
    row.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(row)
    return {
        "body": row.body or "",
        "traits": row.traits or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
