# Agent instructions — Finance Copilot

Guidance for humans and coding agents working in this repository.

## Must-read

- **[docs/AI_PRINCIPLES.md](docs/AI_PRINCIPLES.md)** — architecture, schemas, finance safety, testing, MVP order
- **[docs/DOMAIN_GLOSSARY.md](docs/DOMAIN_GLOSSARY.md)** — shared vocabulary (owner language ↔ code)
- **[docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)** — priorities, mental model, open questions
- **[docs/LLM_SETUP.md](docs/LLM_SETUP.md)** — optional OpenRouter / Ollama configuration
- **[docs/REGRESSION_TEST_PLAN.md](docs/REGRESSION_TEST_PLAN.md)** — A–Z regression scenarios for QA agents
- **[README.md](README.md)** — run locally or with Docker

## Skills

| Skill | Path | Use when |
|-------|------|----------|
| Domain interview | [`.cursor/skills/domain-interview/`](.cursor/skills/domain-interview/SKILL.md) | Terminology unclear, before major features, or when the owner asks to "grill me" / capture context |

Drift tracking: [docs/DRIFT_AUDIT.md](docs/DRIFT_AUDIT.md)

## Cursor rules

Persistent rules live in [`.cursor/rules/`](.cursor/rules/):

| Rule | Scope |
|------|--------|
| `ai-application.mdc` | Always apply — layers, contracts, LLM, confirm-before-write |
| `ai-agents-and-chat.mdc` | `apps/api/app/agents/`, orchestrator, schemas, chat API, LLM client |

## One-line summary

Deterministic orchestrator, typed `AgentResponse`, Ledger for facts and writes, LLM for language/routing only, Redis conversation state, confirm before mutating money, fallbacks when the model is off.

## Key paths

| Area | Path |
|------|------|
| Orchestrator | `apps/api/app/core/orchestrator.py` |
| Schemas | `apps/api/app/core/schemas.py` |
| Planner | `apps/api/app/agents/planner.py` |
| Ledger | `apps/api/app/agents/ledger_agent.py` |
| Chat API | `apps/api/app/api/chat.py` |
| Frontend state machine | `apps/web/lib/chatMachine.ts` |
| E2E tests | `e2e/specs/` |
