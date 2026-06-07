"""Unit tests: post-session persona hook (S2.6)."""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.persona_hook import (
    _append_body_delta,
    _merge_traits,
    _parse_llm_persona_response,
    run_persona_hook,
)

pytestmark = pytest.mark.unit


def test_merge_traits_rules_win_on_factual_fields() -> None:
    merged = _merge_traits(
        {"style": "conservative"},
        {"top_category": "Food", "style": "aggressive"},
        {"top_category": "Transport", "top_category_pct": 40.0},
    )
    assert merged["top_category"] == "Transport"
    assert merged["top_category_pct"] == 40.0
    assert merged["style"] == "aggressive"


def test_parse_llm_persona_response_valid_json() -> None:
    parsed = _parse_llm_persona_response('{"notes": "SIP-heavy", "traits": {"goals": "retirement"}}')
    assert parsed is not None
    assert parsed["notes"] == "SIP-heavy"
    assert parsed["traits"]["goals"] == "retirement"


def test_parse_llm_persona_response_invalid_json() -> None:
    assert _parse_llm_persona_response("not json") is None


def test_append_body_delta() -> None:
    result = _append_body_delta("Existing note.", "New insight.")
    assert "Existing note." in result
    assert "New insight." in result
    assert "---" in result


@pytest.mark.asyncio
async def test_run_persona_hook_rules_only() -> None:
    user_id = uuid4()
    session = AsyncMock()
    with (
        patch("app.services.persona_hook.derive_category_skew", new_callable=AsyncMock) as mock_skew,
        patch("app.services.persona_hook.get_persona", new_callable=AsyncMock) as mock_get,
        patch("app.services.persona_hook.upsert_persona", new_callable=AsyncMock) as mock_upsert,
        patch("app.services.persona_hook.get_llm_provider") as mock_provider,
        patch("app.services.persona_hook.chat_complete") as mock_chat,
    ):
        from app.services.llm_client import LLMProvider

        mock_skew.return_value = {
            "top_category": "Food",
            "top_category_pct": 42.0,
            "subscription_heavy": True,
        }
        mock_get.return_value = {"body": "", "traits": {}, "updated_at": None}
        mock_provider.return_value = LLMProvider.none

        await run_persona_hook(session, user_id, [{"role": "user", "content": "hi"}])

        mock_upsert.assert_awaited()
        call_kwargs = mock_upsert.await_args.kwargs
        assert call_kwargs["traits"]["top_category"] == "Food"
        mock_chat.assert_not_called()


@pytest.mark.asyncio
async def test_run_persona_hook_bad_llm_json_still_saves_rules() -> None:
    user_id = uuid4()
    session = AsyncMock()
    with (
        patch("app.services.persona_hook.derive_category_skew", new_callable=AsyncMock) as mock_skew,
        patch("app.services.persona_hook.get_persona", new_callable=AsyncMock) as mock_get,
        patch("app.services.persona_hook.upsert_persona", new_callable=AsyncMock) as mock_upsert,
        patch("app.services.persona_hook.get_llm_provider") as mock_provider,
        patch("app.services.persona_hook.chat_complete", return_value="garbage") as mock_chat,
    ):
        from app.services.llm_client import LLMProvider
        mock_skew.return_value = {"top_category": "Food", "top_category_pct": 30.0, "subscription_heavy": False}
        mock_get.return_value = {"body": "", "traits": {}, "updated_at": None}
        mock_provider.return_value = LLMProvider.openrouter

        await run_persona_hook(session, user_id, [])

        assert mock_upsert.await_count >= 1
        mock_chat.assert_called_once()


@pytest.mark.asyncio
async def test_run_persona_hook_valid_llm_delta() -> None:
    user_id = uuid4()
    session = AsyncMock()
    with (
        patch("app.services.persona_hook.derive_category_skew", new_callable=AsyncMock) as mock_skew,
        patch("app.services.persona_hook.get_persona", new_callable=AsyncMock) as mock_get,
        patch("app.services.persona_hook.upsert_persona", new_callable=AsyncMock) as mock_upsert,
        patch("app.services.persona_hook.get_llm_provider") as mock_provider,
        patch(
            "app.services.persona_hook.chat_complete",
            return_value='{"notes": "Prefers SIPs", "traits": {"tone": "calm"}}',
        ),
    ):
        from app.services.llm_client import LLMProvider
        mock_skew.return_value = {"top_category": None, "top_category_pct": 0.0, "subscription_heavy": False}
        mock_get.return_value = {"body": "Old", "traits": {}, "updated_at": None}
        mock_provider.return_value = LLMProvider.openrouter

        await run_persona_hook(session, user_id, [{"role": "user", "content": "record SIP"}])

        assert mock_upsert.await_count == 2
        final_kwargs = mock_upsert.await_args_list[-1].kwargs
        assert "Prefers SIPs" in final_kwargs["body"]
        assert final_kwargs["traits"]["tone"] == "calm"
