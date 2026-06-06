"""Compute due recurring bills (rent / EMI style) for user confirmation."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RecurringBill, Transaction


def _due_date_in_month(year: int, month: int, due_day: int) -> date:
    last = monthrange(year, month)[1]
    return date(year, month, min(due_day, last))


def _shift_calendar_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    ny, nm0 = divmod(idx, 12)
    return ny, nm0 + 1


def _monday_of_iso_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def _has_txn_billing_month(
    session: AsyncSession,
    user_id: UUID,
    bill_id: UUID,
    year: int,
    month: int,
) -> bool:
    q = await session.execute(
        select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.recurring_bill_id == bill_id,
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        ).limit(1)
    )
    return q.scalar_one_or_none() is not None


async def _has_txn_iso_week(
    session: AsyncSession,
    user_id: UUID,
    bill_id: UUID,
    week_anchor: date,
) -> bool:
    mon = _monday_of_iso_week(week_anchor)
    sun = mon + timedelta(days=6)
    q = await session.execute(
        select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.recurring_bill_id == bill_id,
            Transaction.transaction_date >= mon,
            Transaction.transaction_date <= sun,
        ).limit(1)
    )
    return q.scalar_one_or_none() is not None


def _status_for(due: date, today: date) -> str:
    if due < today:
        return "overdue"
    if due == today:
        return "due_today"
    if due <= today + timedelta(days=5):
        return "due_soon"
    return "upcoming"


async def list_due_suggestions(
    session: AsyncSession,
    user_id: UUID,
    *,
    today: date | None = None,
    lookahead_days: int = 7,
    lookback_months: int = 3,
) -> list[dict[str, Any]]:
    """
    Bills that need a ledger entry for an open billing period and fall in the date window.
    Monthly: billing month = calendar month of the due date; skip if a linked txn exists that month.
    Weekly: billing week = Mon–Sun week containing the due weekday; skip if a linked txn exists that week.
    """
    today = today or date.today()
    out: list[dict[str, Any]] = []

    res = await session.execute(
        select(RecurringBill).where(RecurringBill.user_id == user_id, RecurringBill.is_active.is_(True))
    )
    bills = list(res.scalars().all())

    candidates: list[dict[str, Any]] = []

    for bill in bills:
        if bill.frequency == "monthly":
            if bill.due_day is None or not (1 <= bill.due_day <= 31):
                continue
            for delta in range(-lookback_months, 2):
                y, m = _shift_calendar_month(today.year, today.month, delta)
                due = _due_date_in_month(y, m, bill.due_day)
                if due > today + timedelta(days=lookahead_days):
                    continue
                if due < today - timedelta(days=120):
                    continue
                if await _has_txn_billing_month(session, user_id, bill.id, y, m):
                    continue
                st = _status_for(due, today)
                if st == "upcoming" and due > today + timedelta(days=lookahead_days):
                    continue
                candidates.append(
                    {
                        "recurring_bill_id": str(bill.id),
                        "name": bill.name,
                        "amount": str(bill.amount),
                        "suggested_date": due.isoformat(),
                        "status": st,
                        "frequency": bill.frequency,
                        "account_id": str(bill.account_id),
                        "category": bill.category,
                    }
                )

        elif bill.frequency == "weekly":
            if bill.weekday is None or not (0 <= bill.weekday <= 6):
                continue
            mon = _monday_of_iso_week(today)
            for week_off in range(-4, 3):
                wmon = mon + timedelta(days=7 * week_off)
                due = wmon + timedelta(days=bill.weekday)
                if due > today + timedelta(days=lookahead_days):
                    continue
                if due < today - timedelta(days=60):
                    continue
                if await _has_txn_iso_week(session, user_id, bill.id, due):
                    continue
                st = _status_for(due, today)
                if st == "upcoming" and due > today + timedelta(days=lookahead_days):
                    continue
                candidates.append(
                    {
                        "recurring_bill_id": str(bill.id),
                        "name": bill.name,
                        "amount": str(bill.amount),
                        "suggested_date": due.isoformat(),
                        "status": st,
                        "frequency": bill.frequency,
                        "account_id": str(bill.account_id),
                        "category": bill.category,
                    }
                )

    # One row per bill: earliest suggested_date (pay oldest open cycle first)
    by_bill: dict[str, dict[str, Any]] = {}
    for row in sorted(candidates, key=lambda r: r["suggested_date"]):
        bid = row["recurring_bill_id"]
        if bid not in by_bill:
            by_bill[bid] = row
    out = list(by_bill.values())
    out.sort(key=lambda x: (x["status"] != "overdue", x["suggested_date"]))
    return out
