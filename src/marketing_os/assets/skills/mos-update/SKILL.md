---
name: mos-update
description: Update the marketing-os engine, then refresh the bundled skills and verify runtime wiring.
---

# Update

Update the installed marketing-os engine and refresh its generated skill copies. The CLI owns
the mechanics; do not ask the user whether they installed from source or pipx, and do not reach
for raw package commands as the first path.

## Preview

Run:

```bash
mos update --plan --json
```

Explain what the plan reports — the detected install mode and whether an engine change is
pending. If it is already current, say so and stop.

## Apply

After approval:

```bash
mos update --yes --json
```

If the result is not ok, show the first finding and stop. Do not continue as if the update
succeeded.

## Refresh skills

A new engine can ship new or changed skills. Refresh the generated copies, previewing first:

```bash
mos install --plan --json
mos skills sync . --plan --json
```

After approval, apply the ones with pending changes:

```bash
mos install --yes --json
mos skills sync . --yes --json
```

## Verify

Confirm the runtime adapters are healthy:

```bash
mos doctor . --json
```

If skill directories changed, tell the user that Claude Code loads its skills at session start,
so a restart from this repository may be needed before new routes appear.
