"""Auth API — username/password + super-admin-gated access (ADR 003, Round 9).

Replaces the legacy email-only MVP auth. No X-User-Email trust, no dev@local
auto-create. Sessions are DB-backed bearer tokens so logout and disable revoke
access immediately.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.db import AuthToken, PasswordResetRequest, User, get_async_session

router = APIRouter()


# --- Schemas ------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str


class ForgotPasswordRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    status: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class MessageResponse(BaseModel):
    message: str


def _user_out(user: User) -> UserOut:
    return UserOut(id=str(user.id), username=user.username, role=user.role, status=user.status)


# --- Token helpers ------------------------------------------------------
async def _issue_token(session: AsyncSession, user: User) -> str:
    raw = security.generate_token()
    token = AuthToken(
        user_id=user.id,
        token_hash=security.hash_token(raw),
        expires_at=datetime.utcnow() + timedelta(days=security.TOKEN_TTL_DAYS),
    )
    session.add(token)
    await session.commit()
    return raw


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


# --- Endpoints ----------------------------------------------------------
@router.post("/auth/register", response_model=MessageResponse)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a pending account. Cannot log in until a super admin approves."""
    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=422, detail="Username is required.")

    pw_err = security.validate_password_strength(body.password)
    if pw_err:
        raise HTTPException(status_code=422, detail=pw_err)

    result = await session.execute(select(User).where(User.username == username))
    existing = result.scalar_one_or_none()
    if existing is not None:
        # Rejected username inside the 24h cool-off may not re-register.
        if existing.status == security.STATUS_REJECTED and security.is_in_cooloff(existing.rejected_at):
            raise HTTPException(
                status_code=409,
                detail="This username was recently rejected. Try again later or contact the administrator.",
            )
        raise HTTPException(status_code=409, detail="That username is taken.")

    user = User(
        username=username,
        password_hash=security.hash_password(body.password),
        role=security.ROLE_USER,
        status=security.STATUS_PENDING,
    )
    session.add(user)
    await session.commit()
    return MessageResponse(
        message="Registration received. Your account is pending administrator approval."
    )


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Approved users with a valid password receive a bearer token."""
    result = await session.execute(select(User).where(User.username == body.username.strip()))
    user = result.scalar_one_or_none()

    # Generic credential failure (no account enumeration) when no user or bad password.
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Password is correct — now surface clear, status-specific messages.
    if user.status == security.STATUS_PENDING:
        raise HTTPException(status_code=403, detail="Your account is pending administrator approval.")
    if user.status == security.STATUS_REJECTED:
        raise HTTPException(status_code=403, detail="Your registration was not approved.")
    if user.status == security.STATUS_DISABLED:
        raise HTTPException(status_code=403, detail="Your account has been disabled. Contact the administrator.")
    if user.status != security.STATUS_APPROVED:
        raise HTTPException(status_code=403, detail="Your account cannot sign in.")

    token = await _issue_token(session, user)
    return LoginResponse(token=token, user=_user_out(user))


@router.post("/auth/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Approved user requests a manual password reset (super admin queue)."""
    generic = MessageResponse(
        message="If that account exists and is approved, a reset request has been sent to the administrator."
    )
    result = await session.execute(select(User).where(User.username == body.username.strip()))
    user = result.scalar_one_or_none()
    if user is None or user.status != security.STATUS_APPROVED:
        return generic

    # Avoid piling up duplicate open requests for the same user.
    existing = await session.execute(
        select(PasswordResetRequest).where(
            PasswordResetRequest.user_id == user.id,
            PasswordResetRequest.status == security.RESET_OPEN,
        )
    )
    if existing.scalar_one_or_none() is None:
        session.add(PasswordResetRequest(user_id=user.id, status=security.RESET_OPEN))
        await session.commit()
    return generic


@router.post("/auth/logout", response_model=MessageResponse)
async def logout(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_async_session),
):
    """Invalidate the presented bearer token (idempotent)."""
    raw = _bearer_token(authorization)
    if raw:
        result = await session.execute(
            select(AuthToken).where(AuthToken.token_hash == security.hash_token(raw))
        )
        token = result.scalar_one_or_none()
        if token is not None:
            await session.delete(token)
            await session.commit()
    return MessageResponse(message="Logged out.")


# --- Current-user dependency -------------------------------------------
async def get_current_user(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Resolve the authenticated, approved user from a bearer token.

    Re-checks status on every request so disabling a user revokes access
    immediately (not just at next login).
    """
    raw = _bearer_token(authorization)
    if not raw:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    result = await session.execute(
        select(AuthToken).where(AuthToken.token_hash == security.hash_token(raw))
    )
    token = result.scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    if token.expires_at < datetime.utcnow():
        await session.delete(token)
        await session.commit()
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    user = await session.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid session.")
    if user.status != security.STATUS_APPROVED:
        raise HTTPException(status_code=403, detail="Your account is not active.")
    return user


async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Guard for /v1/admin/* — approved super_admin only."""
    if current_user.role != security.ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return current_user


@router.get("/auth/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return _user_out(current_user)
