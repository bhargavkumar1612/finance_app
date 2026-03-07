"""
Duplicate detection: fingerprint per row, check against stored fingerprints.
Storage: import_fingerprints table (user_id, fingerprint).
"""
import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import NormalizedTransaction, NormalizedTransactionRow
from app.db.models import ImportFingerprint


def make_fingerprint(date_str: str, amount: str, normalized_merchant: str, account_id: str) -> str:
    raw = f"{date_str}|{amount}|{(normalized_merchant or '').strip()}|{account_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_fingerprint_upi(upi_txn_id: str, amount: str, date_str: str) -> str:
    raw = f"{upi_txn_id}|{amount}|{date_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def check_duplicates(
    session: AsyncSession,
    rows: list[NormalizedTransaction],
    user_id: UUID,
    account_id: str,
) -> list[NormalizedTransactionRow]:
    """
    For each row, compute fingerprint and check if it exists in import_fingerprints.
    Returns list of NormalizedTransactionRow with is_duplicate and fingerprint set.
    """
    result = await session.execute(
        select(ImportFingerprint.fingerprint).where(ImportFingerprint.user_id == user_id)
    )
    existing = {r[0] for r in result}
    out: list[NormalizedTransactionRow] = []
    for row in rows:
        date_str = row.date.isoformat()
        amount_str = str(row.amount)
        merchant = (row.merchant or "").strip()
        fp = make_fingerprint(date_str, amount_str, merchant, account_id)
        is_dup = fp in existing
        out.append(
            NormalizedTransactionRow(
                **row.model_dump(),
                is_duplicate=is_dup,
                fingerprint=fp,
                suggested_category=None,
            )
        )
    return out


async def add_fingerprints(
    session: AsyncSession,
    user_id: UUID,
    fingerprints: list[str],
) -> None:
    """Add fingerprint records; skip any that already exist (caller commits)."""
    result = await session.execute(
        select(ImportFingerprint.fingerprint).where(ImportFingerprint.user_id == user_id)
    )
    existing = {r[0] for r in result}
    for fp in fingerprints:
        if fp not in existing:
            rec = ImportFingerprint(user_id=user_id, fingerprint=fp)
            session.add(rec)
            existing.add(fp)
