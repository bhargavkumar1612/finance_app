"""
Optional LLM client: OpenRouter (OpenAI-compatible) or Ollama.

Settings come from app.core.llm_settings (env). Never commit API keys.
Math/ledger stay deterministic elsewhere.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from openai import AsyncOpenAI, OpenAI

from app.core.llm_settings import clear_llm_settings_cache, get_llm_settings


class LLMProvider(str, Enum):
    none = "none"
    openrouter = "openrouter"
    ollama = "ollama"


class LLMPlannerMode(str, Enum):
    auto = "auto"
    always = "always"
    keywords_only = "keywords_only"


def _normalize_openrouter_base_url(url: str) -> str:
    """
    OpenAI SDK expects base_url ending with /v1 exactly once.
    Accepts https://openrouter.ai/api/v1, .../api, or .../api/v1/.
    """
    base = url.strip().rstrip("/")
    if base.endswith("/v1"):
        return base
    if base.endswith("/api"):
        return f"{base}/v1"
    return f"{base}/v1"


def get_llm_provider() -> LLMProvider:
    raw = get_llm_settings().llm_provider.strip().lower()
    try:
        return LLMProvider(raw)
    except ValueError:
        return LLMProvider.none


def get_llm_planner_mode() -> LLMPlannerMode:
    raw = get_llm_settings().llm_planner_mode.strip().lower()
    try:
        return LLMPlannerMode(raw)
    except ValueError:
        return LLMPlannerMode.auto


def _openrouter_default_headers() -> dict[str, str] | None:
    if get_llm_provider() != LLMProvider.openrouter:
        return None
    s = get_llm_settings()
    out: dict[str, str] = {}
    site = (s.openrouter_http_referer or "").strip()
    title = (s.openrouter_x_title or "Finance Copilot").strip()
    if site:
        out["HTTP-Referer"] = site
    if title:
        out["X-Title"] = title
    return out or None


def try_get_env_async_client_and_model() -> tuple[AsyncOpenAI, str] | None:
    """
    When LLM_PROVIDER is openrouter or ollama and credentials are set, return (AsyncOpenAI, model_id).
    Otherwise None (caller may fall back to llms.json or local defaults).
    """
    s = get_llm_settings()
    provider = get_llm_provider()
    model = get_chat_model()
    if not model:
        return None
    headers = _openrouter_default_headers()
    kwargs: dict[str, Any] = {}
    if headers:
        kwargs["default_headers"] = headers

    if provider == LLMProvider.openrouter:
        api_key = (s.openrouter_api_key or "").strip()
        if not api_key:
            return None
        base_url = _normalize_openrouter_base_url(
            s.openrouter_base_url or "https://openrouter.ai/api/v1"
        )
        return AsyncOpenAI(base_url=base_url, api_key=api_key, **kwargs), model
    if provider == LLMProvider.ollama:
        host = (s.ollama_base_url or "http://localhost:11434").rstrip("/")
        return AsyncOpenAI(base_url=f"{host}/v1", api_key="ollama", **kwargs), model
    return None


def get_openai_client() -> OpenAI | None:
    """Return configured OpenAI-compatible client, or None if LLM_PROVIDER=none."""
    s = get_llm_settings()
    provider = get_llm_provider()
    if provider == LLMProvider.none:
        return None
    if provider == LLMProvider.openrouter:
        api_key = (s.openrouter_api_key or "").strip()
        if not api_key:
            return None
        base_url = _normalize_openrouter_base_url(
            s.openrouter_base_url or "https://openrouter.ai/api/v1"
        )
        return OpenAI(base_url=base_url, api_key=api_key)
    if provider == LLMProvider.ollama:
        host = (s.ollama_base_url or "http://localhost:11434").rstrip("/")
        return OpenAI(base_url=f"{host}/v1", api_key="ollama")
    return None


def get_chat_model() -> str:
    """Model id for chat.completions (provider-specific slug)."""
    s = get_llm_settings()
    provider = get_llm_provider()
    if provider == LLMProvider.openrouter:
        return (s.openrouter_model or "openai/gpt-4o-mini").strip()
    if provider == LLMProvider.ollama:
        return (s.ollama_model or "llama3.2").strip()
    return ""


def chat_complete(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str | None:
    """
    Single non-streaming completion. Returns assistant text or None if LLM disabled/unconfigured.
    """
    client = get_openai_client()
    model = get_chat_model()
    if client is None or not model:
        return None
    extra_headers = _openrouter_default_headers()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra_headers:
        kwargs["extra_headers"] = extra_headers
    resp = client.chat.completions.create(**kwargs)
    choice = resp.choices[0] if resp.choices else None
    if not choice or not choice.message or not choice.message.content:
        return None
    return choice.message.content.strip()


def clear_llm_caches() -> None:
    """Clear cached LLM settings (for tests after env change)."""
    clear_llm_settings_cache()
