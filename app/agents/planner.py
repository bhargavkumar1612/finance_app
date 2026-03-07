"""
AI Planner: Semantic Routing + Intent Extraction.
Uses Google ADK and Semantic Router.
"""
import json
import os
from datetime import date
from typing import Optional

# Semantic Router for fast intent matching
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import FastEmbedEncoder

# Google ADK for agent orchestration
from google.adk.agents import BaseAgent, LlmAgent
from openai import AsyncOpenAI

from app.core.config import settings
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
            "How much did I spend last month?"
        ]
    )
]

# Provide fallback router logic
try:
    router = SemanticRouter(encoder=encoder, routes=routes)
except Exception as e:
    print(f"Failed to initialize Semantic Router: {e}")
    router = None

_INTENT_MAP = {
    "insert_transaction": Intent.add_expense,
    "compute_net_worth": Intent.net_worth_query,
    "compute_monthly_spend": Intent.spending_analysis,
    "compute_affordability": Intent.affordability_check,
    "import_statement": Intent.import_statement,
    "analyze_category_spending": Intent.analyze_category_spending,
    "track_subscriptions": Intent.track_subscriptions,
    "analyze_cash_flow": Intent.analyze_cash_flow,
    "get_top_expenses": Intent.get_top_expenses,
    "budget_vs_actual": Intent.budget_vs_actual,
    "project_future_balance": Intent.project_future_balance,
    "debt_payoff_planner": Intent.debt_payoff_planner,
    "investment_allocation": Intent.investment_allocation,
    "vendor_spending_history": Intent.vendor_spending_history,
    "unusual_spending_alert": Intent.unusual_spending_alert,
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
      "description": "Calculates total spending and breakdowns by category. Use this for 'where did I spend my money?', 'monthly spending', 'how much did I spend last month?'.",
      "parameters": {
        "type": "object",
        "properties": {
          "period": { "type": "string", "enum": ["this_month", "last_month"], "description": "The time period to analyze" }
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
  }
]

# Client logic
_client = None
_active_model = "deepseek-r1:latest"

def get_client() -> AsyncOpenAI:
    global _client, _active_model
    if _client is None:
        try:
            with open("llms.json", "r") as f:
                llms = json.load(f)
                active = next((l for l in llms if l.get("ACTIVE")), None)
                if active:
                    print(f"Loaded active LLM config: {active['LLM_PROVIDER']} - {active['LLM_MODEL']}")
                    _active_model = active.get("LLM_MODEL", "deepseek-r1:latest")
                    _client = AsyncOpenAI(
                        base_url=active.get("LLM_BASE_URL"),
                        api_key=active.get("LLM_API_KEY", "ollama")
                    )
                else:
                    raise ValueError("No active LLM found in llms.json")
        except Exception as e:
            print(f"Error loading llms.json, falling back to defaults: {e}")
            _client = AsyncOpenAI(
                base_url="https://artful-microchemical-madie.ngrok-free.dev/v1",
                api_key="ollama"
            )
    return _client

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
                    return PlannerOutput(
                        intent=intent,
                        steps=[PlannerStep(agent="ledger", action=function_name, params={})],
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
