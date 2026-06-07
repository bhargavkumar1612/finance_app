"""Super-admin user maintenance helpers.

`delete_user_cascade` is the single source of truth for hard-deleting a user and
all their data (FKs have no DB-level cascade, so order matters). Used by the
admin DELETE endpoint and the purge_users script.
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import (
    Account,
    Asset,
    AuthToken,
    ChatMessage,
    ChatSession,
    ImportFingerprint,
    PasswordResetRequest,
    RecurringBill,
    Transaction,
    User,
)
from app.db.models import UserFinancialPersona


async def delete_user_cascade(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Delete a user and every row they own, in dependency order. Does not
    commit — the caller owns the transaction."""
    uid = user_id
    # chat messages (FK -> chat_sessions, which has no DB cascade)
    await session.execute(
        delete(ChatMessage).where(
            ChatMessage.session_id.in_(select(ChatSession.id).where(ChatSession.user_id == uid))
        )
    )
    await session.execute(delete(ChatSession).where(ChatSession.user_id == uid))
    # transactions reference accounts + recurring_bills — delete before both
    await session.execute(delete(Transaction).where(Transaction.user_id == uid))
    await session.execute(delete(ImportFingerprint).where(ImportFingerprint.user_id == uid))
    await session.execute(delete(RecurringBill).where(RecurringBill.user_id == uid))
    await session.execute(delete(Asset).where(Asset.user_id == uid))
    await session.execute(delete(UserFinancialPersona).where(UserFinancialPersona.user_id == uid))
    # break self-referential parent link before deleting accounts
    await session.execute(
        update(Account).where(Account.user_id == uid).values(parent_account_id=None)
    )
    await session.execute(delete(Account).where(Account.user_id == uid))
    # this user may have resolved others' reset requests — null those FKs first
    await session.execute(
        update(PasswordResetRequest)
        .where(PasswordResetRequest.resolved_by == uid)
        .values(resolved_by=None)
    )
    await session.execute(delete(PasswordResetRequest).where(PasswordResetRequest.user_id == uid))
    await session.execute(delete(AuthToken).where(AuthToken.user_id == uid))
    await session.execute(delete(User).where(User.id == uid))
