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
from app.services.llm_client import try_get_env_async_client_and_model
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

        expense = _detect_add_expense(msg)
        if expense:
            return expense

        net_worth = _detect_net_worth(msg)
        if net_worth:
            return net_worth

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
