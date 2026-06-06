# Domain interview — question bank

Use these categories to generate focused questions. Pick only what applies to the current mode and codebase scan.

## Terms and definitions

- What does **[term]** mean to you in daily use?
- Is **[term A]** the same as **[term B]**, or different?
- When you say **[user phrase]**, which feature or screen do you picture?
- Should this appear in the UI as **[label A]** or **[label B]**?

## Naming and code alignment

- What is the **canonical name** for this concept in code and docs?
- Which synonyms should we **avoid** in UI, chat, and variable names?
- Does **[model/API name]** match how you think about it, or should we rename?

## Money and finance semantics

- Does **spending** include transfers between your own accounts?
- How should **credit card** charges vs payments appear in totals?
- Are **refunds** negative spending, excluded, or a separate category?
- What counts as **income** vs **transfer** vs **expense**?
- How do **recurring bills** differ from one-off transactions or subscriptions?

## Accounts and imports

- What is an **account** vs a **wallet** vs a **ledger** in your mental model?
- For **HDFC / bank CSV** rows, which columns or row types are authoritative?
- When import dedupes a row, what makes two rows "the same" to you?
- Should imported rows ever be auto-categorized, or always confirmed?

## Chat and agent behavior

- When the copilot **proposes** an action, what must always be confirmed first?
- What should happen when the model is **wrong** — fallback message, retry, or redirect?
- Which questions should **never** be answered from the LLM alone (numbers, balances)?

## Priorities and scope

- What is **more important**: accuracy, speed of entry, or rich insights?
- What is **explicitly out of scope** for this app?
- For MVP, which feature wins if we cannot do both?

## Edge cases

- How should we handle **[specific scenario from sample data or code]**?
- What is the expected behavior when **[missing account / zero balance / duplicate import]**?

## Audit prompts

- I found **[code term]** in `path` but **[doc term]** in docs — which is canonical?
- The glossary says X but the UI shows Y — update glossary or UI?
- This open question has been unresolved since **[date]** — still valid?
