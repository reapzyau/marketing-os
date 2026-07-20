# Setup Guide

A first-run walkthrough, from installing the CLI to a healthy business brain. Every
command shown here exists in the `mos` CLI; run `mos --help` or `mos <command> --help`
at any point to confirm syntax.

## 1. Install the CLI

Install `mos` with pipx so it lands on your PATH in an isolated environment:

```bash
pipx install marketing-os
```

Check it is available:

```bash
mos --version
```

You should see a line like `mos 0.1.0`.

## 2. Install the bootstrap skills globally

`mos install` copies the bundled skills — including `mos-onboard`, `mos-start`, and
`mos-help` — into your home directory so every runtime can find them. It targets `~/.claude/skills`
for Claude Code and `~/.agents/skills` for Codex, and records what it installed in
`~/.marketing-os/runtime-manifest.json`.

Like every mutating command, `install` requires exactly one of `--plan` or `--yes`.
Preview first:

```bash
mos install --runtime all --plan
```

The plan lists the skill directories it would create, and writes nothing. Read it,
then apply:

```bash
mos install --runtime all --yes
```

Use `--runtime claude` or `--runtime codex` to install for a single runtime; `all`
installs both. After applying, the manifest records a content hash for each installed
skill so later runs know when a copy is stale and can be refreshed instead of duplicated.

## 3. Create a folder for your business

Make an empty folder and move into it. The brain will be scaffolded here:

```bash
mkdir my-business
cd my-business
```

Onboard refuses to adopt a non-empty folder that is not already a marketing-os repository,
so start clean.

## 4. Open the folder in your agent and run onboard

Open the folder in Claude Code or Codex, then run the onboard skill:

- Claude Code: `/mos-onboard`
- Codex: `$mos-onboard`

Both load the same workflow. Before it scaffolds anything, the skill settles the one
question that shapes the whole brain: **which mode?**

- `in-house` — one brand you run yourself. Knowledge is global to the brand.
- `agency` — you serve clients. This HQ repo holds a client *registry* (pointers only);
  each client later gets its own repo via `mos onboard`.
- `client` — the brain for a single agency client. Pass `--agency "<agency name>"` so the
  repo records who runs it.

`--mode` is required. If you leave it off, onboard writes nothing and returns a
`choose-mode` next action whose reason is the exact question to put to the user.

The skill runs `mos status . --json` to check the current state, then previews the
scaffold before writing anything:

```bash
mos onboard . --name "My Business" --mode in-house --runtime all --plan --json
```

The plan lists the files and skill copies it would create. After you approve, the skill
applies it:

```bash
mos onboard . --name "My Business" --mode in-house --runtime all --yes --json
```

This creates the canonical brain: `BRAIN.md`, `CONTEXT.md`, the `business/`, `knowledge/`,
`content/`, `campaigns/`, `reporting/`, and `outputs/` trees, and the generated runtime
skill copies under `.claude/skills/` and `.agents/skills/`. It also initializes a git
repository and records a first commit. See [business-repo.md](business-repo.md) for the
full structure.

## 5. Establish minimum context

Scaffolding creates empty rooms; the onboard skill then interviews you to fill the required
context areas: brand, voice, audience, the primary offer, and strategy
(`business/strategy/{strategy,goals,roadmap}.md`). It proposes the exact edits and saves
them only after you approve. Nothing is invented and no non-placeholder file is overwritten
without discussion.

## 6. Verify

Confirm the brain is structurally sound and both runtimes are wired:

```bash
mos status . --json
mos doctor . --json
```

`mos status` reports a `repo_state`. You are aiming for `ready`. Along the way you may see:

- `absent` - the folder is not a marketing-os repository yet; run onboard.
- `invalid` - a structural error to repair before doing business work.
- `needs-runtime-sync` - the runtime skill copies are missing or stale; run `mos skills sync`.
- `needs-context` - structure and wiring are fine but a required context area is still empty.
- `ready` - structure, runtime wiring, and required context are all complete.

`mos doctor` adds an explicit health check across structure, runtime wiring, and context
readiness for both Claude Code and Codex. When both commands report a healthy `ready`
repository, run the start skill (`/mos-start` or `$mos-start`) to begin working from
`CONTEXT.md`.

If anything looks off, [troubleshooting.md](troubleshooting.md) maps each state to a remedy.
