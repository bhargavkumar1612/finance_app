"""
Core data contracts — strict schemas between layers.
Agents never return free-form chaos when UI is guided.
"""
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ----- Planner (Phase 1) -----
class Intent(str, Enum):
    add_expense = "add_expense"
    import_statement = "import_statement"
    net_worth_query = "net_worth_query"
    spending_analysis = "spending_analysis"
    affordability_check = "affordability_check"
    unknown = "unknown"
    # Phase 4 AI Analytics
    analyze_category_spending = "analyze_category_spending"
    track_subscriptions = "track_subscriptions"
    analyze_cash_flow = "analyze_cash_flow"
    get_top_expenses = "get_top_expenses"
    budget_vs_actual = "budget_vs_actual"
    project_future_balance = "project_future_balance"
    debt_payoff_planner = "debt_payoff_planner"
    investment_allocation = "investment_allocation"
    vendor_spending_history = "vendor_spending_history"
    unusual_spending_alert = "unusual_spending_alert"


class PlannerStep(BaseModel):
    agent: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    intent: Intent
    steps: list[PlannerStep] = Field(default_factory=list)
    ui_mode: str = "guided_flow"
    message: Optional[str] = None


# ----- Conversation state (Redis) -----
class ConversationState(BaseModel):
    conversation_id: str = ""
    current_step: str = ""
    filled_slots: dict[str, Any] = Field(default_factory=dict)
    agent_history: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: Optional[str] = None  # ISO datetime string


# ----- Card types (Phase 3) -----
# Canonical ui_type values sent in AgentResponse to drive dynamic card rendering.
CardType = Literal[
    "transaction_confirm",   # add_expense success → show amount/merchant/category
    "monthly_summary",       # spending_analysis → category breakdown
    "net_worth_breakdown",   # net_worth_query → assets/liabilities/net_worth
    "affordability_result",  # affordability_check → safe_emi, risk_level
    "selection_card",        # multi-option choice (future)
    "message_only",          # fallback / unknown intent
    # Phase 4
    "category_drilldown",
    "subscription_list",
    "cash_flow_summary",
    "top_expenses_list",
    "budget_comparison",
    "future_balance_projection",
    "debt_payoff_plan",
    "investment_pie_chart",
    "vendor_history",
    "anomaly_alert",
]


# ----- Agent response (unified shape) -----
class AgentResponse(BaseModel):
    status: str = "success"  # success | error | confirm
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    next_suggested_actions: list[str] = Field(default_factory=list)
    # Phase 3 — Guided UI
    ui_type: Optional[str] = None       # one of CardType literals
    card_payload: Optional[dict[str, Any]] = None  # card-specific data for the frontend


# ----- Normalized transaction (ingestion output) -----
class NormalizedTransaction(BaseModel):
    amount: Decimal
    date: date
    merchant: Optional[str] = None
    raw_description: Optional[str] = None
    reference: Optional[str] = None
    confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    suggested_category: Optional[str] = None


# ----- Import staging (Phase 2) -----
class NormalizedTransactionRow(NormalizedTransaction):
    is_duplicate: bool = False
    fingerprint: Optional[str] = None
