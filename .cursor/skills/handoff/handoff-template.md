# Handoff brief template

Copy into chat (or a scratch file). Replace bracketed placeholders. Delete sections that are N/A.

```markdown
# Handoff — [YYYY-MM-DD] — [branch or task name]

## Executive summary
[2–4 sentences: what this repo is doing right now, what phase, what the immediate task is]

## Canonical context (from docs)
| Source | Key points |
|--------|------------|
| PROJECT_CONTEXT | [phase, priorities, last interview round] |
| DOMAIN_GLOSSARY | [terms that matter for this task + Related code paths] |
| ADRs | [docs/decisions/* if relevant] |
| Active plan | [INVESTMENT_ACCOUNTS_PLAN / PHASE*_PLAN section] |

## Recent work (from git)
- **Branch:** `...`
- **Recent commits:** `abc1234` — …; `def5678` — …
- **Uncommitted:** [file areas — api / web / e2e / migrations]
- **Diff scope:** [one line — e.g. "account balances + settings theme UI"]

## What appears done
- [ ] …
- [ ] …

## What appears in progress / WIP
- [ ] …

## Open questions (from PROJECT_CONTEXT + session)
| Topic | Status | Blocker? |
|-------|--------|----------|
| … | … | yes/no |

## Drift / risks
- [glossary vs code mismatches from DRIFT_AUDIT or spot-check]
- [migrations not run, tests not updated, etc.]

## Tests to run before claiming done
- [ ] `pytest …` or REG-* IDs from REGRESSION_TEST_PLAN
- [ ] `e2e/specs/regression/...`

## Recommended next action
[One concrete step — e.g. "Run migration 011, then fix due_day clear rule in accounts API per open question row X"]

## Assumptions (verify if wrong)
- …

## Doc gaps (needs domain-interview)
- [decisions from chat/transcript not yet in glossary or PROJECT_CONTEXT]
```

## Short form (quick catch-up)

Use when the user only needs orientation, not a full brief:

```markdown
**Phase:** … | **Branch:** … | **WIP:** …
**Terms:** [2–3 glossary links]
**Next:** [one action]
**Watch:** [one open question or drift item]
```
