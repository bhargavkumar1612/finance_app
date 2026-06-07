"""Financial persona v1 — rules only (Slice 1). No DB, no LLM."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account
from app.services.account_types import HOLDINGS_TYPES
from app.services.mf_investment_mode import is_sip_account
from app.services.spending import compute_period_spending

SUBSCRIPTION_CATEGORIES = frozenset({
    "subscription", "subscriptions", "entertainment", "streaming", "ott",
})
SKEW_THRESHOLD_PCT = 35.0


async def derive_category_skew(session: AsyncSession, user_id: UUID) -> dict:
    """Rules-only spending personality from last 3 months of ledger spending."""
    end = date.today()
    start = end - timedelta(days=90)
    stats = await compute_period_spending(session, user_id, start, end)
    by_cat = stats.get("by_category", {})
    total = sum(by_cat.values())
    if total <= 0:
        return {"top_category": None, "top_category_pct": 0.0, "subscription_heavy": False}

    top_cat, top_amt = max(by_cat.items(), key=lambda x: x[1])
    top_pct = (top_amt / total) * 100
    subscription_amt = sum(
        amt for cat, amt in by_cat.items()
        if any(kw in (cat or "").lower() for kw in SUBSCRIPTION_CATEGORIES)
    )
    subscription_heavy = (subscription_amt / total) * 100 >= 20.0

    return {
        "top_category": top_cat,
        "top_category_pct": round(top_pct, 1),
        "subscription_heavy": subscription_heavy,
    }


def apply_persona_filters(
    entries: list[dict],
    physical: list[dict],
    accounts: list[Account],
    category_skew: dict | None = None,
) -> dict:
    """
    Derive hide_sections and prioritize_drilldowns from account mix + spending skew.
    Slice 1: rules only — see ADR 002 for full persona in Slice 2.
    """
    hide_sections: list[str] = []
    prioritize: list[str] = []
    traits: list[str] = []

    holdings = [e for e in entries if e["type"] in HOLDINGS_TYPES]
    has_pnl = any(e.get("pnl_percent") is not None for e in holdings)
    has_sip = any(is_sip_account(a) for a in accounts)
    skew = category_skew or {}

    if not has_pnl:
        hide_sections.append("pnl")
    if not physical:
        hide_sections.append("physical_assets")
    if not holdings:
        hide_sections.append("pie")
        prioritize.append("create_account")

    if has_sip:
        prioritize.append("sip_status_query")
        traits.append("sip_regular")
    elif holdings:
        traits.append("lump_sum_investor")

    if len(holdings) >= 2:
        prioritize.append("investment_allocation")
    if has_pnl:
        prioritize.append("portfolio_pnl_drilldown")

    top_pct = skew.get("top_category_pct") or 0
    if top_pct >= SKEW_THRESHOLD_PCT:
        traits.append("category_skew")
        prioritize.append("spending_analysis")
    if skew.get("subscription_heavy"):
        traits.append("subscription_heavy")
        prioritize.append("list_recurring_bills")

    return {
        "hide_sections": hide_sections,
        "prioritize_drilldowns": prioritize,
        "traits": traits,
        "top_category": skew.get("top_category"),
        "top_category_pct": skew.get("top_category_pct"),
    }
