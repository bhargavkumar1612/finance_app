from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
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
    response = await orchestrator_run(
        session,
        body.message,
        conversation_id,
        user.id,
    )
    return ChatResponse(response=response, conversation_id=conversation_id)


class SessionSummaryResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


@router.get("/chat/sessions", response_model=list[SessionSummaryResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    rows = result.scalars().all()
    return [
        SessionSummaryResponse(
            id=str(r.id),
            title=r.title,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in rows
    ]


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    text: str
    agent_response: dict | None = None
    created_at: datetime


@router.get("/chat/sessions/{session_id}", response_model=list[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Verify owner
    res = await session.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    chat_session = res.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
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
