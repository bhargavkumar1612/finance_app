# Glossary entry template

Copy into `docs/DOMAIN_GLOSSARY.md` under the appropriate section.

```markdown
### [Canonical term]

**Definition:** One or two sentences in the owner's words.

**Synonyms (avoid in code/UI):** term-a, term-b — or "none"

**Canonical in code:** `ClassName`, `snake_case_field`, API route `/v1/...`

**Example:** Concrete scenario, e.g. "HDFC Swiggy charge on 2024-03-01"

**Not the same as:** [Other term] — brief distinction

**Related code:**
- `app/path/to/file.py`
- `frontend/path/to/component.tsx`

**Decided on:** YYYY-MM-DD
```

## Project context snippet template

Copy into `docs/PROJECT_CONTEXT.md`.

```markdown
### [Topic]

**Preference / priority:** ...

**Mental model:** How the owner thinks about this

**Non-goals:** What we are not building

**Decided on:** YYYY-MM-DD
```

## Decision record template (optional)

Create `docs/decisions/NNN-short-title.md` when the "why" matters.

```markdown
# NNN — [Title]

**Status:** accepted | superseded

**Context:** What forced a choice

**Decision:** What we chose

**Consequences:** Tradeoffs, follow-ups

**Decided on:** YYYY-MM-DD
```
