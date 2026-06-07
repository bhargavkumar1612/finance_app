"""
AI Planner: Semantic Routing + Intent Extraction.
Uses Google ADK and Semantic Router.
"""
import json
import os
import re
from datetime import date
from typing import Optional

# Semantic Router for fast intent matching
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import FastEmbedEncoder

# Google ADK for agent orchestration
from google.adk.agents import BaseAgent, LlmAgent
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.llm_client import LLMProvider, get_llm_provider, try_get_env_async_client_and_model
from app.core.schemas import Intent, PlannerOutput, PlannerStep
from app.core.schemas import ConversationState

# 1. Setup Semantic Router
encoder = FastEmbedEncoder(name="BAAI/bge-small-en-v1.5")

# Define base routes mimicking intents
routes = [
    Route(
        name="insert_transaction",
        utterances=[
            "Add 500 for Swiggy",
            "I spent 100 on Uber",
            "Bought coffee for 5",
            "Added expense 50 for lunch"
        ],
    ),
    Route(
        name="compute_net_worth",
        utterances=[
            "What is my net worth?",
            "How much money do I have?",
            "Assets minus liabilities"
        ]
    ),
    Route(
        name="compute_monthly_spend",
        utterances=[
            "Where did I spend my money?",
            "Monthly spending check",
            "How much did I spend last month?",
            "Summarise my last one year spendings and make a pie chart",
            "Show my spending pie chart for the last year",
            "Spending dashboard for the past 12 months",
            "Histogram of my monthly expenses this year",
            "Break down my expenses with a chart",
        ]
    ),
    Route(
        name="list_accounts",
        utterances=[
            "List my accounts",
            "Show my bank accounts",
            "What accounts do I have?",
            "My credit cards and wallets",
        ],
    ),
    Route(
        name="create_account",
        utterances=[
            "Add a new bank account",
            "Create HDFC savings account",
            "Add my credit card",
            "Register a wallet account",
        ],
    ),
    Route(
        name="portfolio_summary",
        utterances=[
            "How are my investments?",
            "How is my portfolio doing?",
            "Show my investment dashboard",
            "MF P and L",
        ],
    ),
    Route(
        name="portfolio_pnl_drilldown",
        utterances=[
            "Show my most profitable investments",
            "Top performers by P and L",
            "Profit and loss on my funds",
        ],
    ),
    Route(
        name="sip_status_query",
        utterances=[
            "Did I pay my SIP this month?",
            "SIP status",
            "Which SIPs are due?",
        ],
    ),
    Route(
        name="fd_maturity_query",
        utterances=[
            "When does my FD mature?",
            "FD maturity date",
            "RD maturity",
        ],
    ),
    Route(
        name="investment_allocation",
        utterances=[
            "Show my investment allocation",
            "Portfolio allocation pie chart",
            "Breakdown by investment type",
        ],
    ),
    Route(
        name="upcoming_obligations",
        utterances=[
            "What's due this month?",
            "Upcoming bills and EMIs",
            "Show my obligations",
            "What do I owe this month?",
        ],
    ),
    Route(
        name="loan_emi_summary",
        utterances=[
            "How much is my total EMI?",
            "Loan EMI summary",
            "EMIs left on my loans",
        ],
    ),
    Route(
        name="compute_affordability",
        utterances=[
            "Can I afford a new loan?",
            "What's my safe EMI?",
            "Affordability check",
        ],
    ),
]

# Provide fallback router logic
try:
    router = SemanticRouter(encoder=encoder, routes=routes)
except Exception as e:
    print(f"Failed to initialize Semantic Router: {e}")
    router = None

_INTENT_MAP = {
    "insert_transaction": Intent.add_expense,
    "insert_income": Intent.add_income,
    "propose_transaction": Intent.add_expense,
    "propose_income": Intent.add_income,
    "compute_net_worth": Intent.net_worth_query,
    "compute_monthly_spend": Intent.spending_analysis,
    "compute_affordability": Intent.affordability_check,
    "import_statement": Intent.import_statement,
    "analyze_category_spending": Intent.analyze_category_spending,
    "track_subscriptions": Intent.track_subscriptions,
    "list_recurring_bills": Intent.list_recurring_bills,
    "analyze_cash_flow": Intent.analyze_cash_flow,
    "get_top_expenses": Intent.get_top_expenses,
    "budget_vs_actual": Intent.budget_vs_actual,
    "project_future_balance": Intent.project_future_balance,
    "debt_payoff_planner": Intent.debt_payoff_planner,
    "investment_allocation": Intent.investment_allocation,
    "portfolio_summary": Intent.portfolio_summary,
    "portfolio_pnl_drilldown": Intent.portfolio_pnl_drilldown,
    "sip_status_query": Intent.sip_status_query,
    "fd_maturity_query": Intent.fd_maturity_query,
    "upcoming_obligations": Intent.upcoming_obligations,
    "loan_emi_summary": Intent.loan_emi_summary,
    "propose_recurring_bill": Intent.create_recurring_bill,
    "insert_recurring_bill": Intent.create_recurring_bill,
    "propose_transfer": Intent.record_transfer,
    "insert_transfer": Intent.record_transfer,
    "propose_account": Intent.create_account_guided,
    "insert_account": Intent.create_account_guided,
    "explain_transaction": Intent.explain_transaction,
    "propose_recategorize": Intent.recategorize_transaction,
    "insert_recategorize": Intent.recategorize_transaction,
    "vendor_spending_history": Intent.vendor_spending_history,
    "unusual_spending_alert": Intent.unusual_spending_alert,
    "create_account": Intent.manage_accounts,
    "list_accounts": Intent.manage_accounts,
    "update_account": Intent.manage_accounts,
    "delete_account": Intent.manage_accounts,
}

