"""Super admin API (ADR 003, Round 9) — /v1/admin/*.

All routes require an approved super_admin (require_super_admin). Powers:
view stats / users, approve/reject/disable/enable signups, hard-delete a user
with full cascade, and resolve password-reset requests offline.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_super_admin
from app.core import security
from app.db import (
    AuthToken,
    PasswordResetRequest,
    User,
    get_async_session,
)
from app.services.user_admin import delete_user_cascade
from app.services.user_provisioning import seed_default_cash_account

router = APIRouter()


# --- Schemas ------------------------------------------------------------
class StatsOut(BaseModel):
    user_count: int
    pending_signups: int
    pending_resets: int


class UserAdminOut(BaseModel):
    id: str
    username: str
    role: str
    status: str
    created_at: datetime | None = None
    rejected_at: datetime | None = None


class UserListOut(BaseModel):
    total: int
    users: list[UserAdminOut]


class PasswordResetOut(BaseModel):
    id: str
    user_id: str
    username: str
    status: str
    requested_at: datetime | None = None


class ResolveResetRequest(BaseModel):
    new_password: str = Field(min_length=security.PASSWORD_MIN_LEN)


class ResolveResetResponse(BaseModel):
    message: str
    username: str
    new_password: str  # shown once for the admin to share offline


def _user_admin_out(u: User) -> UserAdminOut:
    return UserAdminOut(
        id=str(u.id),
        username=u.username,
        role=u.role,
        status=u.status,
        created_at=u.created_at,
        rejected_at=u.rejected_at,
    )


async def _get_user_or_404(session: AsyncSession, user_id: str) -> User:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found.")
    user = await session.get(User, uid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


# --- Read ---------------------------------------------------------------
@router.get("/admin/stats", response_model=StatsOut)
async def admin_stats(
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    user_count = await session.scalar(select(func.count()).select_from(User))
    pending_signups = await session.scalar(
        select(func.count()).select_from(User).where(User.status == security.STATUS_PENDING)
    )
    pending_resets = await session.scalar(
        select(func.count())
        .select_from(PasswordResetRequest)
        .where(PasswordResetRequest.status == security.RESET_OPEN)
    )
    return StatsOut(
        user_count=user_count or 0,
        pending_signups=pending_signups or 0,
        pending_resets=pending_resets or 0,
    )


@router.get("/admin/users", response_model=UserListOut)
async def admin_users(
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    base = select(User)
    count_query = select(func.count()).select_from(User)
    if q and q.strip():
        like = f"%{q.strip()}%"
        base = base.where(User.username.ilike(like))
        count_query = count_query.where(User.username.ilike(like))
    total = await session.scalar(count_query) or 0
    rows = await session.execute(
        base.order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    return UserListOut(total=total, users=[_user_admin_out(u) for u in rows.scalars().all()])


@router.get("/admin/pending-signups", response_model=list[UserAdminOut])
async def admin_pending_signups(
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    rows = await session.execute(
        select(User).where(User.status == security.STATUS_PENDING).order_by(User.created_at.asc())
    )
    return [_user_admin_out(u) for u in rows.scalars().all()]


@router.get("/admin/password-resets", response_model=list[PasswordResetOut])
async def admin_password_resets(
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    rows = await session.execute(
        select(PasswordResetRequest, User.username)
        .join(User, User.id == PasswordResetRequest.user_id)
        .where(PasswordResetRequest.status == security.RESET_OPEN)
        .order_by(PasswordResetRequest.requested_at.asc())
    )
    out: list[PasswordResetOut] = []
    for req, username in rows.all():
        out.append(
            PasswordResetOut(
                id=str(req.id),
                user_id=str(req.user_id),
                username=username,
                status=req.status,
                requested_at=req.requested_at,
            )
        )
    return out


# --- Signup lifecycle ---------------------------------------------------
@router.post("/admin/users/{user_id}/approve", response_model=UserAdminOut)
async def admin_approve(
    user_id: str,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Approve a signup. Clears the rejection cool-off (instant override) and
    seeds the default Cash account, matching first-login behavior."""
    user = await _get_user_or_404(session, user_id)
    user.status = security.STATUS_APPROVED
    user.rejected_at = None
    await session.flush()
    await seed_default_cash_account(session, user.id)
    await session.commit()
    return _user_admin_out(user)


@router.post("/admin/users/{user_id}/reject", response_model=UserAdminOut)
async def admin_reject(
    user_id: str,
    admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    user = await _get_user_or_404(session, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot reject your own account.")
    user.status = security.STATUS_REJECTED
    user.rejected_at = datetime.utcnow()
    await session.commit()
    return _user_admin_out(user)


@router.post("/admin/users/{user_id}/disable", response_model=UserAdminOut)
async def admin_disable(
    user_id: str,
    admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Block login but keep all data. Existing sessions are revoked."""
    user = await _get_user_or_404(session, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")
    user.status = security.STATUS_DISABLED
    # Revoke active sessions so the block takes effect immediately.
    await session.execute(delete(AuthToken).where(AuthToken.user_id == user.id))
    await session.commit()
    return _user_admin_out(user)


@router.post("/admin/users/{user_id}/enable", response_model=UserAdminOut)
async def admin_enable(
    user_id: str,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    user = await _get_user_or_404(session, user_id)
    user.status = security.STATUS_APPROVED
    user.rejected_at = None
    await session.commit()
    return _user_admin_out(user)


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: str,
    admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Hard delete: user + ALL their financial and chat data.

    FKs have no DB-level cascade, so delete in dependency order. The orphan-free
    delete test (test_admin_api) seeds every user-owned table and asserts zero
    leftovers.
    """
    user = await _get_user_or_404(session, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    await delete_user_cascade(session, user.id)
    await session.commit()
    return {"message": "User and all associated data deleted.", "user_id": user_id}


# --- Password reset queue ----------------------------------------------
@router.post("/admin/password-resets/{request_id}/resolve", response_model=ResolveResetResponse)
async def admin_resolve_reset(
    request_id: str,
    body: ResolveResetRequest,
    admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """Set a new password for the requesting user; return it once for offline sharing."""
    pw_err = security.validate_password_strength(body.new_password)
    if pw_err:
        raise HTTPException(status_code=422, detail=pw_err)
    try:
        rid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Reset request not found.")

    req = await session.get(PasswordResetRequest, rid)
    if req is None:
        raise HTTPException(status_code=404, detail="Reset request not found.")
    if req.status != security.RESET_OPEN:
        raise HTTPException(status_code=409, detail="This reset request is already resolved.")

    user = await session.get(User, req.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password_hash = security.hash_password(body.new_password)
    req.status = security.RESET_RESOLVED
    req.resolved_at = datetime.utcnow()
    req.resolved_by = admin.id
    # Force re-login with the new password.
    await session.execute(delete(AuthToken).where(AuthToken.user_id == user.id))
    await session.commit()
    return ResolveResetResponse(
        message="Password reset. Share the new password with the user offline.",
        username=user.username,
        new_password=body.new_password,
    )
