#!/usr/bin/env python
"""Set a temporary password for legacy users that have no password yet.

Migration 013 backfills this for fresh cutovers, but a DB already migrated
before that step (or any user left without a password) can be fixed with this.
Only touches users where password_hash IS NULL — never overwrites a real one.

Usage (inside the api container):
    docker compose run --rm -w /app/apps/api -e PYTHONPATH=/app/apps/api \\
        api python -m scripts.backfill_legacy_passwords            # Password@123
    ... api python -m scripts.backfill_legacy_passwords 'Other@123'
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select, update

from app.core import security
from app.db import User, async_session_maker

DEFAULT_PASSWORD = "Password@123"


async def backfill(password: str) -> int:
    err = security.validate_password_strength(password)
    if err:
        raise SystemExit(f"Refusing weak password: {err}")
    hashed = security.hash_password(password)
    async with async_session_maker() as session:
        ids = (
            await session.execute(select(User.id).where(User.password_hash.is_(None)))
        ).scalars().all()
        if ids:
            await session.execute(
                update(User).where(User.password_hash.is_(None)).values(password_hash=hashed)
            )
            await session.commit()
        return len(ids)


def main() -> None:
    password = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_PASSWORD
    count = asyncio.run(backfill(password))
    print(f"Set temporary password for {count} legacy user(s).")


if __name__ == "__main__":
    main()
