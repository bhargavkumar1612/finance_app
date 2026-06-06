import logging
import traceback
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.orchestrator import run as orchestrator_run
from app.core.schemas import AgentResponse
from app.db import get_async_session, User, ChatSession, ChatMessage

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: AgentResponse
    conversation_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ChatResponse:
    """Chat with the finance copilot. Uses Planner -> Ledger -> structured AgentResponse."""
    conversation_id = body.conversation_id or str(uuid4())
    try:
        response = await orchestrator_run(
            session,
            body.message,
            conversation_id,
            user.id,
        )
        return ChatResponse(response=response, conversation_id=conversation_id)
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Unhandled error in chat orchestrator: {error_msg}\n{traceback.format_exc()}")
        fallback_response = AgentResponse(
            status="error",
            data={"message": f"Internal Server Error: {error_msg}"},
            confidence=0.0,
            next_suggested_actions=["Add an expense", "What's my net worth?"],
            ui_type="message_only",
            card_payload={"message": f"Internal Server Error: {error_msg}"}
        )
        return ChatResponse(response=fallback_response, conversation_id=conversation_id)


class SessionSummaryResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class UpdateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


async def _get_owned_session(
    db: AsyncSession, user_id: UUID, session_id: str
) -> ChatSession:
    try:
        session_uuid = UUID(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid session id") from e
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_uuid,
            ChatSession.user_id == user_id,
        )
    )
    chat_session = result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return chat_session


@router.get("/chat/sessions", response_model=list[SessionSummaryResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    try:
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(func.coalesce(ChatSession.updated_at, ChatSession.created_at).desc())
        )
        rows = result.scalars().all()
        return [
            SessionSummaryResponse(
                id=str(r.id),
                title=r.title or "Chat",
                created_at=r.created_at,
                updated_at=r.updated_at or r.created_at,
            )
            for r in rows
        ]
    except Exception as e:
        logging.error("list_sessions failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Could not load chat sessions: {e}") from e


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    text: str
    agent_response: dict | None = None
    created_at: datetime


@router.patch("/chat/sessions/{session_id}", response_model=SessionSummaryResponse)
async def rename_session(
    session_id: str,
    body: UpdateSessionRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    chat_session = await _get_owned_session(session, user.id, session_id)
    chat_session.title = body.title.strip()
    chat_session.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(chat_session)
    return SessionSummaryResponse(
        id=str(chat_session.id),
        title=chat_session.title,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at or chat_session.created_at,
    )


@router.delete("/chat/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    chat_session = await _get_owned_session(session, user.id, session_id)
    await session.delete(chat_session)
    await session.commit()


@router.get("/chat/sessions/{session_id}", response_model=list[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    chat_session = await _get_owned_session(session, user.id, session_id)
    session_uuid = chat_session.id

    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_uuid)
        .order_by(ChatMessage.created_at.asc())
    )
    rows = result.scalars().all()
    return [
        ChatMessageResponse(
            id=str(r.id),
            role=r.role,
            text=r.text,
            agent_response=r.agent_response,
            created_at=r.created_at
        )
        for r in rows
    ]
