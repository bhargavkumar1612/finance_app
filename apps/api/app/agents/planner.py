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
from app.services.llm_client import LLMProvider, get_llm_planner_mode, get_llm_provider, try_get_env_async_client_and_model
from app.core.schemas import Intent, PlannerOutput, PlannerStep, ConversationState, AgentTrace

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

# Provide fallback router logic — auto_sync builds the local embedding index from routes
try:
    router = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")
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
          "target_emi": { "type": "number", "description": "The optional target EMI amount they want to check" },
          "hypothetical_monthly_income": {
            "type": "number",
            "description": "Assumed monthly income when user clarifies salary but has not recorded it yet"
          }
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

def _looks_like_expense_capture(lower: str) -> bool:
    """Distinguish 'add 200 for lunch' from 'where did I spend this month'."""
    if re.search(r"\b(add|record|log)\s+\d", lower):
        return True
    if re.search(r"\b(spent|paid)\s+\d", lower):
        return True
    if re.search(r"\d+\s+(?:rupees?|rs|inr|₹)?\s*(?:for|on)\s+\w", lower):
        return True
    return False


def _detect_spending_period(message: str) -> str | None:
    """Keyword fallback so chart/year spending requests reach the ledger tool."""
    lower = message.lower()
    if _looks_like_expense_capture(lower):
        return None
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


def _parse_money_amount(message: str) -> float | None:
    """Parse INR amounts including 20k, 1.5L, 190000."""
    lower = message.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*k\b", lower)
    if m:
        return float(m.group(1)) * 1000
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:l|lac|lakh|lacs|lakhs)\b", lower)
    if m:
        return float(m.group(1)) * 100000
    m = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", message, re.I)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", message)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _parse_emi_from_message(message: str) -> float | None:
    lower = message.lower()
    if "emi" not in lower and "afford" not in lower:
        return None
    m = re.search(
        r"emi\s*(?:of|for|:)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*k?\b",
        lower,
    )
    if m:
        val = float(m.group(1))
        tail = lower[m.end() : m.end() + 2]
        if "k" in tail or re.search(rf"{re.escape(m.group(1))}\s*k", lower):
            val *= 1000
        return val
    return _parse_money_amount(message)


def _recent_affordability_context(state: ConversationState | None) -> dict | None:
    if not state:
        return None
    afford = state.current_step == Intent.affordability_check.value
    params: dict = {}
    for h in reversed(state.agent_history[:-1]):
        content = h.get("content") or ""
        lower = content.lower()
        if "afford" in lower or re.search(r"\bemi\b", lower):
            afford = True
            if "target_emi" not in params:
                emi = _parse_emi_from_message(content)
                if emi:
                    params["target_emi"] = emi
    if not afford:
        return None
    return params


def _detect_affordability_income_followup(
    message: str,
    state: ConversationState | None,
) -> PlannerOutput | None:
    """Follow-up like 'my salary is 190k/mo' after an affordability question."""
    ctx = _recent_affordability_context(state)
    if ctx is None:
        return None

    lower = message.lower()
    if not any(c in lower for c in ("salary", "income", "earn", "credited", "take home")):
        return None
    if re.search(r"\b(add|record|log)\s+(?:my\s+)?(?:salary|income)", lower):
        return None

    amount = _parse_money_amount(message)
    if not amount:
        return None

    params = {**ctx, "hypothetical_monthly_income": amount}
    return PlannerOutput(
        intent=Intent.affordability_check,
        steps=[PlannerStep(agent="ledger", action="compute_affordability", params=params)],
        ui_mode="guided_flow",
    )


def _detect_affordability_emi_followup(
    message: str,
    state: ConversationState | None,
) -> PlannerOutput | None:
    """Follow-up like 'what about 30k emi instead?' after an affordability question."""
    ctx = _recent_affordability_context(state)
    if ctx is None:
        return None
    lower = message.lower()
    if not any(c in lower for c in ("what about", "how about", "instead", "try ", "emi")):
        return None
    emi = _parse_emi_from_message(message) or _parse_money_amount(message)
    if not emi:
        return None
    params = {**ctx, "target_emi": emi}
    return PlannerOutput(
        intent=Intent.affordability_check,
        steps=[PlannerStep(agent="ledger", action="compute_affordability", params=params)],
        ui_mode="guided_flow",
    )


