"""LLM-related settings (OpenRouter / Ollama). Loaded from environment with pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "none"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_http_referer: str = ""
    openrouter_x_title: str = "Finance Copilot"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    # auto: LLM for multi-turn / complex context; keywords for simple one-shot commands
    # always: LLM routes every message when provider is enabled
    # keywords_only: never call LLM planner (semantic + keywords only; LLM_PROVIDER=none behavior for routing)
    llm_planner_mode: str = "auto"


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    return LLMSettings()


def clear_llm_settings_cache() -> None:
    get_llm_settings.cache_clear()
