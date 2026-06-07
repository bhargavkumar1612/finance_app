#!/usr/bin/env python
"""One-time super admin bootstrap (ADR 003 — not self-registration).

Non-interactive: reads credentials from argv or environment so it can run in
CI / e2e setup as well as locally.

Usage:
    python -m scripts.create_super_admin <username> <password>
    SUPER_ADMIN_USERNAME=root SUPER_ADMIN_PASSWORD=... python -m scripts.create_super_admin

Idempotent: if the username already exists it is promoted to super_admin /
approved and its password is reset to the supplied value.

Run inside the api container, e.g.:
    docker compose run --rm -w /app/apps/api -e PYTHONPATH=/app/apps/api \\
        api python -m scripts.create_super_admin root 'change-me-please'
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from app.core import security
from app.db import User, async_session_maker
from app.services.user_provisioning import seed_default_cash_account


async def create_super_admin(username: str, password: str) -> str:
    err = security.validate_password_strength(password)
    if err:
        raise SystemExit(f"Refusing weak password: {err}")

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        action = "updated"
        if user is None:
            user = User(username=username)
            session.add(user)
            action = "created"

        user.password_hash = security.hash_password(password)
        user.role = security.ROLE_SUPER_ADMIN
        user.status = security.STATUS_APPROVED
        user.rejected_at = None
        await session.flush()
        await seed_default_cash_account(session, user.id)
        await session.commit()
        return f"Super admin '{username}' {action} (id={user.id})."


def main() -> None:
    if len(sys.argv) >= 3:
        username, password = sys.argv[1], sys.argv[2]
    else:
        username = os.getenv("SUPER_ADMIN_USERNAME", "")
        password = os.getenv("SUPER_ADMIN_PASSWORD", "")
    if not username or not password:
        raise SystemExit(
            "Provide credentials via argv (<username> <password>) or "
            "SUPER_ADMIN_USERNAME / SUPER_ADMIN_PASSWORD env vars."
        )
    message = asyncio.run(create_super_admin(username, password))
    print(message)


if __name__ == "__main__":
    main()
