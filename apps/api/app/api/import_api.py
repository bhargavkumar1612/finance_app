"""
Import API: upload file -> normalized rows; confirm -> bulk insert + store fingerprints.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.schemas import NormalizedTransactionRow
from app.db import get_async_session, Account, Transaction, User
from app.ingestion.deduper import (
    add_fingerprints,
    make_fingerprint,
    _existing_transaction_fingerprints,
)
from app.services.import_service import parse_and_normalize
from app.services.transaction_semantics import NwImpact, classify_transaction

router = APIRouter()


class ImportConfirmRow(BaseModel):
    amount: float
    date: str  # YYYY-MM-DD
    merchant: str | None = None
    raw_description: str | None = None
    reference: str | None = None
    confidence: float | None = None
    fingerprint: str | None = None
    suggested_category: str | None = None
    suggested_nw_impact: str | None = None
    nw_impact: str | None = None


class ImportConfirmRequest(BaseModel):
    account_id: UUID
    rows: list[ImportConfirmRow] = Field(default_factory=list)


class ImportConfirmResponse(BaseModel):
    inserted: int = 0
    errors: list[str] = Field(default_factory=list)


class ImportResponse(BaseModel):
    rows: list[NormalizedTransactionRow]
    account_id: str


@router.post("/import", response_model=ImportResponse)
async def import_file(
    file: UploadFile = File(...),
    bank_hint: str | None = Form(None),
    account_id: UUID | None = Form(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Upload CSV (or PDF later). Returns normalized rows with is_duplicate and fingerprint."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    aid = account_id
    if aid is None:
        result = await session.execute(select(Account.id).where(Account.user_id == user.id).limit(1))
        row = result.first()
        if not row:
            raise HTTPException(
                status_code=400,
                detail="No account found. Create an account first (e.g. POST /v1/accounts).",
            )
        aid = row[0]
    rows = await parse_and_normalize(
        session, content, file.filename or "", user.id, str(aid), bank_hint=bank_hint
    )
    return ImportResponse(rows=rows, account_id=str(aid))


@router.post("/import/confirm", response_model=ImportConfirmResponse)
async def import_confirm(
    body: ImportConfirmRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Insert selected rows into ledger (source=import) and store fingerprints."""
    result = await session.execute(
        select(Account).where(Account.id == body.account_id, Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or not yours.")
    inserted = 0
    skipped = 0
    errors: list[str] = []
    fingerprints_to_add: list[str] = []
    account_id_str = str(body.account_id)
    existing_fps = await _existing_transaction_fingerprints(session, user.id, account_id_str)
    for r in body.rows:
        try:
            dt = date.fromisoformat(r.date)
            amount = Decimal(str(r.amount))
            fp = r.fingerprint
            if not fp:
                fp = make_fingerprint(
                    r.date, str(r.amount), (r.merchant or "").strip(), account_id_str
                )
            if fp in existing_fps:
                skipped += 1
                continue
            nw = r.nw_impact or r.suggested_nw_impact
            if not nw:
                nw = classify_transaction(
                    amount,
                    category=r.suggested_category,
                    merchant=r.merchant,
                    raw_description=r.raw_description,
                    account_type=account.account_type,
                ).value
            txn = Transaction(
                user_id=user.id,
                account_id=body.account_id,
                amount=amount,
                currency="INR",
                transaction_date=dt,
                merchant=r.merchant,
                category=r.suggested_category,
                raw_description=r.raw_description,
                source="import",
                confidence=Decimal(str(r.confidence)) if r.confidence is not None else None,
                nw_impact=nw,
            )
            session.add(txn)
            await session.flush()
            fingerprints_to_add.append(fp)
            existing_fps.add(fp)
            inserted += 1
        except Exception as e:
            errors.append(f"Row {r.date} {r.amount}: {e}")
    if skipped:
        errors.insert(
            0,
            f"Skipped {skipped} row(s) already in your ledger (duplicate).",
        )
    if fingerprints_to_add:
        await add_fingerprints(session, user.id, list(dict.fromkeys(fingerprints_to_add)))
    await session.commit()
    return ImportConfirmResponse(inserted=inserted, errors=errors)