def _detect_add_income(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if not any(w in lower for w in ("salary", "got paid", "record income", "add income", "received")):
        return None
    explicit_capture = any(
        phrase in lower
        for phrase in ("add ", "record income", "log income", "got paid", "received ")
    )
    clarification = any(
        phrase in lower
        for phrase in ("will be credited", "every month", "monthly salary", "take home", "i earn", "i make")
    )
    if clarification and not explicit_capture:
        return None
    amount = _parse_money_amount(message)
    if amount is None:
        return None
    merchant = "Salary" if "salary" in lower else "Income"
    return PlannerOutput(
        intent=Intent.add_income,
        steps=[
            PlannerStep(
                agent="ledger",
                action="insert_income",
                params={"amount": amount, "merchant": merchant, "category": "Income"},
            )
        ],
        ui_mode="guided_flow",
    )


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
    for pattern in (
        r"\bfor\s+(.+?)(?:\.|$)",
        r"\bspend\s+on\s+(.+?)(?:\.|$)",
        r"\bon\s+(.+?)(?:\.|$)",
    ):
        m = re.search(pattern, message, re.I)
        if m:
            merchant = m.group(1).strip()
            break
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


_ACCOUNT_BALANCE_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("epf", ("epf", "provident fund", "employee provident")),
    ("mutual_fund", ("mutual fund", "mutual funds")),
    ("fixed_deposit", ("fixed deposit", " fd ", "my fd")),
    ("recurring_deposit", ("recurring deposit", " rd ", "my rd")),
    ("stock", ("stock", "stocks", "demat")),
    ("bank", ("bank account", "my bank", "savings")),
    ("wallet", ("wallet", "paytm", "phonepe")),
    ("loan", ("loan", "emi account")),
)


def _account_type_in_message(lower: str) -> str | None:
    if re.search(r"\bmf\b|\bmfs\b", lower):
        return "mutual_fund"
    for account_type, phrases in _ACCOUNT_BALANCE_ALIASES:
        if any(phrase in lower for phrase in phrases):
            return account_type
    return None


def _is_account_scoped_balance_query(lower: str) -> bool:
    if _account_type_in_message(lower) is None:
        return False
    return any(
        phrase in lower
        for phrase in (
            "how much",
            "balance",
            "money in",
            "money do i have",
            "what do i have",
            "how much do i have",
            "amount in",
        )
    )


def _is_portfolio_style_query(lower: str) -> bool:
    """Performance/allocation questions should use portfolio tools, not account list."""
    if any(
        w in lower
        for w in (
            "perform", "performance", "p&l", "pnl", "profit", "allocation",
            "how are they", "how are my", "dashboard", "portfolio", "invested in",
            "invested", "top performer", " doing",
        )
    ):
        return True
    return ("mutual fund" in lower or "mutual funds" in lower) and "how much" in lower


def _detect_compound_affordability(message: str) -> PlannerOutput | None:
    """Multi-topic safety/affordability questions → single affordability tool."""
    lower = message.lower()
    if not any(w in lower for w in ("compare", "safe", "enough", "afford", "holistic", "overall", "saving")):
        return None
    has_obligations = any(w in lower for w in ("obligation", "emi", "sip", "due", "bill", "loan"))
    has_spending = any(w in lower for w in ("spend", "spending", "spent", "expense"))
    if has_obligations and (has_spending or "afford" in lower or "safe" in lower):
        return PlannerOutput(
            intent=Intent.affordability_check,
            steps=[PlannerStep(agent="ledger", action="compute_affordability", params={})],
            ui_mode="guided_flow",
        )
    return None


