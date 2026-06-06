"""
Orchestrator: load state -> Plan -> run Ledger steps -> build AgentResponse -> save state.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.ledger_agent import run as ledger_run, LedgerError
from app.agents.insight_agent import run as insight_run
from app.agents.ui_guide import build_ui_guide
from app.agents.planner import plan
from app.core.schemas import (
    AgentResponse,
    ConversationState,
    Intent,
    PlannerOutput,
)
from app.core.pending_mutation import (
    MUTATION_ACTIONS,
    commit_action_for,
    is_confirm_message,
    is_reject_message,
    propose_action_for,
)
from app.core.state_manager import get_state, set_state
from app.db.models import Account, ChatSession, ChatMessage


# Next suggested actions per intent
_NEXT_ACTIONS = {
    Intent.add_expense: ["Confirm", "Cancel", "View this month's spending"],
    Intent.add_income: ["Confirm", "Cancel", "What's my net worth?"],
    Intent.net_worth_query: ["Add an expense", "Spending breakdown", "Import statement"],
    Intent.spending_analysis: [
        "Pie chart for this month",
        "Last 12 months spending dashboard",
        "What's my net worth?",
    ],
    Intent.affordability_check: ["What's my net worth?", "Spending breakdown", "Add an expense"],
    Intent.import_statement: ["Import CSV", "Add expense manually", "View transactions"],
    Intent.unknown: ["Add an expense", "What's my net worth?", "Where did I spend this month?"],
    Intent.analyze_category_spending: ["Spending breakdown", "What's my net worth?"],
    Intent.track_subscriptions: ["Add recurring bill", "Spending breakdown"],
    Intent.list_recurring_bills: ["Add recurring bill", "Spending breakdown"],
    Intent.analyze_cash_flow: ["What's my net worth?", "Spending breakdown"],
    Intent.get_top_expenses: ["Spending breakdown", "What's my net worth?"],
    Intent.budget_vs_actual: ["Add an expense", "Spending breakdown"],
    Intent.project_future_balance: ["What's my net worth?", "Spending breakdown"],
    Intent.debt_payoff_planner: ["What's my net worth?", "Spending breakdown"],
    Intent.investment_allocation: ["What's my net worth?", "Spending breakdown"],
    Intent.vendor_spending_history: ["Spending breakdown", "What's my net worth?"],
    Intent.unusual_spending_alert: ["Spending breakdown", "What's my net worth?"],
    Intent.manage_accounts: ["List my accounts", "Add a bank account", "View transactions"],
}


async def _get_or_create_chat_session(session: AsyncSession, conversation_id: str, user_id: UUID, initial_message: str) -> UUID:
    try:
        session_uuid = UUID(conversation_id)
    except ValueError:
        session_uuid = None
        
    if session_uuid:
        result = await session.execute(
            select(ChatSession).where(ChatSession.id == session_uuid, ChatSession.user_id == user_id)
        )
        chat_session = result.scalar_one_or_none()
        if chat_session:
            return chat_session.id
            
    # Need to create it. Use first 30 chars of msg as title
    title = initial_message[:30] + "..." if len(initial_message) > 30 else initial_message
    
    new_session = ChatSession(
        id=session_uuid if session_uuid else None, # type: ignore
        user_id=user_id,
        title=title
    )
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    return new_session.id


async def run(
    session: AsyncSession,
    message: str,
    conversation_id: str,
    user_id: UUID,
) -> AgentResponse:
    # 1. DB Session Management
    db_session_id = await _get_or_create_chat_session(session, conversation_id, user_id, message)
    conversation_id = str(db_session_id)
    
    user_msg_record = ChatMessage(
        session_id=db_session_id,
        role="user",
        text=message
    )
    session.add(user_msg_record)
    await session.execute(
        update(ChatSession)
        .where(ChatSession.id == db_session_id)
        .values(updated_at=datetime.utcnow())
    )
    await session.commit()
    
    # 2. Redis Short-term State (Slots)
    state = await get_state(conversation_id)
    if state is None:
        state = ConversationState(
            conversation_id=conversation_id,
            current_step="",
            filled_slots={},
            agent_history=[],
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
    # Append the current message to history for the planner context
    state.agent_history.append({"role": "user", "content": message})

    default_account_id = await _get_default_account_id(session, user_id)
    pending = state.filled_slots.get("pending_mutation")

    if pending:
        if is_confirm_message(message):
            commit_action = commit_action_for(pending.get("action", ""))
            try:
                last_result = await ledger_run(
                    session,
                    user_id,
                    commit_action,
                    pending.get("params", {}),
                    default_account_id=default_account_id,
                )
            except LedgerError as e:
                res = AgentResponse(
                    status="error",
                    data={"message": e.message, "error": e.message},
                    confidence=0.0,
                    next_suggested_actions=_NEXT_ACTIONS[Intent.unknown],
                    ui_type="message_only",
                    card_payload={"message": e.message},
                )
                await _save_assistant_response(session, db_session_id, res, state)
                return res
            state.filled_slots.pop("pending_mutation", None)
            intent_val = pending.get("intent", Intent.add_expense.value)
            try:
                intent = Intent(intent_val)
            except ValueError:
                intent = Intent.add_expense
            ui_type, card_payload, chat_summary = build_ui_guide(intent, last_result)
            card_payload = {**card_payload, "committed": True, "preview": False}
            res = AgentResponse(
                status="success",
                data={"message": chat_summary, **last_result},
                confidence=1.0,
                next_suggested_actions=_NEXT_ACTIONS.get(intent, _NEXT_ACTIONS[Intent.unknown]),
                ui_type=ui_type,
                card_payload=card_payload,
            )
            await _save_assistant_response(session, db_session_id, res, state)
            return res
        if is_reject_message(message):
            state.filled_slots.pop("pending_mutation", None)
            msg = "Cancelled — no changes saved."
            res = AgentResponse(
                status="success",
                data={"message": msg},
                confidence=1.0,
                next_suggested_actions=_NEXT_ACTIONS[Intent.unknown],
                ui_type="message_only",
                card_payload={"message": msg},
            )
            await _save_assistant_response(session, db_session_id, res, state)
            return res

    planner_output = await plan(message, state)
    state.current_step = planner_output.intent.value
    state.updated_at = datetime.now(timezone.utc).isoformat()

    last_result = {}

    for step in planner_output.steps:
        if step.agent != "ledger":
            continue
        action = step.action
        if action in MUTATION_ACTIONS:
            action = propose_action_for(action)
        try:
            result = await ledger_run(
                session,
                user_id,
                action,
                step.params,
                default_account_id=default_account_id,
            )
            last_result = result
        except LedgerError as e:
            msg = f"Wait, {e.message}"
            res = AgentResponse(
                status="error",
                data={"message": msg, "error": e.message, "intent": planner_output.intent.value},
                confidence=0.0,
                next_suggested_actions=_NEXT_ACTIONS.get(planner_output.intent, _NEXT_ACTIONS[Intent.unknown]),
                ui_type="message_only",
                card_payload={"message": msg},
            )
            await _save_assistant_response(session, db_session_id, res, state)
            return res
        except Exception as e:
            msg = f"An unexpected error occurred: {str(e)}"
            res = AgentResponse(
                status="error",
                data={"message": msg, "error": str(e), "intent": planner_output.intent.value},
                confidence=0.0,
                next_suggested_actions=_NEXT_ACTIONS[Intent.unknown],
                ui_type="message_only",
                card_payload={"message": msg},
            )
            await _save_assistant_response(session, db_session_id, res, state)
            return res

        if last_result.get("preview") and step.action in MUTATION_ACTIONS:
            state.filled_slots["pending_mutation"] = {
                "action": propose_action_for(step.action),
                "params": {
                    "amount": last_result.get("amount"),
                    "merchant": last_result.get("merchant"),
                    "category": last_result.get("category"),
                    "transaction_date": last_result.get("transaction_date"),
                    "account_id": last_result.get("account_id"),
                    "nw_impact": last_result.get("nw_impact"),
                },
                "intent": planner_output.intent.value,
            }
            ui_type, card_payload, chat_summary = build_ui_guide(planner_output.intent, last_result)
            card_payload = {**card_payload, "committed": False, "preview": True}
            res = AgentResponse(
                status="confirm",
                data={"message": last_result.get("summary", chat_summary), **last_result},
                confidence=1.0,
                next_suggested_actions=["Confirm", "Cancel"],
                ui_type=ui_type,
                card_payload=card_payload,
            )
            await _save_assistant_response(session, db_session_id, res, state)
            return res
            
    # Phase 4: Generate LLM Insights if intent matches
    last_result = await insight_run(session, user_id, planner_output.intent, last_result)
            
    if planner_output.intent == Intent.unknown:
        if planner_output.message:
            ui_type = "message_only"
            card_payload = {"message": planner_output.message}
            chat_summary = planner_output.message
        else:
            ui_type, card_payload, chat_summary = build_ui_guide(Intent.unknown, last_result)
            
        res = AgentResponse(
            status="success",
            data={"message": chat_summary},
            confidence=0.0,
            next_suggested_actions=_NEXT_ACTIONS[Intent.unknown],
            ui_type=ui_type,
            card_payload=card_payload,
        )
        await _save_assistant_response(session, db_session_id, res, state)
        return res
        
    if planner_output.intent == Intent.import_statement:
        msg = "Use the Import tab to upload a CSV or PDF bank statement."
        ui_type, card_payload, chat_summary = build_ui_guide(Intent.import_statement, {"message": msg})
        res = AgentResponse(
            status="success",
            data={"message": chat_summary},
            confidence=1.0,
            next_suggested_actions=_NEXT_ACTIONS[Intent.import_statement],
            ui_type=ui_type,
            card_payload=card_payload,
        )
        await _save_assistant_response(session, db_session_id, res, state)
        return res

    # Call UI Guide to enrich response with ui_type, card_payload, chat_summary
    ui_type, card_payload, chat_summary = build_ui_guide(planner_output.intent, last_result)
    response_data = {"message": chat_summary, **last_result}
    
    from app.services.missing_data import check_missing_data
    hints = await check_missing_data(session, user_id)
    suggested_actions = hints + _NEXT_ACTIONS.get(planner_output.intent, _NEXT_ACTIONS[Intent.unknown])
    
    res = AgentResponse(
        status="success",
        data=response_data,
        confidence=1.0,
        next_suggested_actions=suggested_actions,
        ui_type=ui_type,
        card_payload=card_payload,
    )
    await _save_assistant_response(session, db_session_id, res, state)
    return res


async def _save_assistant_response(session: AsyncSession, db_session_id: UUID, res: AgentResponse, state: ConversationState):
    """Helper to save the final agent output to Postgres and Redis."""
    chat_summary = res.data.get("message", "Done.")
    
    # 1. DB Save
    agent_msg_record = ChatMessage(
        session_id=db_session_id,
        role="assistant",
        text=chat_summary,
        agent_response=res.model_dump()
    )
    session.add(agent_msg_record)
    await session.execute(
        update(ChatSession)
        .where(ChatSession.id == db_session_id)
        .values(updated_at=datetime.utcnow())
    )
    await session.commit()
    
    # 2. Redis Save
    state.agent_history.append({"role": "assistant", "content": chat_summary})
    await set_state(str(db_session_id), state)


async def _get_default_account_id(session: AsyncSession, user_id: UUID) -> UUID | None:
    result = await session.execute(
        select(Account.id).where(Account.user_id == user_id).limit(1)
    )
    row = result.first()
    return row[0] if row else None


def _summary(intent: Intent, result: dict) -> str:
    if intent == Intent.add_expense and result.get("summary"):
        return result["summary"]
    if intent == Intent.net_worth_query:
        nw = result.get("net_worth", 0)
        return f"Your net worth is ₹{nw:,.2f} (assets − liabilities)."
    if intent == Intent.spending_analysis:
        total = result.get("total_spend", 0)
        return f"You spent ₹{total:,.2f} in the period. Check 'by_category' for breakdown."
    if intent == Intent.affordability_check:
        return result.get("message", "Affordability estimate ready.")
    return result.get("message", "Done.")
