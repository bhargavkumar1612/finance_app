"""
Import service: parse file -> normalize -> dedupe -> return NormalizedTransactionRow list.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import NormalizedTransactionRow
from app.db.models import Account
from app.ingestion.csv_router import parse_csv_file
from app.ingestion.deduper import check_duplicates
from app.ingestion.normalizer import normalize_row
from app.ingestion.pdf_router import parse_pdf


async def parse_and_normalize(
    session: AsyncSession,
    content: bytes,
    filename: str,
    user_id: UUID,
    account_id: str,
    bank_hint: str | None = None,
) -> list[NormalizedTransactionRow]:
    """
    Parse file (CSV or PDF by extension), normalize each row, check duplicates.
    Returns list of NormalizedTransactionRow with is_duplicate and fingerprint set.
    """
    ext = (filename or "").lower().split(".")[-1] if filename else ""
    if ext == "pdf":
        raw_rows = parse_pdf(content, filename=filename, bank_hint=bank_hint)
    elif ext in ("csv", "txt"):
        raw_rows = parse_csv_file(content, filename=filename, bank_hint=bank_hint)
    else:
        return []
    acct_result = await session.execute(
        select(Account.account_type).where(Account.id == UUID(account_id))
    )
    account_type_row = acct_result.first()
    account_type = account_type_row[0] if account_type_row else None
    normalized = [normalize_row(r, account_type=account_type) for r in raw_rows]
    normalized = [n for n in normalized if n.amount != 0]
    rows_with_dup = await check_duplicates(session, normalized, user_id, account_id)
    return rows_with_dup
