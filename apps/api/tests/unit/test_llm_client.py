"""Unit tests for optional LLM client (mocked OpenAI SDK)."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.llm_settings import clear_llm_settings_cache
from app.services.llm_client import chat_complete, clear_llm_caches, get_llm_provider

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_llm_cache() -> None:
    clear_llm_caches()
    clear_llm_settings_cache()
    yield
    clear_llm_caches()
    clear_llm_settings_cache()


def test_chat_complete_returns_none_when_provider_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "none")
    clear_llm_settings_cache()
    assert chat_complete([{"role": "user", "content": "hi"}]) is None


def test_chat_complete_openrouter_uses_mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    clear_llm_settings_cache()

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="  Four.  "))]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    with patch("app.services.llm_client.get_openai_client", return_value=mock_client):
        out = chat_complete([{"role": "user", "content": "2+2?"}], temperature=0.1, max_tokens=50)
    assert out == "Four."
    mock_client.chat.completions.create.assert_called_once()
    call_kw = mock_client.chat.completions.create.call_args.kwargs
    assert call_kw["model"] == "openai/gpt-4o-mini"
    assert call_kw["messages"][0]["content"] == "2+2?"


def test_get_llm_provider_invalid_falls_back_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "not-a-real-provider")
    clear_llm_settings_cache()
    assert get_llm_provider().value == "none"
