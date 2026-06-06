from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db import get_async_session, User, Account

router = APIRouter()


class LoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    id: str
    email: str


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Very basic auth for MVP. Look up user by email, create if doesn't exist.
    """
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(email=body.email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        default_acc = Account(user_id=user.id, account_type="cash", name="Cash Wallet")
        session.add(default_acc)
        await session.commit()
        
    return LoginResponse(id=str(user.id), email=str(user.email))


async def get_current_user(
    x_user_email: str | None = Header(None),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """Dependency to extract the user based on the X-User-Email header."""
    # Temporary fallback during development transition
    email = x_user_email or "dev@local"
    
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Auto-create if not exists to mimic MVP ease of use
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        default_acc = Account(user_id=user.id, account_type="cash", name="Cash Wallet")
        session.add(default_acc)
        await session.commit()
        
    return user
