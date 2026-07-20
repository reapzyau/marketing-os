---
name: mos-onboard
description: Create a brand-new business brain in its own folder with git history and hand off the context interview.
---

# Onboard

Create a new brain — the operator's own business or an agency client — in one command with a
first commit, then interview for real context. Use `mos-setup` instead to complete or repair
the repository you are already in; onboarding always targets a new folder.

## How to run this skill (interaction contract)

This skill is an interactive, guided flow — not a batch job. It creates a real repository with
git history, so a wrong guess costs more than a question. At every step:

- Never invent or assume the business name, mode, agency, or destination — each comes from the
  user. Ask for one thing at a time and wait for the answer before moving on.
- Use `AskUserQuestion` for fixed choices (the mode); ask in plain language for free-text such
  as the business name or the destination.
- Show the plan and get explicit approval before applying — never run `--yes` until the user has
  seen the plan and told you to proceed.
- If a step needs something the user has not given you, ask them; do not proceed on a guess.

## Ask

Establish two facts before touching disk:

1. Whose brain is this — the operator's own business, an agency they run, or one of that
   agency's clients? That maps to `--mode in-house`, `--mode agency`, or `--mode client`.
   Client mode also needs `--agency "<agency name>"`.
2. The business display name.

## Choose the destination

Target a new empty folder with a lowercase hyphenated name; the plan result's
`suggested_repo_name` is the default (the business slug plus `-hq`, or `<agency>-<client>` for
a client). Keep an agency's client brains as sibling folders under one parent workspace
directory. Never create a brain inside an existing
brain — a nested repository violates the parent's schema. If the destination already is a
brain, route to `mos-start` or `mos-setup` instead.

## Plan before writing

```bash
mos onboard "<path>" --name "<business name>" --mode <mode> --runtime all --plan --json
```

Explain the plan: the scaffold, plus `git init`, `git add -A`, and a first commit. For a
client, add `--agency "<agency name>"`, and pass `--hq "<agency hq path>"` to register the
client in the agency's registry. Ask for approval, then re-run with `--yes` in place of
`--plan`.

## Interview

The onboard result includes an `interview` handoff listing the unfilled business files with
guidance — follow it rather than inventing a script. Gather the same inputs as `mos-setup`: what
the business is, who the audience is, the primary offer, how it should sound, and the strategy
(the approach, goals, and roadmap → `business/strategy/{strategy,goals,roadmap}.md`). Propose
exact edits, and write them to the same files only after approval.

## Verify

Run from the new brain:

```bash
mos validate . --json
mos status . --json
mos doctor . --json
```

Finish with the business outcome, remaining context gaps, and one next action.
