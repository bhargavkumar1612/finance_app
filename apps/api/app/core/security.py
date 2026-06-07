"""Auth primitives for username/password + super admin (Round 9, ADR 003).

Pure helpers — no DB, no FastAPI. Password hashing (bcrypt), opaque session
tokens (DB-backed, stored as sha256 hashes), user role/status constants, and
the 24h rejection cool-off rule. Kept side-effect free so it is unit-testable.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

# --- Roles --------------------------------------------------------------
ROLE_USER = "user"
ROLE_SUPER_ADMIN = "super_admin"
ROLES = {ROLE_USER, ROLE_SUPER_ADMIN}

# --- User status (see DOMAIN_GLOSSARY § Identity and access) ------------
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_DISABLED = "disabled"
STATUSES = {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_DISABLED}

# --- Password reset request status -------------------------------------
RESET_OPEN = "open"
RESET_RESOLVED = "resolved"

# --- Policy knobs -------------------------------------------------------
REJECTION_COOLOFF_HOURS = 24
TOKEN_TTL_DAYS = 30  # ADR 003 defers; sensible default
PASSWORD_MIN_LEN = 8
# bcrypt silently truncates input beyond 72 bytes — reject longer to avoid
# two distinct passwords hashing the same.
PASSWORD_MAX_BYTES = 72


def now_utc() -> datetime:
    """Timezone-aware UTC now (single source for testability)."""
    return datetime.now(timezone.utc)


# --- Passwords ----------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt. Returns a UTF-8 string."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> str | None:
    """Return an error message if the password is unacceptable, else None."""
    if len(password) < PASSWORD_MIN_LEN:
        return f"Password must be at least {PASSWORD_MIN_LEN} characters."
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return f"Password must be at most {PASSWORD_MAX_BYTES} bytes."
    return None


# --- Tokens (opaque bearer; stored hashed) ------------------------------
def generate_token() -> str:
    """A fresh, URL-safe opaque session token. Return value is the secret
    shown to the client once; only its hash is persisted."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """sha256 of a bearer token. The DB stores only this — never the secret."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_expiry(issued_at: datetime | None = None) -> datetime:
    base = issued_at or now_utc()
    return base + timedelta(days=TOKEN_TTL_DAYS)


# --- Rejection cool-off -------------------------------------------------
def is_in_cooloff(rejected_at: datetime | None, *, now: datetime | None = None) -> bool:
    """True if a rejected username is still inside the 24h re-register window.

    `rejected_at` may be naive (DB) or aware; both are treated as UTC.
    """
    if rejected_at is None:
        return False
    current = now or now_utc()
    if rejected_at.tzinfo is None:
        rejected_at = rejected_at.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current - rejected_at < timedelta(hours=REJECTION_COOLOFF_HOURS)


def cooloff_remaining(rejected_at: datetime | None, *, now: datetime | None = None) -> timedelta:
    """How long until the cool-off expires (zero if not in cool-off)."""
    if not is_in_cooloff(rejected_at, now=now):
        return timedelta(0)
    current = now or now_utc()
    if rejected_at.tzinfo is None:  # type: ignore[union-attr]
        rejected_at = rejected_at.replace(tzinfo=timezone.utc)  # type: ignore[union-attr]
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return timedelta(hours=REJECTION_COOLOFF_HOURS) - (current - rejected_at)  # type: ignore[operator]
