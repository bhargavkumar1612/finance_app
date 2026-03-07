"""
Redis-backed conversation state for Phase 1.
Key: conv:{conversation_id}, TTL 24h, refresh on each set_state.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings
from app.core.schemas import ConversationState

_KEY_PREFIX = "conv:"
_DEFAULT_TTL = 86400  # 24 hours


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def get_state(conversation_id: str) -> Optional[ConversationState]:
    if not conversation_id:
        return None
    client = _redis()
    try:
        key = f"{_KEY_PREFIX}{conversation_id}"
        raw = await client.get(key)
        if not raw:
            return None
        data = json.loads(raw)
        return ConversationState(**data)
    finally:
        await client.aclose()


async def set_state(
    conversation_id: str,
    state: ConversationState,
    ttl_seconds: int = _DEFAULT_TTL,
) -> None:
    if not conversation_id:
        return
    state.conversation_id = conversation_id
    state.updated_at = datetime.now(timezone.utc).isoformat()
    client = _redis()
    try:
        key = f"{_KEY_PREFIX}{conversation_id}"
        await client.setex(key, ttl_seconds, state.model_dump_json())
    finally:
        await client.aclose()
