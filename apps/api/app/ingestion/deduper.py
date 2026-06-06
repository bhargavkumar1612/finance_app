"""
Duplicate detection: fingerprint per row, check against stored fingerprints.
Storage: import_fingerprints table (user_id, fingerprint).
"""
import hashlib
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import NormalizedTransaction, NormalizedTransactionRow
from app.db.models import ImportFingerprint, Transaction


def _amount_fingerprint_key(amount) -> str:
    """Stable amount string for fingerprints (avoids -450 vs -450.00 mismatches)."""
    return str(Decimal(str(amount)).quantize(Decimal("0.01")))


def make_fingerprint(date_str: str, amount: str, normalized_merchant: str, account_id: str) -> str:
    raw = f"{date_str}|{_amount_fingerprint_key(amount)}|{(normalized_merchant or '').strip()}|{account_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_fingerprint_upi(upi_txn_id: str, amount: str, date_str: str) -> str:
    raw = f"{upi_txn_id}|{amount}|{date_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fingerprint_for_transaction(
    transaction_date,
    amount,
    merchant: str | None,
    account_id: str,
) -> str:
    return make_fingerprint(
        transaction_date.isoformat() if hasattr(transaction_date, "isoformat") else str(transaction_date),
        str(amount),
        (merchant or "").strip(),
        account_id,
    )


async def _existing_transaction_fingerprints(
    session: AsyncSession,
    user_id: UUID,
    account_id: str,
) -> set[str]:
    """Fingerprints of transactions currently in the ledger for this account."""
    result = await session.execute(
        select(Transaction.transaction_date, Transaction.amount, Transaction.merchant).where(
            Transaction.user_id == user_id,
            Transaction.account_id == UUID(account_id),
        )
    )
    return {
        fingerprint_for_transaction(d, amt, merch, account_id)
        for d, amt, merch in result.all()
    }


async def check_duplicates(
    session: AsyncSession,
    rows: list[NormalizedTransaction],
    user_id: UUID,
    account_id: str,
) -> list[NormalizedTransactionRow]:
    """
    Mark rows that already exist in the ledger (same date, amount, merchant, account).
    Returns list of NormalizedTransactionRow with is_duplicate and fingerprint set.
    """
    existing = await _existing_transaction_fingerprints(session, user_id, account_id)
    out: list[NormalizedTransactionRow] = []
    for row in rows:
        date_str = row.date.isoformat()
        merchant = (row.merchant or "").strip()
        fp = make_fingerprint(date_str, row.amount, merchant, account_id)
        is_dup = fp in existing
        out.append(
            NormalizedTransactionRow(
                **row.model_dump(),
                is_duplicate=is_dup,
                fingerprint=fp,
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


async def remove_fingerprints(
    session: AsyncSession,
    user_id: UUID,
    fingerprints: list[str],
) -> None:
    if not fingerprints:
        return
    await session.execute(
        delete(ImportFingerprint).where(
            ImportFingerprint.user_id == user_id,
            ImportFingerprint.fingerprint.in_(fingerprints),
        )
    )


async def clear_import_fingerprints(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(delete(ImportFingerprint).where(ImportFingerprint.user_id == user_id))
