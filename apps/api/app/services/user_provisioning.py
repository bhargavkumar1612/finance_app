"""Shared user-provisioning helpers.

Seeding the default Cash account is the historical first-login behavior; it now
runs when a super admin approves a signup (and on super-admin bootstrap).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Account


async def seed_default_cash_account(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """Create a default 'Cash Wallet' account for the user if they have none.

    Idempotent: returns True if an account was created, False if one already
    existed. Does not commit — the caller owns the transaction.
    """
    existing = await session.execute(
        select(Account.id).where(Account.user_id == user_id).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return False
    session.add(Account(user_id=user_id, account_type="cash", name="Cash Wallet"))
    return True
