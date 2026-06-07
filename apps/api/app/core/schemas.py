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


class NwImpact(str, Enum):
    spending = "spending"
    income = "income"
    transfer = "transfer"
    liability_payment = "liability_payment"
    refund = "refund"
    unknown = "unknown"


# ----- Planner (Phase 1) -----
class Intent(str, Enum):
    add_expense = "add_expense"
    add_income = "add_income"
    import_statement = "import_statement"
    net_worth_query = "net_worth_query"
    spending_analysis = "spending_analysis"
    affordability_check = "affordability_check"
    unknown = "unknown"
    # Phase 4 AI Analytics
    analyze_category_spending = "analyze_category_spending"
    track_subscriptions = "track_subscriptions"  # alias: list_recurring_bills
    list_recurring_bills = "list_recurring_bills"
    analyze_cash_flow = "analyze_cash_flow"
    get_top_expenses = "get_top_expenses"
    budget_vs_actual = "budget_vs_actual"
    project_future_balance = "project_future_balance"
    debt_payoff_planner = "debt_payoff_planner"
    investment_allocation = "investment_allocation"
    vendor_spending_history = "vendor_spending_history"
    unusual_spending_alert = "unusual_spending_alert"
    manage_accounts = "manage_accounts"
    # Slice 1 — Investment + SIP
    portfolio_summary = "portfolio_summary"
    portfolio_pnl_drilldown = "portfolio_pnl_drilldown"
    sip_status_query = "sip_status_query"
    fd_maturity_query = "fd_maturity_query"
    # Slice 2 — Obligations hub
    upcoming_obligations = "upcoming_obligations"
    loan_emi_summary = "loan_emi_summary"
    create_recurring_bill = "create_recurring_bill"
    # Slice 3 — Capture
    record_transfer = "record_transfer"
    explain_transaction = "explain_transaction"
    recategorize_transaction = "recategorize_transaction"
    create_account_guided = "create_account_guided"


class PlannerStep(BaseModel):
    agent: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class PlannerOutput(BaseModel):
    intent: Intent
    steps: list[PlannerStep] = Field(default_factory=list)
    ui_mode: str = "guided_flow"
    message: Optional[str] = None
    trace: Optional["AgentTrace"] = None


class AgentTrace(BaseModel):
    """Routing/debug metadata surfaced to chat UI (not a source of financial truth)."""
    route: str  # keyword | semantic | llm_tool | llm_context | llm_message | fallback
    intent: Optional[str] = None
    tool: Optional[str] = None
    semantic_match: Optional[str] = None
    thinking: Optional[str] = None
    model: Optional[str] = None
    note: Optional[str] = None


PlannerOutput.model_rebuild()


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
    "monthly_summary",       # spending_analysis → category breakdown (legacy)
    "spending_dashboard",    # spending_analysis → pie + monthly bar charts
    "net_worth_breakdown",   # net_worth_query → assets/liabilities/net_worth
    "affordability_result",  # affordability_check → safe_emi, risk_level
    "selection_card",        # multi-option choice (future)
    "message_only",          # fallback / unknown intent
    # Phase 4
    "category_drilldown",
    "subscription_list",
    "recurring_bill_list",
    "cash_flow_summary",
    "top_expenses_list",
    "budget_comparison",
    "future_balance_projection",
    "debt_payoff_plan",
    "investment_pie_chart",
    "vendor_history",
    "anomaly_alert",
    "account_list",
    # Slice 1
    "investment_portfolio_dashboard",
    "investment_pnl_bars",
    "sip_schedule_summary",
    "fd_maturity_summary",
    # Slice 2
    "obligation_list",
    "recurring_bill_confirm",
    # Slice 3
    "import_guide",
    "transaction_detail",
    "account_create_confirm",
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
    suggested_nw_impact: Optional[str] = None


# ----- Import staging (Phase 2) -----
class NormalizedTransactionRow(NormalizedTransaction):
    is_duplicate: bool = False
    fingerprint: Optional[str] = None


# ----- Pending mutation (confirm before write) -----
class PendingMutation(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    preview: dict[str, Any] = Field(default_factory=dict)
