from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_async_session, Asset, User

router = APIRouter()

ASSET_TYPES = ("property", "mf", "stock", "gold", "other")


class CreateAssetRequest(BaseModel):
    asset_type: str = Field(..., description="property | mf | stock | gold | other")
    name: str = Field(..., min_length=1)
    current_value: float = Field(..., gt=0)
    valuation_date: date | None = None


class AssetResponse(BaseModel):
    id: UUID
    asset_type: str
    name: str
    current_value: float
    valuation_date: date | None = None


@router.post("/assets", response_model=AssetResponse)
async def create_asset(
    body: CreateAssetRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if body.asset_type not in ASSET_TYPES:
        raise HTTPException(status_code=400, detail=f"asset_type must be one of: {', '.join(ASSET_TYPES)}")
    asset = Asset(
        user_id=user.id,
        asset_type=body.asset_type,
        name=body.name.strip(),
        current_value=Decimal(str(body.current_value)),
        valuation_date=body.valuation_date,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return AssetResponse(
        id=asset.id,
        asset_type=asset.asset_type,
        name=asset.name,
        current_value=float(asset.current_value),
        valuation_date=asset.valuation_date,
    )


@router.get("/assets", response_model=list[AssetResponse])
async def list_assets(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Asset).where(Asset.user_id == user.id))
    return [
        AssetResponse(
            id=a.id,
            asset_type=a.asset_type,
            name=a.name,
            current_value=float(a.current_value),
            valuation_date=a.valuation_date,
        )
        for a in result.scalars().all()
    ]
