"""Backfill nw_impact on existing transactions."""
import asyncio

from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import Account, Transaction
from app.services.transaction_semantics import classify_transaction


async def backfill() -> int:
    updated = 0
    async with async_session_maker() as session:
        result = await session.execute(select(Transaction))
        txns = list(result.scalars().all())
        acct_cache: dict = {}
        for txn in txns:
            if txn.nw_impact and txn.nw_impact != "unknown":
                continue
            aid = txn.account_id
            if aid not in acct_cache:
                ar = await session.execute(select(Account).where(Account.id == aid))
                acc = ar.scalar_one_or_none()
                acct_cache[aid] = acc.account_type if acc else None
            impact = classify_transaction(
                txn.amount,
                category=txn.category,
                merchant=txn.merchant,
                raw_description=txn.raw_description,
                account_type=acct_cache[aid],
            )
            txn.nw_impact = impact.value
            updated += 1
        await session.commit()
    return updated


if __name__ == "__main__":
    n = asyncio.run(backfill())
    print(f"Backfilled nw_impact on {n} transaction(s).")