def _detect_account_balance_query(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if _is_portfolio_style_query(lower):
        return None
    if not _is_account_scoped_balance_query(lower):
        return None
    account_type = _account_type_in_message(lower)
    if not account_type:
        return None
    return PlannerOutput(
        intent=Intent.manage_accounts,
        steps=[
            PlannerStep(
                agent="ledger",
                action="list_accounts",
                params={"account_type": account_type},
            )
        ],
        ui_mode="guided_flow",
    )


def _detect_net_worth(message: str) -> PlannerOutput | None:
    lower = message.lower()
    if _is_account_scoped_balance_query(lower):
        return None
    if any(w in lower for w in ("net worth", "total assets", "what am i worth")):
        return PlannerOutput(
            intent=Intent.net_worth_query,
            steps=[PlannerStep(agent="ledger", action="compute_net_worth", params={})],
            ui_mode="guided_flow",
        )
    if "how much money" in lower and not any(
        w in lower for w in (" in my ", " in the ", " in a ", "account")
    ):
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
            "what mutual funds",
            "which mutual funds",
            "mutual funds did i",
            "mutual funds have i",
        )
    ) or ("portfolio" in lower and "invest" in lower) or ("mf" in lower and any(w in lower for w in ("doing", "performance", "performing", "p&l", "pnl"))):
        return PlannerOutput(
            intent=Intent.portfolio_summary,
            steps=[PlannerStep(agent="ledger", action="portfolio_summary", params={})],
            ui_mode="guided_flow",
        )
    mf_terms = ("mutual fund", "mutual funds")
    if any(t in lower for t in mf_terms) and any(
        w in lower for w in ("invest", "invested", "how much", "performing", "performance", "doing", "worth", "holdings")
    ):
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
            "afford an emi",
        )
    ):
        params: dict = {}
        emi = _parse_emi_from_message(message)
        if emi:
            params["target_emi"] = emi
        return PlannerOutput(
            intent=Intent.affordability_check,
            steps=[PlannerStep(agent="ledger", action="compute_affordability", params=params)],
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
    # Remove reasoning blocks common in reasoning models (think / redacted_thinking tags)
    cleaned = re.sub(
        r"<\s*think\s*>.*?<\s*/\s*think\s*>",
        "",
        raw_args,
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
    # Strip everything outside of the first { and last }
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON Decode error after cleaning: {e} | Raw string: {raw_args}")
        return {}


def extract_thinking(raw: str) -> str | None:
    """Extract model reasoning/thinking blocks before JSON parsing."""
    for pattern in (
        r"<\s*think\s*>(.*?)<\s*/\s*think\s*>",
        r"<think>(.*?)</think>",
    ):
        match = re.search(pattern, raw, flags=re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            if text:
                return text
    return None


def _infer_keyword_trace(output: PlannerOutput) -> AgentTrace:
    tool = output.steps[0].action if output.steps else None
    if output.message and not output.steps:
        return AgentTrace(
            route="fallback",
            intent=output.intent.value,
            note=output.message[:200],
        )
    return AgentTrace(route="keyword", intent=output.intent.value, tool=tool)


def _attach_trace(output: PlannerOutput, trace: AgentTrace) -> PlannerOutput:
    return output.model_copy(update={"trace": trace})


def _semantic_route_hint(message: str) -> str | None:
    if not router:
        return None
    try:
        if not router.index.is_ready():
            router.sync("local")
        if router.index.is_ready():
            route_result = router(message)
            if route_result.name:
                print(f"Semantic Router Hit: {route_result.name}")
                return route_result.name
    except Exception as e:
        print(f"Router err: {e}")
    return None


def _build_planner_context_block(state: ConversationState | None) -> str:
    if not state:
        return ""
    parts: list[str] = []
    if state.current_step:
        parts.append(f"Active flow: {state.current_step}")
    pending = state.filled_slots.get("pending_mutation")
    if pending:
        parts.append(
            "Pending user confirmation: "
            f"{pending.get('intent')} via {pending.get('action')} "
            f"with params {json.dumps(pending.get('params') or {}, default=str)[:300]}"
        )
    prior = state.agent_history[:-1] if state.agent_history else []
    if prior:
        lines = [
            f"{h.get('role', 'user')}: {(h.get('content') or '')[:160]}"
            for h in prior[-6:]
        ]
        parts.append("Recent conversation:\n" + "\n".join(lines))
    return "\n\n".join(parts)


def _needs_contextual_llm(message: str, state: ConversationState | None) -> bool:
    """True when the message likely needs prior turns to interpret correctly."""
    if not state:
        return False
    lower = message.lower().strip()
    prior = [h for h in state.agent_history[:-1] if (h.get("content") or "").strip()]
    if not prior:
        return False

    follow_up_cues = (
        "but ",
        "what about",
        "how about",
        "instead",
        "also ",
        "you said",
        "earlier",
        "that emi",
        "that loan",
        "same ",
        "still ",
        "actually ",
        "however ",
        "though ",
        "even if",
        "assuming ",
        "if my",
        "will be credited",
        "every month",
        "monthly salary",
        "based on that",
        "given that",
        "in that case",
    )
    if any(c in lower for c in follow_up_cues):
        return True

    if state.current_step in (
        Intent.affordability_check.value,
        Intent.spending_analysis.value,
        Intent.net_worth_query.value,
        Intent.portfolio_summary.value,
        Intent.upcoming_obligations.value,
    ):
        return True

    if state.filled_slots.get("pending_mutation") and any(
        w in lower for w in ("change", "make it", "update", "instead", "lower", "higher")
    ):
        return True

    if len(lower.split()) > 18 or lower.count("?") > 1:
        return True
    if " and " in lower and any(
        w in lower for w in ("afford", "spend", "emi", "invest", "save", "loan", "sip", "salary")
    ):
        return True
    return False


def _prefer_llm_planner(message: str, state: ConversationState | None) -> bool:
    if get_llm_provider() == LLMProvider.none:
        return False
    mode = get_llm_planner_mode()
    if mode.value == "keywords_only":
        return False
    if mode.value == "always":
        return True
    return _needs_contextual_llm(message, state)


async def _llm_plan(
    msg: str,
    state: ConversationState | None,
    *,
    semantic_hint: str | None = None,
    contextual: bool = False,
) -> PlannerOutput:
    """Route via LLM with conversation context. Ledger tools still execute deterministically."""
    client = get_client()
    model_name = _active_model
    context_block = _build_planner_context_block(state)

    active_tools = TOOLS
    if semantic_hint and not contextual:
        active_tools = [t for t in TOOLS if t["function"]["name"] == semantic_hint] or TOOLS

    tools_description = json.dumps([t["function"] for t in active_tools], indent=2)
    context_section = ""
    if context_block:
        context_section = (
            f"\n\nConversation context (use this to fill tool parameters and interpret follow-ups):\n"
            f"{context_block}\n"
        )
    hint_section = ""
    if semantic_hint:
        hint_section = (
            f"\nSemantic router hint: `{semantic_hint}` "
            "(suggestion only — pick the best tool using full context).\n"
        )

    system_prompt = (
        "You are Finance Copilot, an AI assistant for a personal finance app. "
        f"Today's date is {date.today().isoformat()}. "
        "Your job is to route user requests to the correct ledger function OR answer general questions.\n\n"
        "You have the following skills (tools) available:\n"
        f"{tools_description}\n"
        f"{context_section}"
        f"{hint_section}\n"
        "Context rules:\n"
        "- Use prior messages to fill parameters (e.g. target_emi from an earlier EMI question).\n"
        "- If the user clarifies salary/income during an affordability discussion, call compute_affordability "
        "with hypothetical_monthly_income — do NOT call insert_income unless they explicitly ask to record/add/log income.\n"
        "- For spending summaries, charts, or dashboards, call compute_monthly_spend.\n"
        "- Never invent numbers; extract amounts from the current or prior user messages.\n"
        "- Never tell the user you cannot create charts — the UI renders them from tool results.\n\n"
        "You MUST respond ONLY with a valid JSON object. Do not include any text outside the JSON object.\n"
        "If the user request requires a skill/tool, use this format:\n"
        "{\n"
        '  "tool": "function_name",\n'
        '  "parameters": { "param1": "value1" }\n'
        "}\n\n"
        "If the user is chatting generally or no tool fits, reply with:\n"
        "{\n"
        '  "message": "Your helpful response here"\n'
        "}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if state and state.agent_history:
        for h in state.agent_history[-8:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": msg})

    try:
        response_stream = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.1,
            stream=True,
        )

        text_response = ""
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                text_response += chunk.choices[0].delta.content

        thinking = extract_thinking(text_response)
        parsed_json = clean_deepseek_args(text_response)
        base_route = "llm_context" if contextual else "llm_tool"

        if "tool" in parsed_json:
            extracted_name = parsed_json["tool"]
            params = parsed_json.get("parameters", {})

            if extracted_name == "insert_transaction" and "amount" in params:
                if params["amount"] > 0:
                    extracted_name = "insert_income"
                else:
                    params["amount"] = -abs(params["amount"])

            intent = _INTENT_MAP.get(extracted_name, Intent.unknown)
            trace = AgentTrace(
                route=base_route,
                intent=intent.value,
                tool=extracted_name,
                semantic_match=semantic_hint,
                thinking=thinking,
                model=model_name,
                note="LLM selected ledger tool (context-aware)" if contextual else "LLM selected ledger tool",
            )
            return _attach_trace(
                PlannerOutput(
                    intent=intent,
                    steps=[PlannerStep(agent="ledger", action=extracted_name, params=params)],
                    ui_mode="guided_flow",
                ),
                trace,
            )

        if "message" in parsed_json:
            return _attach_trace(
                PlannerOutput(
                    intent=Intent.unknown,
                    steps=[],
                    ui_mode="guided_flow",
                    message=parsed_json["message"],
                ),
                AgentTrace(
                    route="llm_message",
                    intent="unknown",
                    thinking=thinking,
                    model=model_name,
                    semantic_match=semantic_hint,
                    note="LLM conversational reply (no ledger tool)",
                ),
            )

        if semantic_hint:
            intent = _INTENT_MAP.get(semantic_hint, Intent.unknown)
            params: dict = {}
            if semantic_hint == "compute_monthly_spend":
                params["period"] = _detect_spending_period(msg) or "this_month"
            return _attach_trace(
                PlannerOutput(
                    intent=intent,
                    steps=[PlannerStep(agent="ledger", action=semantic_hint, params=params)],
                    ui_mode="guided_flow",
                    message="Processed via semantic fallback.",
                ),
                AgentTrace(
                    route="semantic",
                    intent=intent.value,
                    tool=semantic_hint,
                    semantic_match=semantic_hint,
                    thinking=thinking,
                    model=model_name,
                ),
            )

        return _attach_trace(
            PlannerOutput(intent=Intent.unknown, steps=[], ui_mode="guided_flow", message="Could not determine the routing."),
            AgentTrace(route="fallback", intent="unknown", thinking=thinking, model=model_name),
        )

    except Exception as e:
        print(f"OpenAI Plan Error: {e}")
        return _attach_trace(
            PlannerOutput(intent=Intent.unknown, steps=[], ui_mode="guided_flow"),
            AgentTrace(route="fallback", intent="unknown", note=f"LLM error: {e}"),
        )


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

        if _prefer_llm_planner(msg, state):
            hint = _semantic_route_hint(msg)
            llm_result = await _llm_plan(msg, state, semantic_hint=hint, contextual=True)
            if llm_result.steps or (
                llm_result.message
                and llm_result.trace
                and llm_result.trace.route not in ("fallback",)
            ):
                return llm_result

        # S3.4 detectors must run before _detect_spending_period since "spend/spent" is a broad keyword
        explain = _detect_explain_transaction(msg)
        if explain:
            return explain

        recat = _detect_recategorize_transaction(msg)
        if recat:
            return _attach_trace(recat, _infer_keyword_trace(recat))

        affordability = _detect_affordability(msg)
        if affordability:
            return _attach_trace(affordability, _infer_keyword_trace(affordability))

        compound = _detect_compound_affordability(msg)
        if compound:
            return _attach_trace(compound, _infer_keyword_trace(compound))

        afford_followup = _detect_affordability_income_followup(msg, state)
        if afford_followup:
            return _attach_trace(afford_followup, _infer_keyword_trace(afford_followup))

        emi_followup = _detect_affordability_emi_followup(msg, state)
        if emi_followup:
            return _attach_trace(emi_followup, _infer_keyword_trace(emi_followup))

        expense = _detect_add_expense(msg)
        if expense:
            return _attach_trace(expense, _infer_keyword_trace(expense))

        spending_period = _detect_spending_period(msg)
        if spending_period:
            return _attach_trace(
                PlannerOutput(
                    intent=Intent.spending_analysis,
                    steps=[
                        PlannerStep(
                            agent="ledger",
                            action="compute_monthly_spend",
                            params={"period": spending_period},
                        )
                    ],
                    ui_mode="guided_flow",
                ),
                AgentTrace(
                    route="keyword",
                    intent=Intent.spending_analysis.value,
                    tool="compute_monthly_spend",
                ),
            )

        income = _detect_add_income(msg)
        if income:
            return _attach_trace(income, _infer_keyword_trace(income))

        acct_guided = _detect_create_account_guided(msg)
        if acct_guided:
            return acct_guided

        transfer = _detect_record_transfer(msg)
        if transfer:
            return transfer

        recurring = _detect_create_recurring_bill(msg)
        if recurring:
            return recurring

        account_balance = _detect_account_balance_query(msg)
        if account_balance:
            return account_balance

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
            out = PlannerOutput(
                intent=Intent.unknown,
                steps=[],
                ui_mode="guided_flow",
                message=(
                    "I can help with expenses, net worth, spending, investments, or obligations. "
                    "Try 'what's due this month?'"
                ),
            )
            return _attach_trace(out, AgentTrace(route="fallback", intent="unknown", note="LLM_PROVIDER=none"))

        hint = _semantic_route_hint(msg)
        return await _llm_plan(msg, state, semantic_hint=hint, contextual=False)


# Create a singleton ADK agent for orchestrator
coordinator = CoordinatorAgent()

async def plan(message: str, state: ConversationState | None = None) -> PlannerOutput:
    """Wrapper function to maintain backward compatibility with orchestrator imports"""
    output = await coordinator.invoke(message, state)
    if output.trace is None:
        output = _attach_trace(output, _infer_keyword_trace(output))
    return output
