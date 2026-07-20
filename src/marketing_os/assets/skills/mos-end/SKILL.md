---
name: mos-end
description: Close a marketing-os session by recording the current focus, logging what changed, and proposing a safe commit.
---

# End

Close the session from deterministic facts, capture durable memory, and offer a reviewed save.
There is no checkpoint command; git is the mechanism and this skill narrates it.

## How to run this skill (interaction contract)

Ending a session records memory and can commit to git, so keep it interactive:

- Propose the exact `CONTEXT.md` and log edits and wait for approval before writing them.
- Show the commit message and the full file list, and commit only after the operator approves.
- Never push, force, or rewrite history unless the operator explicitly asks, and never commit
  secrets or raw customer data.

## Inspect

Run:

```bash
mos status . --json
mos validate . --json
```

Use status for the current business state and validate for unresolved structural gaps. Report
what business truth or deliverables changed this session, and anything left incomplete.

## Record

Propose the exact edits before writing, then after approval:

- update `CONTEXT.md` with the current focus and any open loops to resume;
- append one dated session entry to `knowledge/wiki/_log.md` summarizing what changed and why.

Keep both edits short and business-readable. Never invent tomorrow's priority; `mos-start`
opens the next session.

## Save

Preview the changed files, then propose a commit with a business-language message. After
approval:

```bash
git add -A
git commit -m "<business-readable summary of the session>"
```

Show the message and the file list before committing, and commit only after the operator
approves. Never push, and never force or rewrite history, unless the operator explicitly asks.
Do not commit secrets, credentials, or raw customer exports.
