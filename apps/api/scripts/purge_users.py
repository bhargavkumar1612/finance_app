#!/usr/bin/env python
"""DESTRUCTIVE: delete all users (and their data) except an explicit keep-list.

Dry-run by default — prints the plan and deletes nothing. Pass --yes to execute.

Usage (inside the api container):
    # preview
    python -m scripts.purge_users bhargav@local csm@finance e2e-admin
    # execute
    python -m scripts.purge_users --yes bhargav@local csm@finance e2e-admin

The keep-list may also come from KEEP_USERS="a,b,c". Refuses to run if any
keep-list username does not exist (guards against typos wiping everything).
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from app.db import User, async_session_maker
from app.services.user_admin import delete_user_cascade


async def purge(keep: set[str], execute: bool) -> None:
    async with async_session_maker() as session:
        rows = (await session.execute(select(User.id, User.username))).all()
    present = {name for _, name in rows}
    missing = keep - present
    if missing:
        raise SystemExit(
            f"Aborting — keep-list usernames not found in DB: {sorted(missing)}. "
            "Fix the names; nothing was deleted."
        )

    to_delete = [(uid, name) for uid, name in rows if name not in keep]
    print(f"Total users: {len(rows)}")
    print(f"Keeping ({len(keep)}): {sorted(keep)}")
    print(f"Will delete: {len(to_delete)} user(s) and all their data.")

    if not execute:
        print("\nDRY RUN — nothing deleted. Re-run with --yes to execute.")
        return

    deleted = 0
    # commit per user so a failure mid-way leaves a consistent, partial result
    for uid, _name in to_delete:
        async with async_session_maker() as session:
            await delete_user_cascade(session, uid)
            await session.commit()
        deleted += 1
        if deleted % 50 == 0:
            print(f"  …deleted {deleted}/{len(to_delete)}")
    print(f"Done. Deleted {deleted} user(s). {len(keep)} remain.")


def main() -> None:
    args = [a for a in sys.argv[1:]]
    execute = "--yes" in args
    args = [a for a in args if a != "--yes"]
    keep: set[str] = set(args)
    if not keep and os.getenv("KEEP_USERS"):
        keep = {s.strip() for s in os.getenv("KEEP_USERS", "").split(",") if s.strip()}
    if not keep:
        raise SystemExit("Provide a keep-list (argv or KEEP_USERS). Refusing to delete all users.")
    asyncio.run(purge(keep, execute))


if __name__ == "__main__":
    main()
