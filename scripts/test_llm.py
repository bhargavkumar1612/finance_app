#!/usr/bin/env python3
"""Smoke test optional LLM (OpenRouter or Ollama) via app.services.llm_client.

Run from repo root with venv active:
  LLM_PROVIDER=openrouter OPENROUTER_API_KEY=sk-or-v1-... python scripts/test_llm.py
  LLM_PROVIDER=ollama OLLAMA_BASE_URL=http://localhost:11434 python scripts/test_llm.py

Requires: pip install openai pydantic-settings (same as app).
"""
from __future__ import annotations

import os
import sys

# Repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.llm_settings import clear_llm_settings_cache
from app.services.llm_client import chat_complete, clear_llm_caches, get_chat_model, get_llm_provider


def main() -> int:
    clear_llm_caches()
    clear_llm_settings_cache()
    provider = get_llm_provider()
    model = get_chat_model()
    print(f"provider={provider.value} model={model!r}")
    if provider.value == "none":
        print("Set LLM_PROVIDER=openrouter or ollama and required API vars.")
        return 1
    text = chat_complete(
        [{"role": "user", "content": "Reply in one short sentence: what is 2 + 2?"}],
        max_tokens=128,
    )
    if text is None:
        print("chat_complete returned None (missing API key or model).")
        return 1
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
