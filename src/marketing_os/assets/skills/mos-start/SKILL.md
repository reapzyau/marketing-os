---
name: mos-start
description: Start or resume work from deterministic repository facts and recommend one useful next action.
---

# Start

Orient from repository truth before giving advice.

## How to run this skill (interactive)

This skill is read-only, but keep it a conversation, not a monologue:

- If the user's intent is unclear, ask before you dig in — don't assume what they want.
- After orienting, offer the one recommended next action and ask whether to take it, rather than
  acting unprompted.
- Anything that would write or reach outside the repo waits for the user's explicit go-ahead.

## Inspect

Run:

```bash
mos status . --json
```

If health or runtime discovery is unclear, also run `mos doctor . --json`.

## Ground

Read in this order:

1. `BRAIN.md` for the operating contract.
2. `CONTEXT.md` for current focus and constraints.
3. Only the business files relevant to the request.
4. Relevant wiki pages and prior work only when they improve the answer.

Do not load `archive/` for ordinary grounding.

## Route

- If this is not a marketing-os repository, use `mos-setup`.
- If structure or runtime wiring is unhealthy, propose the exact repair plan before applying it.
- If core context is incomplete, recommend the first missing context item.
- Otherwise follow the user's stated intent directly.

Read installed capabilities from the `installed_skills` status field. Never route to a skill that
is not installed. When no specialist exists, continue with the base agent using the repository's
rules and context.

## Respond

Return:

- the current state in one sentence;
- one recommended next action and why it matters;
- the relevant skill or CLI operation, if one exists;
- any approval required before writing or external action.

Do not dump a generic menu when the user has already stated what they want.
