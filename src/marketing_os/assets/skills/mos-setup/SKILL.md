---
name: mos-setup
description: Create a new marketing-os business brain or safely complete its initial context and runtime wiring.
---

# Setup

Create an agent-ready marketing brain without inventing folders or overwriting business truth.

## How to run this skill (interaction contract)

This skill is an **interactive, guided flow — not a batch job.** Run it as a conversation and
hold to these rules at every step:

- **Never invent or assume** the business name, destination path, mode, or any context value.
  Each of these comes from the user.
- **Ask for one thing at a time, then stop and wait** for the user's answer before moving on.
  Do not run ahead with placeholders or guessed values.
- Use **`AskUserQuestion`** for fixed choices (for example, the mode). Ask in plain language for
  free-text answers such as the business name or the destination.
- **Show every plan and get explicit approval before writing.** Never run a `--yes` command
  until the user has seen the plan and told you to proceed.
- If a step needs something the user has not given you, your next action is to **ask them** — not
  to proceed.

## 1. Detect what is already here

Run `mos status . --json` first, in case the current directory is already a repository, and tell
the user what you found:

- **A ready or incomplete marketing-os repo** — continue in place.
- **An empty directory** — you still need a business name and destination; do not assume them,
  ask (step 2).
- **A non-empty directory without a marketing-os identity** — do **not** adopt or migrate it.
  Tell the user and ask where they want the new brain created instead.

Report what you detected before doing anything else.

## 2. Ask for the business name and destination

Ask the user, and wait for each answer:

- **What is the business called?** Use their exact name — never a placeholder.
- **Where should the brain live?** Confirm an empty destination path. Offer one only as a
  proposal for the user to confirm or replace.

Do not continue until you have both.

## 3. Ask which mode (use AskUserQuestion)

Setup requires a mode. Ask the user with **`AskUserQuestion`** and wait for their choice:

- **in-house** — one brand you own. Knowledge is global to the brand.
- **agency** — you serve clients; this creates the agency HQ with a client registry
  (`business/clients/clients.md`, pointers only). Each client gets its own repo via
  `mos onboard --mode client --agency "<agency name>" --hq "<agency-hq-path>"`, because the
  repo is the access boundary.
- **client** — a brain for one agency client. Ask for the agency name and pass
  `--agency "<agency name>"` to record who runs it.

If you ever run setup without `--mode`, it returns `ok=false` with a `choose-mode` next action —
relay its question to the user and wait for their answer; never pick a mode for them.

## 4. Plan, then ask approval before writing

With the confirmed name, destination, and mode, preview the scaffold — this writes nothing:

```bash
mos setup "<path>" --name "<business name>" --mode <in-house|agency|client> --runtime all --plan --json
```

Explain the destination and the proposed changes to the user. **Then stop and ask for approval.**
Only after they approve, apply:

```bash
mos setup "<path>" --name "<business name>" --mode <in-house|agency|client> --runtime all --yes --json
```

## 5. Establish minimum context — one question at a time

After scaffolding, gather these four inputs **conversationally, asking one at a time and waiting
for each answer** — never fill them in yourself:

1. What the business is and wants to be known for.
2. Who the primary audience is and what they are trying to change.
3. The primary offer: name, promise, mechanism, price or commercial model, and next step.
4. How the business should sound, including representative examples and language to avoid.

For each answer, **propose the exact edit and get approval before saving.** After approval:

- update `business/brand/brand.md` and `business/brand/voice.md`;
- update `business/audience/primary.md`;
- create `business/offers/<offer-slug>/offer.md` using a lowercase hyphenated slug;
- update `CONTEXT.md` with the current focus and desired outcome.

Never collect secrets, credentials, raw customer exports, or private account data into tracked
files. Never replace a non-placeholder business file without asking the user first.

## 6. Verify

Run:

```bash
mos validate . --json
mos status . --json
mos doctor . --json
```

Finish by telling the user the business outcome, any context gaps, runtime readiness, and one
next action — then ask what they want to do next.
