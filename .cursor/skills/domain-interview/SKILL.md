---
name: domain-interview
description: >-
  Interviews the project owner on ambiguous domain terms, naming, priorities,
  and mental models; records answers in docs/DOMAIN_GLOSSARY.md and
  docs/PROJECT_CONTEXT.md; maps terms to code locations. Use when starting
  work on unfamiliar areas, when terminology is inconsistent, when the user
  says "grill me", "capture context", or "align vocabulary", or before major
  features.
---

# Domain Interview

Bridge the gap between the owner's language and this codebase. Skills do not persist memory — **files do**. After every interview, write durable answers to the docs below.

## Before you start

1. Read [docs/DOMAIN_GLOSSARY.md](../../../docs/DOMAIN_GLOSSARY.md) and [docs/PROJECT_CONTEXT.md](../../../docs/PROJECT_CONTEXT.md).
2. Scan relevant code for terms missing from the glossary or that conflict with recorded answers.
3. Read [docs/AI_PRINCIPLES.md](../../../docs/AI_PRINCIPLES.md) for architecture — do not duplicate it in the glossary.

## Session modes

| Mode | When | Goal |
|------|------|------|
| **Onboarding** | First pass or new contributor | Broad terms, priorities, non-goals |
| **Feature deep-dive** | Before a major feature | Narrow questions on one area |
| **Audit** | Periodic or after drift | Resolve doc/code mismatches and open questions |

Pick one mode and tell the user which you are running.

## Interview workflow

Copy this checklist and track progress:

```
Interview progress:
- [ ] Read existing glossary and project context
- [ ] List unknowns / conflicts (max 5–7 per round)
- [ ] Ask focused questions (one topic at a time)
- [ ] Confirm answers with the user before writing
- [ ] Record to docs using entry-template
- [ ] Update open questions backlog
- [ ] Link AGENTS.md / rules only if a rule must always apply
```

### Step 1: Find gaps

Look for:
- Terms in code, UI, or chat that are not in `DOMAIN_GLOSSARY.md`
- Same concept named differently in docs vs code vs UI
- Behavior the code implies but docs never define
- Items in **Open questions** in `PROJECT_CONTEXT.md`

### Step 2: Ask (grill, don't guess)

Use [question-bank.md](question-bank.md). Rules:
- **Max 5–7 questions per round** — avoid overwhelming the owner
- **One concept per question** — offer concrete options when helpful
- **Cite evidence** — "In `ledger_agent.py` we sum X; in chat you say Y — which is correct?"
- **Never assume** — if unsure, ask; do not silently pick an interpretation

### Step 3: Confirm before recording

Summarize each answer in one sentence and ask: "Should I record this as canonical?"

If an answer **contradicts** existing docs or code, stop and ask which wins:
- Update glossary and code
- Update glossary and docs only
- Defer (add to open questions)

### Step 4: Record answers

Write to the correct artifact:

| Answer type | Destination |
|-------------|-------------|
| Term, naming, synonyms, code mapping | `docs/DOMAIN_GLOSSARY.md` |
| Priorities, mental model, non-goals, preferences | `docs/PROJECT_CONTEXT.md` |
| Architectural "why" with tradeoffs | `docs/decisions/NNN-short-title.md` (create if needed) |
| Always-on agent behavior (short) | `.cursor/rules/` — only distilled invariants |
| Session-only or tentative | Do not persist — keep in chat |

Use [entry-template.md](entry-template.md) for glossary entries.

Every glossary entry must include **Related code** paths.

### Step 5: Apply shared language

When writing docs, UI copy, commits, or code after an interview:
- Prefer **canonical names** from the glossary
- Avoid **synonyms marked deprecated** in the glossary
- If you must introduce a new term, add it to open questions or ask in the next interview round

## Promotion rules

- Glossary = **what words mean** and **where they live in code**
- `AI_PRINCIPLES.md` = **how the app is built** — do not merge the two
- Cursor rules = **non-negotiable behavior** — promote only stable, short rules
- Do not create empty ADRs — one decision per file when the "why" matters

## Drift audit (Audit mode)

1. Compare glossary terms to identifiers in `app/core/schemas.py`, API routes, and UI labels
2. List mismatches as a table: Term | Glossary | Code/UI | Action needed
3. Interview the owner on each mismatch
4. Update glossary or file a code/doc fix — never leave silent drift

## Example question (Finance Copilot)

> You use "spending" in chat suggestions and `spending_analysis` in the planner. Should **spending** include credit-card payments that pay off prior charges, or only new outflows? Where should refunds appear?

After the answer, record under `### Spending` in `DOMAIN_GLOSSARY.md` with links to `ledger_agent.py` and relevant intents.

## Additional resources

- Question categories: [question-bank.md](question-bank.md)
- Glossary entry format: [entry-template.md](entry-template.md)
- Architecture (read-only context): [docs/AI_PRINCIPLES.md](../../../docs/AI_PRINCIPLES.md)
- Incoming agents without chat history: [handoff skill](../handoff/SKILL.md)
