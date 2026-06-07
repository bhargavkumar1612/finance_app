from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, RecurringBill, Transaction
from app.services.account_types import LOAN_TYPES
from app.services.mf_investment_mode import is_sip_account
from app.services.mf_sip_schedule import compute_sip_schedule
from app.services.transaction_semantics import NwImpact


async def check_missing_data(session: AsyncSession, user_id: UUID) -> list[str]:
    """Rule-based hints for missing income, rent spending, EMI logs, or overdue SIPs."""
    sip_hints: list[str] = []
    general_hints: list[str] = []
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    income_q = select(Transaction.id).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_of_month,
        Transaction.nw_impact.in_((NwImpact.income.value, NwImpact.refund.value)),
    ).limit(1)
    if not (await session.execute(income_q)).scalar_one_or_none():
        general_hints.append("Add this month's salary")

    rent_q = select(Transaction.id).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_of_month,
        Transaction.nw_impact == NwImpact.spending.value,
        (
            Transaction.category.ilike("%rent%")
            | Transaction.category.ilike("%housing%")
            | Transaction.raw_description.ilike("%rent%")
        ),
    ).limit(1)
    if not (await session.execute(rent_q)).scalar_one_or_none():
        general_hints.append("Log your rent payment")

    loan_q = select(Account.name).where(
        Account.user_id == user_id,
        Account.account_type.in_(tuple(LOAN_TYPES)),
        Account.emi_amount.isnot(None),
        Account.emi_amount > 0,
    )
    for loan_name in (await session.execute(loan_q)).scalars().all():
        emi_q = select(Transaction.id).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_of_month,
            Transaction.nw_impact == NwImpact.liability_payment.value,
            (
                Transaction.merchant.ilike(f"%{loan_name}%")
                | Transaction.raw_description.ilike(f"%{loan_name}%")
            ),
        ).limit(1)
        if not (await session.execute(emi_q)).scalar_one_or_none():
            general_hints.append(f"Log EMI for {loan_name}")

    sip_accounts_q = select(Account).where(
        Account.user_id == user_id,
        Account.account_type == "mutual_fund",
    )
    sip_accounts = (await session.execute(sip_accounts_q)).scalars().all()
    for acc in sip_accounts:
        if not is_sip_account(acc) or not acc.due_day:
            continue
        if today.day < acc.due_day:
            continue
        schedule = await compute_sip_schedule(session, acc, user_id)
        paid_this_month = False
        for p in schedule.get("payment_history", []):
            pd = date.fromisoformat(p["date"])
            if pd.year == today.year and pd.month == today.month:
                paid_this_month = True
                break
        if not paid_this_month:
            sip_hints.append(f"Log SIP payment for {acc.name}")

    # Overdue SIPs first — they are time-sensitive vs generic rent/salary prompts.
    return (sip_hints + general_hints)[:5]
