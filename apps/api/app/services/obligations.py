"""Upcoming obligations hub — SIPs, loan EMIs, recurring bills, credit cards."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, RecurringBill
from app.services.account_balances import liability_outstanding
from app.services.account_types import LOAN_TYPES
from app.services.commitments import monthly_commitments_breakdown
from app.services.loan_schedule import compute_loan_schedule
from app.services.portfolio_summary import _next_due_date, compute_sip_status


def _bill_next_due(bill: RecurringBill, today: date) -> str | None:
    if bill.frequency == "monthly" and bill.due_day:
        return _next_due_date(bill.due_day, today, False).isoformat()
    if bill.frequency == "weekly" and bill.weekday is not None:
        days_ahead = (bill.weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat()
    return None


async def compute_loan_emi_summary(session: AsyncSession, user_id: UUID) -> dict:
    result = await session.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type.in_(tuple(LOAN_TYPES)),
        )
    )
    loans: list[dict] = []
    total_emi = 0.0
    today = date.today()
    for acc in result.scalars().all():
        emi = float(acc.emi_amount or 0)
        if emi <= 0:
            continue
        schedule = await compute_loan_schedule(session, acc, user_id)
        next_due = None
        if acc.due_day:
            next_due = _next_due_date(acc.due_day, today, False).isoformat()
        loans.append({
            "account_id": str(acc.id),
            "name": acc.name,
            "loan_type": acc.loan_type,
            "emi_amount": emi,
            "due_day": acc.due_day,
            "next_due_on": next_due,
            "outstanding": schedule.get("outstanding"),
            "emi_paid_count": schedule.get("emi_paid_count"),
            "emi_pending_count": schedule.get("emi_pending_count"),
        })
        total_emi += emi
    loans.sort(key=lambda x: x.get("next_due_on") or "9999")
    return {
        "loans": loans,
        "total_monthly_emi": round(total_emi, 2),
        "message": (
            f"{len(loans)} loan(s) · ₹{total_emi:,.0f}/month total EMI."
            if loans
            else "No loan accounts with EMI set up."
        ),
    }


async def compute_upcoming_obligations(session: AsyncSession, user_id: UUID) -> dict:
    today = date.today()
    sip_data = await compute_sip_status(session, user_id)
    sips = [
        {
            **s,
            "next_due_on": s.get("next_expected_on"),
            "amount": s.get("emi_amount"),
        }
        for s in sip_data.get("sips", [])
    ]
    sips.sort(key=lambda x: x.get("next_due_on") or "9999")

    loan_summary = await compute_loan_emi_summary(session, user_id)
    loan_emis = loan_summary["loans"]

    bill_result = await session.execute(
        select(RecurringBill).where(
            RecurringBill.user_id == user_id,
            RecurringBill.is_active.is_(True),
        )
    )
    recurring_bills: list[dict] = []
    for bill in bill_result.scalars().all():
        recurring_bills.append({
            "id": str(bill.id),
            "name": bill.name,
            "amount": abs(float(bill.amount)),
            "frequency": bill.frequency,
            "due_day": bill.due_day,
            "category": bill.category,
            "next_due_on": _bill_next_due(bill, today),
        })
    recurring_bills.sort(key=lambda x: x.get("next_due_on") or "9999")

    cc_result = await session.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == "credit_card",
        )
    )
    credit_cards: list[dict] = []
    for acc in cc_result.scalars().all():
        outstanding = await liability_outstanding(session, acc.id, user_id)
        next_due = None
        if acc.due_day:
            next_due = _next_due_date(acc.due_day, today, False).isoformat()
        credit_cards.append({
            "account_id": str(acc.id),
            "name": acc.name,
            "due_day": acc.due_day,
            "outstanding": float(outstanding),
            "next_due_on": next_due,
        })
    credit_cards.sort(key=lambda x: x.get("next_due_on") or "9999")

    commitments = await monthly_commitments_breakdown(session, user_id)
    section_count = sum(
        1 for section in (sips, loan_emis, recurring_bills, credit_cards) if section
    )
    return {
        "sections": {
            "sips": sips,
            "loan_emis": loan_emis,
            "recurring_bills": recurring_bills,
            "credit_cards": credit_cards,
        },
        "commitments": commitments,
        "total_monthly_commitments": commitments["total_commitments"],
        "message": (
            f"Upcoming obligations across {section_count} section(s) · "
            f"₹{commitments['total_commitments']:,.0f}/month committed."
            if section_count
            else "No obligations tracked yet. Add loans, SIPs, or recurring bills."
        ),
    }
