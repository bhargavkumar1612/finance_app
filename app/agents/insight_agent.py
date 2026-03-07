import json
import re
from datetime import date
from typing import Any

from app.core.schemas import Intent
from app.agents.planner import get_client, _active_model

async def run(
    session,
    user_id,
    intent: Intent,
    ledger_result: dict[str, Any]
) -> dict[str, Any]:
    """
    Takes the deterministic output of the Ledger agent and generates a user-friendly narrative.
    """
    # Only generate insights for specific analytical intents
    insight_intents = [
        Intent.spending_analysis, 
        Intent.net_worth_query, 
        Intent.affordability_check,
        Intent.analyze_category_spending,
        Intent.analyze_cash_flow
    ]
    
    if not ledger_result or intent not in insight_intents:
        return ledger_result
        
    client = get_client()

    # Format the prompt
    system_prompt = (
        "You are Finance Copilot, a helpful and concise personal finance AI. "
        f"Today's date is {date.today().isoformat()}. "
        "Your task is to review the following structured financial data and write a short, friendly 1-2 sentence narrative summarizing it. "
        "Do NOT invent any numbers. Only use the numbers provided in the data. "
        "Do NOT include markdown. Just return the raw text."
    )
    
    # Strip heavy data out if necessary, but ledger_result is usually small summaries
    context_data = json.dumps(ledger_result, default=str)
    
    user_prompt = f"Data for '{intent.value}' query:\n{context_data}\n\nWrite a short, friendly summary."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        response_stream = await client.chat.completions.create(
            model=_active_model,
            messages=messages,
            temperature=0.3,
            stream=True
        )

        narrative = ""
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                narrative += chunk.choices[0].delta.content
                
        # Remove deepseek reasoning tags
        narrative = re.sub(r'<think>.*?</think>', '', narrative, flags=re.DOTALL).strip()
        
        # Output is the original result + narrative message
        output = ledger_result.copy()
        output["message"] = narrative
        return output

    except Exception as e:
        print(f"Insight Agent Error: {e}")
        return ledger_result
