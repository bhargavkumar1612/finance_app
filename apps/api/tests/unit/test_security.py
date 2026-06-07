"""Unit tests for auth primitives (ADR 003): password hashing, opaque tokens,
and the 24h rejection cool-off rule."""
from datetime import datetime, timedelta, timezone

from app.core import security


def test_password_hash_roundtrip():
    h = security.hash_password("hunter2-strong")
    assert h != "hunter2-strong"
    assert security.verify_password("hunter2-strong", h) is True
    assert security.verify_password("wrong-password", h) is False


def test_verify_password_handles_missing_hash():
    assert security.verify_password("anything", None) is False
    assert security.verify_password("anything", "") is False


def test_password_hash_is_salted_unique():
    a = security.hash_password("same-password-x")
    b = security.hash_password("same-password-x")
    assert a != b  # distinct salts
    assert security.verify_password("same-password-x", a)
    assert security.verify_password("same-password-x", b)


def test_validate_password_strength():
    assert security.validate_password_strength("short") is not None  # < 8
    assert security.validate_password_strength("longenough") is None
    # bcrypt 72-byte cap
    assert security.validate_password_strength("a" * 73) is not None
    assert security.validate_password_strength("a" * 72) is None


def test_token_generation_and_hash():
    t1 = security.generate_token()
    t2 = security.generate_token()
    assert t1 != t2
    assert len(t1) > 20
    # hash is deterministic and not the secret
    assert security.hash_token(t1) == security.hash_token(t1)
    assert security.hash_token(t1) != t1
    assert security.hash_token(t1) != security.hash_token(t2)


def test_token_expiry_is_ttl_days_out():
    issued = datetime(2026, 1, 1, tzinfo=timezone.utc)
    exp = security.token_expiry(issued)
    assert exp == issued + timedelta(days=security.TOKEN_TTL_DAYS)


def test_cooloff_none_when_never_rejected():
    assert security.is_in_cooloff(None) is False


def test_cooloff_active_within_24h():
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    rejected = now - timedelta(hours=1)
    assert security.is_in_cooloff(rejected, now=now) is True
    assert security.cooloff_remaining(rejected, now=now) == timedelta(hours=23)


def test_cooloff_expired_after_24h():
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    rejected = now - timedelta(hours=24, minutes=1)
    assert security.is_in_cooloff(rejected, now=now) is False
    assert security.cooloff_remaining(rejected, now=now) == timedelta(0)


def test_cooloff_handles_naive_rejected_at():
    """DB timestamps may be naive — treat as UTC."""
    now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
    rejected_naive = datetime(2026, 6, 7, 11, 0)  # naive, 1h ago
    assert security.is_in_cooloff(rejected_naive, now=now) is True
