---
name: handoff
description: >-
  Orients agents with no chat history by reading persisted project context
  (same stores as domain-interview), recent git state, and active plans.
  Use when starting a new session, switching agents, the user says "handoff",
  "catch me up", "continue where we left off", or before picking up unfinished work.
---

# Agent Handoff

Skills do not persist memory — **files and git do**. Before acting, reconstruct what happened from the artifacts below. Do not guess from chat alone; the incoming agent has no prior turns.

**Companion skill:** [domain-interview](../domain-interview/SKILL.md) *writes* durable context; handoff *reads* it.

## When to run

| Trigger | Mode |
|---------|------|
| New session / new agent / "what happened?" | **Inbound** — read and summarize |
| End of a long session / before switching agents | **Outbound** — write a brief + flag doc gaps |
| User says "continue" on a specific feature | **Scoped** — inbound + filter to that area |

Pick a mode and tell the user which you are running.

## Inbound workflow

Copy this checklist and track progress:

```
Handoff progress:
- [ ] Read domain-interview stores (glossary, project context, decisions)
- [ ] Read architecture + drift + active plan docs
- [ ] Inspect git (branch, log, status, diff vs main)
- [ ] Note open questions and uncommitted work
- [ ] Produce handoff brief (template below)
- [ ] State assumptions and next safe action
```

### Step 1: Domain-interview stores (canonical memory)

Read in this order — same destinations as [domain-interview Step 4](../domain-interview/SKILL.md):

| Priority | File | What to extract |
|----------|------|-----------------|
| 1 | [docs/PROJECT_CONTEXT.md](../../../docs/PROJECT_CONTEXT.md) | Roadmap phase, priorities, non-goals, **Open questions**, recent interview rounds (dates + topics) |
| 2 | [docs/DOMAIN_GLOSSARY.md](../../../docs/DOMAIN_GLOSSARY.md) | Canonical terms for the area you will touch; **Related code** paths |
| 3 | [docs/decisions/](../../../docs/decisions/) | Accepted ADRs — especially money/ledger semantics |
| 4 | [.cursor/rules/](../../../.cursor/rules/) | Non-negotiable invariants (orchestrator, confirm-before-write) |

Skim only — do not reload full glossary on every handoff. Focus on sections matching git changes or the user's task.

### Step 2: Project-wide context

| File | When to read |
|------|--------------|
| [docs/AI_PRINCIPLES.md](../../../docs/AI_PRINCIPLES.md) | Always — architecture layers, confirm pattern, testing |
| [docs/DRIFT_AUDIT.md](../../../docs/DRIFT_AUDIT.md) | When touching ledger, spending, net worth, or UI labels |
| [docs/REGRESSION_TEST_PLAN.md](../../../docs/REGRESSION_TEST_PLAN.md) | When verifying or adding tests — find relevant REG-* IDs |
| [AGENTS.md](../../../AGENTS.md) | Key paths and skill index |

**Active feature plans** (read if git or user task touches that area):

| Plan | Path |
|------|------|
| Investments | [docs/INVESTMENT_ACCOUNTS_PLAN.md](../../../docs/INVESTMENT_ACCOUNTS_PLAN.md) |
| Phase overview | [docs/PHASES_OVERVIEW.md](../../../docs/PHASES_OVERVIEW.md) |
| Phase 1–5 | `docs/PHASE{N}_PLAN.md` |

### Step 3: Recent work (git)

Run in parallel:

```bash
git branch --show-current
git log --oneline -15
git status --short
git diff --stat
git diff main...HEAD --stat   # if not on main
```

From output, capture:

- **Branch** and whether it tracks remote
- **Last few commits** — what shipped vs WIP
- **Uncommitted files** — especially migrations, API, UI, e2e specs
- **Scope of diff** — which apps (`apps/api`, `apps/web`, `e2e`) changed

Do not assume committed work is deployed or tested.

### Step 4: Optional — prior agent session

If the user points to a transcript or says "previous chat":

- Agent transcripts live under the project's Cursor agent-transcripts folder (session UUID `.jsonl` files)
- Read the **last portion** of the relevant transcript for task-specific details not yet in docs
- Treat transcript content as **tentative** until it matches glossary, code, or git

### Step 5: Produce the handoff brief

Use [handoff-template.md](handoff-template.md). Deliver it to the user (or keep internal if they only asked you to catch up silently).

Rules:

- **Separate facts from inference** — label guesses clearly
- **Cite paths** — glossary terms, files, REG-* test IDs
- **Flag gaps** — decisions made in chat but not in PROJECT_CONTEXT or glossary
- **One next action** — smallest safe step that respects confirm-before-write and existing tests

## Outbound workflow (end of session)

Before ending a long or multi-agent session:

1. List decisions or terminology established **this session** not yet in docs
2. If canonical → prompt user: "Should I record this via domain-interview?" (do not silently rewrite glossary)
3. Append a short **Session note** to PROJECT_CONTEXT under Preferences → Interview cadence *only if user confirms*
4. Leave a handoff brief in chat using the template so the next agent can start at Step 1

## Scoped handoff (feature area)

When the user names a feature (e.g. "accounts", "investments", "themes"):

1. Grep glossary + PROJECT_CONTEXT for that topic
2. `git diff --stat -- 'apps/**/<area>'` or relevant paths
3. Read matching plan doc section + REG-* tests in regression plan
4. Brief covers **only that slice** — still mention global invariants from AI_PRINCIPLES

## Conflict resolution

If git, docs, and code disagree:

| Source wins for… | Authority |
|------------------|-----------|
| Money math, nw_impact, balances | Code + glossary + ADRs — fix drift, don't guess |
| Owner intent, naming, priorities | Glossary + PROJECT_CONTEXT — ask user if stale |
| Session-only chat claims | Nowhere — verify or ask |

Use domain-interview **Audit mode** when drift is material; do not patch around silent mismatches.

## Anti-patterns

- Starting implementation without reading PROJECT_CONTEXT open questions
- Duplicating AI_PRINCIPLES into the handoff brief
- Treating uncommitted diff as finished or tested
- Ignoring `nw_impact` / confirm-card invariants when summarizing "what's done"

## Additional resources

- Handoff output format: [handoff-template.md](handoff-template.md)
- How context gets written: [domain-interview/SKILL.md](../domain-interview/SKILL.md)
- Glossary entry format: [domain-interview/entry-template.md](../domain-interview/entry-template.md)