TOOLS = [
  {
    "type": "function",
    "function": {
      "name": "insert_transaction",
      "description": "Records a new expense or income transaction based on user input. Use this for 'I spent', 'I bought', 'paid for', or 'added X'.",
      "parameters": {
        "type": "object",
        "properties": {
          "amount": { "type": "number", "description": "The transaction amount (positive for income, negative for expenses)" },
          "merchant": { "type": "string", "description": "The name of the vendor, person, or store (e.g., Swiggy, Amazon, Uber)" },
          "category": { "type": "string", "description": "The category of the expense (e.g., Food, Transport, Shopping)" },
          "transaction_date": { "type": "string", "description": "ISO 8601 date (YYYY-MM-DD). If unspecified, say today's date." },
          "account_id": { "type": "string", "description": "(Optional) UUID of the account used" }
        },
        "required": ["amount", "merchant", "transaction_date"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "compute_net_worth",
      "description": "Calculates the user's total net worth (assets minus liabilities). Use this when the user asks 'what is my net worth?', 'how much money do I have?', 'assets', etc.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "compute_monthly_spend",
      "description": "Calculates total spending with category breakdown and monthly trend. The app renders pie charts, bar charts, and dashboards automatically—always use this tool for spending summaries, pie charts, histograms, or dashboards. Never say you cannot create charts.",
      "parameters": {
        "type": "object",
        "properties": {
          "period": {
            "type": "string",
            "enum": ["this_month", "last_month", "last_12_months", "this_year", "last_year"],
            "description": "Time period: this_month, last_month, last_12_months (past year), this_year, last_year"
          }
        },
        "required": ["period"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "compute_affordability",
      "description": "Calculates if the user can safely afford a new EMI or expense based on their income and debts. Use this for 'can I afford X?', 'safe EMI', 'can I take a loan for Y?'.",
      "parameters": {
        "type": "object",
        "properties": {
          "target_emi": { "type": "number", "description": "The optional target EMI amount they want to check" }
        },
        "required": []
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "create_account",
      "description": "Creates a bank, credit card, online wallet, cash, loan, investment, or EPF account.",
      "parameters": {
        "type": "object",
        "properties": {
          "account_type": {
            "type": "string",
            "enum": ["bank", "credit_card", "wallet", "cash", "loan", "mutual_fund", "fixed_deposit", "recurring_deposit", "stock", "epf"],
            "description": "Type of account"
          },
          "name": { "type": "string", "description": "Display name, e.g. HDFC Savings" },
          "institution": { "type": "string", "description": "Bank or provider name (optional)" },
          "loan_type": {
            "type": "string",
            "enum": ["home", "personal", "vehicle", "education", "other"],
            "description": "Optional loan detail when account_type is loan"
          },
          "loan_type_description": {
            "type": "string",
            "description": "Required when loan_type is other"
          },
          "credit_limit": { "type": "number", "description": "Credit limit for credit_card only" },
          "sanctioned_amount": { "type": "number", "description": "Sanctioned amount for loan accounts" },
          "emi_amount": { "type": "number", "description": "Monthly EMI for loan accounts" },
          "tenure_months": { "type": "integer", "description": "Loan tenure in months" },
          "interest_rate": { "type": "number", "description": "Optional interest rate for loan accounts" },
          "opening_balance": { "type": "number", "description": "Starting balance for bank/cash/holdings accounts (incl. EPF)" },
          "account_number": { "type": "string", "description": "Bank account number (bank only)" },
          "ifsc_code": { "type": "string", "description": "IFSC code (bank only)" },
          "branch": { "type": "string", "description": "Branch name (bank only)" },
          "account_notes": { "type": "string", "description": "Other notes for bank account" },
          "parent_account_id": { "type": "string", "description": "Required for credit_card, loan, liquid investment accounts; optional for online wallet" },
          "currency": { "type": "string", "description": "Currency code, default INR" }
        },
        "required": ["account_type", "name"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "list_accounts",
      "description": "Lists all user accounts with types and transaction counts. Use when user asks to see accounts, cards, or online wallets.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "update_account",
      "description": "Updates an existing account name, type, institution, or credit limit. Requires account_id.",
      "parameters": {
        "type": "object",
        "properties": {
          "account_id": { "type": "string", "description": "UUID of the account" },
          "name": { "type": "string" },
          "account_type": { "type": "string", "enum": ["bank", "credit_card", "wallet", "cash", "loan", "mutual_fund", "fixed_deposit", "recurring_deposit", "stock"] },
          "loan_type": { "type": "string", "enum": ["home", "personal", "vehicle", "education", "other"] },
          "loan_type_description": { "type": "string" },
          "sanctioned_amount": { "type": "number" },
          "emi_amount": { "type": "number" },
          "tenure_months": { "type": "integer" },
          "interest_rate": { "type": "number" },
          "parent_account_id": { "type": "string" },
          "institution": { "type": "string" },
          "credit_limit": { "type": "number" },
          "opening_balance": { "type": "number", "description": "Starting balance for bank/cash/holdings accounts (incl. EPF)" },
          "account_number": { "type": "string" },
          "ifsc_code": { "type": "string" },
          "branch": { "type": "string" },
          "account_notes": { "type": "string" },
          "currency": { "type": "string" }
        },
        "required": ["account_id"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "delete_account",
      "description": "Deletes an account with no transactions. Requires account_id. Fails if account has transactions.",
      "parameters": {
        "type": "object",
        "properties": {
          "account_id": { "type": "string", "description": "UUID of the account to delete" }
        },
        "required": ["account_id"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "portfolio_summary",
      "description": "Investment portfolio dashboard: current value, P&L, liquidity ranking, allocation pie. Use for 'how are my investments', 'portfolio', 'MF performance'.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "portfolio_pnl_drilldown",
      "description": "Top investment performers by P&L percent and rupee amount. Use for 'most profitable funds', 'P&L breakdown'.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "sip_status_query",
      "description": "SIP mutual fund status: last paid, next due, paid this month. Use for 'did I pay SIP', 'SIP due'.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "fd_maturity_query",
      "description": "Fixed deposit and recurring deposit maturity dates. Use for 'when does FD mature', 'RD ending'.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "investment_allocation",
      "description": "Portfolio allocation pie by investment type (MF, FD, stock, EPF). Use for 'investment allocation', 'breakdown by type'.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "upcoming_obligations",
      "description": "Unified obligations hub: SIPs, loan EMIs, recurring bills, credit card due dates. Use for 'what's due', 'upcoming bills'.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "loan_emi_summary",
      "description": "Loan EMI totals and per-loan breakdown. Use for 'total EMI', 'loan EMI summary'.",
      "parameters": { "type": "object", "properties": {}, "required": [] }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "insert_recurring_bill",
      "description": "Create a recurring monthly or weekly bill (rent, subscription). Requires confirm.",
      "parameters": {
        "type": "object",
        "properties": {
          "name": { "type": "string", "description": "Bill name e.g. Netflix, Rent" },
          "amount": { "type": "number", "description": "Monthly amount (positive number)" },
          "frequency": { "type": "string", "enum": ["monthly", "weekly"] },
          "due_day": { "type": "integer", "description": "Day of month 1-31" },
          "category": { "type": "string" },
          "account_id": { "type": "string" }
        },
        "required": ["name", "amount"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "insert_transfer",
      "description": "Record an investment/SIP transfer as dual-leg bank debit + MF credit. Use for 'record SIP', 'transfer to MF', 'fund my SIP'. Never use insert_transaction for SIP funding.",
      "parameters": {
        "type": "object",
        "properties": {
          "amount": { "type": "number", "description": "Transfer amount (positive)" },
          "investment_name": { "type": "string", "description": "MF/SIP account name" },
          "transaction_date": { "type": "string", "description": "ISO date YYYY-MM-DD" }
        },
        "required": ["amount"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "insert_account",
      "description": "Creates any account type with full SIP/investment fields. Use when user says 'add SIP', 'create mutual fund account', 'add EPF', etc. Requires confirm before write.",
      "parameters": {
        "type": "object",
        "properties": {
          "account_type": { "type": "string", "enum": ["bank", "credit_card", "wallet", "cash", "loan", "mutual_fund", "fixed_deposit", "recurring_deposit", "stock", "epf"] },
          "name": { "type": "string" },
          "institution": { "type": "string" },
          "investment_mode": { "type": "string", "enum": ["one_time", "sip"], "description": "mutual_fund only" },
          "emi_amount": { "type": "number", "description": "SIP monthly amount" },
          "due_day": { "type": "integer", "description": "SIP due day 1-31" },
          "start_date": { "type": "string", "description": "SIP/loan start date YYYY-MM-DD" },
          "tenure_months": { "type": "integer" },
          "loan_type": { "type": "string", "enum": ["home", "personal", "vehicle", "education", "other"] },
          "credit_limit": { "type": "number" },
          "opening_balance": { "type": "number" },
          "parent_account_id": { "type": "string" }
        },
        "required": ["account_type", "name"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "explain_transaction",
      "description": "Shows recent transactions for a merchant. Use for 'what is this charge?', 'explain Netflix', 'show me recent Swiggy transactions'.",
      "parameters": {
        "type": "object",
        "properties": {
          "merchant": { "type": "string", "description": "Merchant or description to search" },
          "limit": { "type": "integer", "description": "Max results, default 5" }
        },
        "required": []
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "insert_recategorize",
      "description": "Change the category of a transaction. Use for 'recategorize Netflix to Entertainment', 'change Swiggy to Food'. Requires confirm before write.",
      "parameters": {
        "type": "object",
        "properties": {
          "merchant": { "type": "string", "description": "Merchant name to find the transaction" },
          "new_category": { "type": "string", "description": "New category to assign" },
          "transaction_id": { "type": "string", "description": "Optional exact transaction UUID" }
        },
        "required": ["new_category"]
      }
    }
  }
]

# Client logic
_client = None
_active_model = "deepseek-r1:latest"

def get_client() -> AsyncOpenAI:
    global _client, _active_model
    if _client is None:
        env_client = try_get_env_async_client_and_model()
        if env_client is not None:
            _client, _active_model = env_client
            print(f"Loaded LLM from env: model={_active_model!r}")
            return _client
        try:
            llms_path = os.environ.get("LLMS_CONFIG_PATH", "/app/llms.json")
            with open(llms_path, "r") as f:
                llms = json.load(f)
                active = next((l for l in llms if l.get("ACTIVE")), None)
                if active:
                    print(f"Loaded active LLM config: {active['LLM_PROVIDER']} - {active['LLM_MODEL']}")
                    _active_model = active.get("LLM_MODEL", "deepseek-r1:latest")
                    _client = AsyncOpenAI(
                        base_url=active.get("LLM_BASE_URL"),
                        api_key=active.get("LLM_API_KEY", "ollama"),
                    )
                else:
                    raise ValueError("No active LLM found in llms.json")
        except Exception as e:
            print(f"Error loading llms.json, falling back to local Ollama: {e}")
            _client = AsyncOpenAI(
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/v1",
                api_key="ollama",
            )
            _active_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    return _client

def _detect_spending_period(message: str) -> str | None:
    """Keyword fallback so chart/year spending requests reach the ledger tool."""
    lower = message.lower()
    spend_kw = any(
        w in lower
        for w in (
            "spend", "spending", "spent", "expense", "expenses",
            "breakdown", "budget", "where did i",
        )
    )
    chart_kw = any(
        w in lower
        for w in ("pie", "chart", "histogram", "dashboard", "graph", "visual", "plot")
    )
    if not spend_kw and not chart_kw:
        return None
    if any(w in lower for w in ("last year", "past year", "one year", "1 year", "12 month", "twelve month", "annual")):
        return "last_12_months"
    if "this year" in lower or "year to date" in lower:
        return "this_year"
    if chart_kw and not any(w in lower for w in ("this month", "last month")):
        return "last_12_months"
    if "last month" in lower:
        return "last_month"
    if "this month" in lower:
        return "this_month"
    return "last_12_months" if chart_kw else "this_month"


def _detect_add_expense(message: str) -> PlannerOutput | None:
    """Keyword fallback when semantic router / LLM are unavailable."""
    lower = message.lower()
    if not any(
        w in lower
        for w in ("add ", "spent", "paid for", "paid ", "bought ", "i paid", "expense of")
    ):
        return None
    amount_match = re.search(r"(\d+(?:\.\d+)?)", message)
    if not amount_match:
        return None
    amount = float(amount_match.group(1))
    merchant = None
    for_match = re.search(r"\bfor\s+(.+)$", message, re.I)
    if for_match:
        merchant = for_match.group(1).strip().rstrip(".")
    return PlannerOutput(
        intent=Intent.add_expense,
        steps=[
            PlannerStep(
                agent="ledger",
                action="insert_transaction",
                params={"amount": amount, "merchant": merchant},
            )
        ],
        ui_mode="guided_flow",
    )


def _detect_net_worth(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(w in lower for w in ("net worth", "how much money", "total assets", "what am i worth")):
        return PlannerOutput(
            intent=Intent.net_worth_query,
            steps=[PlannerStep(agent="ledger", action="compute_net_worth", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_portfolio_summary(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in (
            "how are my investments",
            "my investments",
            "investment dashboard",
            "portfolio summary",
            "how is my portfolio",
            "how are my mfs",
            "mf p&l",
            "mf pnl",
            "mutual fund performance",
        )
    ) or ("portfolio" in lower and "invest" in lower) or ("mf" in lower and any(w in lower for w in ("doing", "performance", "p&l", "pnl"))):
        return PlannerOutput(
            intent=Intent.portfolio_summary,
            steps=[PlannerStep(agent="ledger", action="portfolio_summary", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_investment_allocation(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in (
            "investment allocation",
            "allocation pie",
            "portfolio allocation",
            "show allocation",
            "breakdown by type",
        )
    ) or ("allocation" in lower and "invest" in lower):
        return PlannerOutput(
            intent=Intent.investment_allocation,
            steps=[PlannerStep(agent="ledger", action="investment_allocation", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_portfolio_pnl(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in (
            "p&l",
            "pnl",
            "profit and loss",
            "most profitable",
            "top performer",
            "best investment",
            "show pnl",
        )
    ):
        return PlannerOutput(
            intent=Intent.portfolio_pnl_drilldown,
            steps=[PlannerStep(agent="ledger", action="portfolio_pnl_drilldown", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_sip_status(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in (
            "did i pay sip",
            "did i pay my sip",
            "sip status",
            "sips due",
            "installments left",
            "sip schedule",
            "my sips",
        )
    ) or (
        "sip" in lower
        and any(w in lower for w in ("pay", "paid", "due", "status", "installment"))
    ):
        return PlannerOutput(
            intent=Intent.sip_status_query,
            steps=[PlannerStep(agent="ledger", action="sip_status_query", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_fd_maturity(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in (
            "fd maturity",
            "rd maturity",
            "when does my fd",
            "when does my rd",
            "maturity date",
            "fixed deposit mature",
        )
    ):
        return PlannerOutput(
            intent=Intent.fd_maturity_query,
            steps=[PlannerStep(agent="ledger", action="fd_maturity_query", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_upcoming_obligations(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in (
            "upcoming obligations",
            "upcoming bills",
            "what's due",
            "whats due",
            "due this month",
            "what do i owe",
            "obligations hub",
            "show obligations",
            "show my obligations",
        )
    ) or ("obligations" in lower) or (
        "due" in lower and any(w in lower for w in ("bill", "emi", "sip", "month"))
    ):
        return PlannerOutput(
            intent=Intent.upcoming_obligations,
            steps=[PlannerStep(agent="ledger", action="upcoming_obligations", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_loan_emi_summary(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in (
            "loan emi",
            "total emi",
            "how much emi",
            "emis left",
            "emi summary",
            "my emis",
        )
    ) or ("emi" in lower and "loan" in lower):
        return PlannerOutput(
            intent=Intent.loan_emi_summary,
            steps=[PlannerStep(agent="ledger", action="loan_emi_summary", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_affordability(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if any(
        phrase in lower
        for phrase in (
            "can i afford",
            "safe emi",
            "affordability",
            "afford a loan",
            "afford new emi",
        )
    ):
        return PlannerOutput(
            intent=Intent.affordability_check,
            steps=[PlannerStep(agent="ledger", action="compute_affordability", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_explain_transaction(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if not any(
        phrase in lower
        for phrase in (
            "explain this",
            "what is this charge",
            "what is this transaction",
            "what is this payment",
            "explain the charge",
            "show recent",
            "show my recent",
            "what did i spend at",
        )
    ):
        return None
    merchant = None
    for pattern in (
        r"explain\s+(?:the\s+)?(?:charge|transaction|payment)?\s*(?:from|at|for|by)?\s+(.+?)(?:\?|$)",
        r"what is this charge (?:from|for)\s+(.+?)(?:\?|$)",
        r"show (?:my )?recent\s+(.+?)\s+(?:transactions|charges)(?:\?|$)",
        r"what did i spend at\s+(.+?)(?:\?|$)",
    ):
        m = re.search(pattern, message, re.I)
        if m:
            merchant = m.group(1).strip().rstrip(".")
            break
    params: dict = {}
    if merchant:
        params["merchant"] = merchant
    return PlannerOutput(
        intent=Intent.explain_transaction,
        steps=[PlannerStep(agent="ledger", action="explain_transaction", params=params)],
        ui_mode="guided_flow",
    )


def _detect_recategorize_transaction(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if not any(
        phrase in lower
        for phrase in (
            "recategorize",
            "change category",
            "change the category",
            "move to category",
            "categorize as",
            "classify as",
            "classify ",
            "mark as",
        )
    ):
        return None
    new_category = None
    for pattern in (
        r"(?:recategorize|categorize|classify|mark)\s+.+?\s+(?:as|to)\s+(.+?)(?:\.|$)",
        r"change\s+(?:the\s+)?category\s+(?:of\s+.+?\s+)?to\s+(.+?)(?:\.|$)",
        r"move\s+to\s+(.+?)(?:\s+category)?(?:\.|$)",
    ):
        m = re.search(pattern, message, re.I)
        if m:
            new_category = m.group(1).strip().rstrip(".")
            break
    if not new_category:
        return None
    merchant = None
    for pattern in (
        r"(?:recategorize|categorize|classify|change category of|mark)\s+(.+?)\s+(?:as|to)\s+",
    ):
        m = re.search(pattern, message, re.I)
        if m:
            merchant = m.group(1).strip()
            break
    params: dict = {"new_category": new_category}
    if merchant:
        params["merchant"] = merchant
    return PlannerOutput(
        intent=Intent.recategorize_transaction,
        steps=[PlannerStep(agent="ledger", action="insert_recategorize", params=params)],
        ui_mode="guided_flow",
    )


def _detect_create_account_guided(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if not any(
        phrase in lower
        for phrase in (
            "add sip account",
            "create sip",
            "add mutual fund",
            "create mutual fund",
            "add mf account",
            "create mf account",
            "add epf",
            "create epf",
            "add fd account",
            "create fd",
            "add recurring deposit",
        )
    ):
        return None
    account_type = "mutual_fund"
    if "epf" in lower:
        account_type = "epf"
    elif "fd" in lower or "fixed deposit" in lower:
        account_type = "fixed_deposit"
    elif "recurring deposit" in lower or " rd " in lower:
        account_type = "recurring_deposit"
    investment_mode = "sip" if "sip" in lower else None
    amount_match = re.search(r"(\d+(?:\.\d+)?)", message)
    name = ""
    for pat in (
        r"(?:add|create)\s+(?:sip|mutual fund|mf|epf|fd|recurring deposit|rd)\s+account\s+(?:\d+\s+)?(?:for|named?)\s+(.+?)(?:\s*$)",
        r"(?:add|create)\s+(?:sip|mutual fund|mf|epf|fd|recurring deposit|rd)\s+(?:account\s+)?(?:\d+\s+)?(.+?)(?:\s*$)",
    ):
        m = re.search(pat, message, re.I)
        if m:
            candidate = m.group(1).strip().rstrip(".")
            candidate = re.sub(r"^\d+\s+", "", candidate).strip()
            if candidate:
                name = candidate
                break
    params: dict = {"account_type": account_type, "name": name}
    if investment_mode:
        params["investment_mode"] = investment_mode
    if amount_match and investment_mode == "sip":
        params["emi_amount"] = float(amount_match.group(1))
    return PlannerOutput(
        intent=Intent.create_account_guided,
        steps=[PlannerStep(agent="ledger", action="insert_account", params=params)],
        ui_mode="guided_flow",
    )


def _detect_record_transfer(message: str) -> PlannerOutput | None:
    lower = message.lower()
    transfer_phrases = (
        "record sip",
        "transfer to mf",
        "transfer to mutual",
        "to my mutual",
        "fund my sip",
        "fund sip",
        "paid sip",
        "record transfer",
        "transfer to my",
        "sip payment",
        "invested in",
    )
    has_transfer_phrase = any(phrase in lower for phrase in transfer_phrases)
    has_transfer_amount = bool(re.search(r"transfer\s+\d", lower))
    if not (has_transfer_phrase or has_transfer_amount):
        return None
    amount_match = re.search(r"(\d+(?:\.\d+)?)", message)
    if not amount_match:
        return None
    amount = float(amount_match.group(1))
    investment_name = None
    for pattern in (
        r"record sip\s+(?:\d+(?:\.\d+)?\s+)?(?:for\s+)?(.+?)(?:\.|$)",
        r"transfer\s+\d+(?:\.\d+)?\s+to\s+(.+?)(?:\.|$)",
        r"fund\s+(?:my\s+)?sip(?:\s+\d+(?:\.\d+)?)?\s+(?:for\s+)?(.+?)(?:\.|$)",
        r"for\s+(.+?)(?:\.|$)",
    ):
        m = re.search(pattern, message, re.I)
        if m:
            investment_name = m.group(1).strip()
            break
    params: dict = {"amount": amount}
    if investment_name:
        params["investment_name"] = investment_name
    return PlannerOutput(
        intent=Intent.record_transfer,
        steps=[
            PlannerStep(
                agent="ledger",
                action="insert_transfer",
                params=params,
            )
        ],
        ui_mode="guided_flow",
    )


def _detect_create_recurring_bill(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if not any(
        phrase in lower
        for phrase in (
            "recurring bill",
            "add rent",
            "set up rent",
            "monthly subscription",
            "add subscription",
        )
    ):
        return None
    amount_match = re.search(r"(\d+(?:\.\d+)?)", message)
    if not amount_match:
        return None
    amount = float(amount_match.group(1))
    name = None
    for pattern in (
        r"recurring bill\s+(.+?)\s+\d",
        r"add rent\s+(.+?)\s+\d",
        r"subscription\s+(.+?)\s+\d",
        r"bill\s+(.+?)\s+\d",
    ):
        m = re.search(pattern, message, re.I)
        if m:
            name = m.group(1).strip()
            break
    if not name:
        name = "Recurring bill"
    return PlannerOutput(
        intent=Intent.create_recurring_bill,
        steps=[
            PlannerStep(
                agent="ledger",
                action="insert_recurring_bill",
                params={"name": name, "amount": amount, "frequency": "monthly"},
            )
        ],
        ui_mode="guided_flow",
    )


def _slice1_keyword_route(message: str) -> PlannerOutput | None:
    """Keyword fallbacks for Slice 1 intents (works with LLM_PROVIDER=none)."""
    for detector in (
        _detect_portfolio_summary,
        _detect_sip_status,
        _detect_fd_maturity,
        _detect_portfolio_pnl,
        _detect_investment_allocation,
    ):
        result = detector(message)
        if result:
            return result
    return None


def _slice2_keyword_route(message: str) -> PlannerOutput | None:
    """Keyword fallbacks for Slice 2 intents (works with LLM_PROVIDER=none)."""
    for detector in (
        _detect_upcoming_obligations,
        _detect_loan_emi_summary,
        _detect_affordability,
        _detect_create_recurring_bill,
    ):
        result = detector(message)
        if result:
            return result
    return None


def _detect_import_statement(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if not any(
        phrase in lower
        for phrase in (
            "import statement",
            "upload statement",
            "import csv",
            "import bank statement",
            "upload csv",
            "import pdf",
        )
    ):
        return None
    return PlannerOutput(
        intent=Intent.import_statement,
        steps=[],
        ui_mode="guided_flow",
    )


def _slice3_keyword_route(message: str) -> PlannerOutput | None:
    """Keyword fallbacks for Slice 3 intents (works with LLM_PROVIDER=none)."""
    for detector in (
        _detect_import_statement,
    ):
        result = detector(message)
        if result:
            return result
    return None


def clean_deepseek_args(raw_args: str) -> dict:
    import re
    # Remove <think>...</think> blocks common in reasoning models
    cleaned = re.sub(r'<think>.*?</think>', '', raw_args, flags=re.DOTALL)
    # Strip everything outside of the first { and last }
    match = re.search(r'\{.*\}', cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON Decode error after cleaning: {e} | Raw string: {raw_args}")
        return {}

class CoordinatorAgent(BaseAgent):
    """
    Google ADK BaseAgent implementation acting as the Coordinator.
    It uses semantic routing to dispatch, and LLM to extract parameters.
    """
    name: str = "CoordinatorAgent"
    
    async def invoke(self, message: str, state: ConversationState | None = None) -> PlannerOutput:
        msg = message.strip() if message else ""
        if not msg:
            return PlannerOutput(intent=Intent.unknown, steps=[], ui_mode="guided_flow")

        function_name = None

        # S3.4 detectors must run before _detect_spending_period since "spend/spent" is a broad keyword
        explain = _detect_explain_transaction(msg)
        if explain:
            return explain

        recat = _detect_recategorize_transaction(msg)
        if recat:
            return recat

        spending_period = _detect_spending_period(msg)
        if spending_period:
            return PlannerOutput(
                intent=Intent.spending_analysis,
                steps=[
                    PlannerStep(
                        agent="ledger",
                        action="compute_monthly_spend",
                        params={"period": spending_period},
                    )
                ],
                ui_mode="guided_flow",
            )

        lower = msg.lower()
        if any(w in lower for w in ("salary", "got paid", "record income", "add income", "received")):
            return PlannerOutput(
                intent=Intent.add_income,
                steps=[PlannerStep(agent="ledger", action="insert_income", params={"merchant": "Income"})],
                ui_mode="guided_flow",
            )

        acct_guided = _detect_create_account_guided(msg)
        if acct_guided:
            return acct_guided

        transfer = _detect_record_transfer(msg)
        if transfer:
            return transfer

        recurring = _detect_create_recurring_bill(msg)
        if recurring:
            return recurring

        expense = _detect_add_expense(msg)
        if expense:
            return expense

        net_worth = _detect_net_worth(msg)
        if net_worth:
            return net_worth

        slice1 = _slice1_keyword_route(msg)
        if slice1:
            return slice1

        slice2 = _slice2_keyword_route(msg)
        if slice2:
            return slice2

        slice3 = _slice3_keyword_route(msg)
        if slice3:
            return slice3

        if get_llm_provider() == LLMProvider.none:
            return PlannerOutput(
                intent=Intent.unknown,
                steps=[],
                ui_mode="guided_flow",
                message=(
                    "I can help with expenses, net worth, spending, investments, or obligations. "
                    "Try 'what's due this month?'"
                ),
            )

        # 1. Semantic Routing (Fast Intent Classification)
        if router:
            try:
                route_result = router(msg)
                if route_result.name:
                    print(f"Semantic Router Hit: {route_result.name}")
                    function_name = route_result.name
            except Exception as e:
                print(f"Router err: {e}")

        client = get_client()

        # Filter tools if semantic router found a perfect match
        active_tools = TOOLS
        if function_name:
            active_tools = [t for t in TOOLS if t["function"]["name"] == function_name] or TOOLS

        tools_description = json.dumps([t["function"] for t in active_tools], indent=2)

        system_prompt = (
            "You are Finance Copilot, an AI assistant for a personal finance app. "
            f"Today's date is {date.today().isoformat()}. "
            "Your job is to route user requests to the correct ledger function OR answer their general questions.\n\n"
            "You have the following skills (tools) available:\n"
            f"{tools_description}\n\n"
            "For spending summaries, pie charts, histograms, or dashboards, you MUST call compute_monthly_spend. "
            "Never tell the user you cannot create charts—the UI renders them from tool results.\n"
            "You MUST respond ONLY with a valid JSON object. Do not include any text outside the JSON object.\n"
            "If the user request requires a skill/tool, use this format:\n"
            "{\n"
            '  "tool": "function_name",\n'
            '  "parameters": { "param1": "value1" }\n'
            "}\n\n"
            "If the user is just chatting, asking a general finance question, or the request does NOT match any tool, reply with a helpful conversational message using this format:\n"
            "{\n"
            '  "message": "Your helpful response here"\n'
            "}"
        )

        messages = [{"role": "system", "content": system_prompt}]
        if state and state.agent_history:
            for h in state.agent_history[-6:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": msg})


        try:
            response_stream = await client.chat.completions.create(
                model=_active_model,
                messages=messages,
                temperature=0.1,
                stream=True
            )

            text_response = ""
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    text_response += chunk.choices[0].delta.content
            
            # Extract JSON from response
            parsed_json = clean_deepseek_args(text_response)
            
            if "tool" in parsed_json:
                extracted_name = parsed_json["tool"]
                params = parsed_json.get("parameters", {})
                    
                if extracted_name == "insert_transaction" and "amount" in params:
                    if params["amount"] > 0:
                        extracted_name = "insert_income"
                    else:
                        params["amount"] = -abs(params["amount"])
                         
                intent = _INTENT_MAP.get(extracted_name, Intent.unknown)
                
                return PlannerOutput(
                    intent=intent,
                    steps=[PlannerStep(agent="ledger", action=extracted_name, params=params)],
                    ui_mode="guided_flow",
                )
            elif "message" in parsed_json:
                 text_response = parsed_json["message"]
                 return PlannerOutput(
                     intent=Intent.unknown, 
                     steps=[], 
                     ui_mode="guided_flow", 
                     message=text_response
                 )
            else:
                # Fallback mapping if LLM returns text but router hit successfully
                if function_name:
                    intent = _INTENT_MAP.get(function_name, Intent.unknown)
                    params: dict = {}
                    if function_name == "compute_monthly_spend":
                        params["period"] = spending_period or _detect_spending_period(msg) or "this_month"
                    return PlannerOutput(
                        intent=intent,
                        steps=[PlannerStep(agent="ledger", action=function_name, params=params)],
                        ui_mode="guided_flow",
                        message="Processed via fast routing."
                    )

                return PlannerOutput(intent=Intent.unknown, steps=[], ui_mode="guided_flow", message="Could not determine the routing.")

        except Exception as e:
            print(f"OpenAI Plan Error: {e}")
            return PlannerOutput(intent=Intent.unknown, steps=[], ui_mode="guided_flow")


# Create a singleton ADK agent for orchestrator
coordinator = CoordinatorAgent()

async def plan(message: str, state: ConversationState | None = None) -> PlannerOutput:
    """Wrapper function to maintain backward compatibility with orchestrator imports"""
    return await coordinator.invoke(message, state)
