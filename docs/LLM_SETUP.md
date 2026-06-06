# Optional LLM (OpenRouter / Ollama)

Settings live in [`app/core/llm_settings.py`](../app/core/llm_settings.py) (`LLMSettings`); the client is [`app/services/llm_client.py`](../app/services/llm_client.py).

## Environment variables

Add to `.env` (never commit real keys):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `none` | `none` \| `openrouter` \| `ollama` |
| `OPENROUTER_API_KEY` | (empty) | Inference key from [OpenRouter](https://openrouter.ai/) |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API root; must resolve to a URL ending in `/v1` once normalized |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | Model slug from [OpenRouter models](https://openrouter.ai/models) |
| `OPENROUTER_HTTP_REFERER` | (empty) | Optional site URL for OpenRouter |
| `OPENROUTER_X_TITLE` | `Finance Copilot` | Optional app title header |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama host |
| `OLLAMA_MODEL` | `llama3.2` | Pulled Ollama model name |

## Recommended models (OpenRouter)

- **Default in code:** `openai/gpt-4o-mini` — good instruction following for short narratives; verify current pricing on OpenRouter.
- **Free tier:** browse [free text models](https://openrouter.ai/models?max_price=0&output_modalities=text); slugs change, pick an active `:free` model if needed.

## Docker

Pass the same variables into the `api` service `environment` block (or extend `env_file`) so containers can call the LLM when enabled.

Example fragment for `docker-compose.yml` under `api`:

```yaml
environment:
  LLM_PROVIDER: ${LLM_PROVIDER:-none}
  OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}
  OPENROUTER_BASE_URL: ${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
  OPENROUTER_MODEL: ${OPENROUTER_MODEL:-openai/gpt-4o-mini}
  OPENROUTER_HTTP_REFERER: ${OPENROUTER_HTTP_REFERER:-}
  OPENROUTER_X_TITLE: ${OPENROUTER_X_TITLE:-Finance Copilot}
  OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://localhost:11434}
  OLLAMA_MODEL: ${OLLAMA_MODEL:-llama3.2}
```

Copy the same keys into `.env.example` (with empty `OPENROUTER_API_KEY=`) so teammates know what exists.

## Single `Settings` class (optional)

LLM options are isolated in `LLMSettings` so they work without touching `app/core/config.py`. If you prefer one `Settings` object, duplicate these fields onto your main `Settings` and switch `llm_client` to read from `get_settings()` instead of `get_llm_settings()`.

## Run API + frontend (Docker) with OpenRouter

Put in `.env` (do not paste keys into shell history):

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

Then:

```bash
docker compose up --build
```

- Frontend: http://localhost:3000  
- API: http://localhost:8000  

The `api` service receives the same variables via `docker-compose.yml`. For **Ollama on your host** from inside Docker, the default `OLLAMA_BASE_URL` uses `host.docker.internal` (works with Docker Desktop and `extra_hosts: host-gateway` on Linux).

## Smoke test

```bash
# From repo root, with dependencies installed
LLM_PROVIDER=openrouter OPENROUTER_API_KEY=your_key python scripts/test_llm.py
```

## Tests

`pytest tests/test_llm_client.py` — mocks the OpenAI client; no network or API key required.
