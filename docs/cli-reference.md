# CLI Reference

`mos` is a deterministic, model-free command line tool that manages a file-based
marketing brain. It scaffolds structure, reports facts, validates the canonical
schema, and wires the shared skills into each runtime. It never writes business
prose; that is the agent's job.

```text
mos [--version] <command> [path] [options]
```

- `--version` prints `mos <version>` and exits.
- Every command accepts `--json` to emit the machine envelope only.
- Exit code is `0` when the result is `ok`, otherwise `1`.

See [json-output-contract.md](json-output-contract.md) for the envelope shape and
[agent-runtime-contract.md](agent-runtime-contract.md) for the skill sync model.

## Mutation gating

The mutating commands (`install`, `onboard`, `skills sync`) require **exactly one** of:

- `--plan` — preview the changes without writing anything.
- `--yes` — apply the reviewed changes.

The two flags form a required, mutually exclusive group. Passing both or neither
is rejected before any work runs. The convention is: plan, review the reported
changes, then apply. Read-only commands (`status`, `validate`, `doctor`) take no
mutation flag.

## Output modes

Without `--json`, `mos` prints a human summary: a state line (`OK` or
`NEEDS ATTENTION`), the repository path, any changes, any findings, and the next
action's reason. With `--json`, it prints only the sorted, indented envelope.
Failures are still reported through the envelope, never as a stack trace.

## Commands

### `mos install`

```text
mos install [--runtime claude|codex|all] (--plan | --yes) [--json]
```

Installs every bundled skill (the set listed in the packaged `manifest.json`)
**globally** into your home directory so they are available in every project. The
target runtime directories are `~/.claude/skills` (Claude Code) and
`~/.agents/skills` (Codex); `--runtime all` (the default) does both. Installed
copies are tracked in the global manifest at
`~/.marketing-os/runtime-manifest.json`. Run this once per machine before opening
any business folder.

### `mos onboard`

```text
mos onboard [path] --name "<business name>" --mode in-house|agency|client [--agency "<name>"] \
    [--hq <path>] [--runtime claude|codex|all] (--plan | --yes) [--json]
```

The single command to create **or** complete a business brain. Onboard works on a
new empty folder (scaffold + `git init` + first commit + interview) and on an
existing brain (complete or repair in place; `git init` only when the folder is not
already a repository). `--name` is required. `--mode` is also required and decides
how the brain is shaped:

- `in-house` — one brand you run yourself; knowledge is global to the brand.
- `agency` — you serve clients; the HQ repo also scaffolds
  `business/clients/clients.md`, a registry of pointers to each client's own repo.
- `client` — the brain for a single agency client; requires `--agency "<name>"`,
  which is recorded in the config. Passing `--agency` in any other mode is ignored
  with an `agency-ignored` warning.

Omitting `--mode` returns `ok: false` with a `mode-required` finding and a
`choose-mode` next action (nothing is written); the action's `reason` is the
verbatim question to put to the user. An unrecognized value returns `invalid-mode`.

Onboard writes the template tree, the agency overlay when relevant, the
`.mos/config.yaml` identity file (carrying `mode`, plus `agency` in client mode),
and the project-local runtime skill copies. It refuses a non-empty destination that
is not already a marketing-os repository, and it never overwrites an existing
business file. It then runs the context interview — brand, voice, audience, offer,
and strategy (`business/strategy/{strategy,goals,roadmap}.md`) — and carries an
`interview` block in the envelope listing still-unfilled business files. On apply it
also initializes a git repository and records a first commit; when git is unavailable
the step is skipped with a `git-unavailable` warning.

`--hq <path>` applies only in client mode. It points at the agency HQ repo and, on
apply, appends a registry row to `<hq>/business/clients/clients.md`, inserted
directly after the `_example-client_` row (else at the table tail). The row records
the client repo as a **relative, forward-slash path** from the HQ root (falling back
to an absolute path only across Windows drives). Duplicate client names (compared
case-insensitively) are skipped with `client-already-registered`; an HQ path that is
not an agency repo warns `no-client-registry`; a registry file with no markdown
table warns `registry-malformed`; and `--hq` in a non-client mode warns
`hq-ignored`. In `--plan` mode nothing is written to the registry. The envelope adds
`mode` and `suggested_repo_name` facts on success (`{slug}-hq` for in-house/agency,
`{agency-slug}-{slug}` for client).

After onboard, push to GitHub with the manual handoff:
`gh repo create <owner>/<repo> --private --source . --push`

### `mos migrate`

```text
mos migrate [path] [--plan-file <plan.json>] (--plan | --yes) [--json]
```

Routes off-schema files into the canonical structure. It is model-free: with no
`--plan-file` in `--plan` mode it **diagnoses**, listing the stray top-level entries
as `unrouted` (dotfiles and canonical areas are ignored) — nothing is written. Given
a `--plan-file` — a `mos.migrate-plan.v1` document with `mkdirs` and `moves` — it
validates the moves as a set and, under `--yes`, applies them. The plan is atomic:
if any move is invalid (missing source, a destination that escapes the repo, or a
destination that already exists) **nothing** is written and the findings name what to
fix; existing files are never overwritten. The judgement of where each stray file
belongs lives in the `mos-migrate` skill, not the command. The envelope adds
`unrouted`, `plan_schema`, `moved`, and `created_dirs` facts.

### `mos status`

```text
mos status [path] [--json]
```

Inspects structure, context readiness, and runtime wiring, then reports a single
`repo_state` (see below). This is the primary orientation command. It is
read-only. Exit code is `0` for `needs-runtime-sync`, `needs-context`, and
`ready`; `absent` and `invalid` exit `1`.

### `mos validate`

```text
mos validate [path] [--json]
```

Validates the canonical schema and the dated-folder grammar (config identity,
required directories and files, allowed top-level paths, and the
`YYYY/MM/YYYY-MM-DD-slug` layout for dated artifacts). Structural problems are
`error` findings; unknown top-level paths are `warning` findings. Exit is `1`
only when there is at least one error.

### `mos doctor`

```text
mos doctor [path] [--json]
```

Runs the `status` checks plus an explicit health verdict for both runtime
adapters. It reports a `checks` block (`structure`, `runtime_wiring`,
`context_ready`) and is `ok` only when structure is sound **and** Claude Code and
Codex skill discovery are both ready.

### `mos skills sync`

```text
mos skills sync [path] [--runtime claude|codex|all] (--plan | --yes) [--json]
```

Plans or synchronizes the **project-local** runtime skill copies against the
packaged source, using content-hash staleness detection. It creates missing skill
directories and replaces stale generated ones, but never overwrites an
unrecognized directory — those raise a `skill-conflict` finding for you to resolve
by hand. Project sync state lives in `.mos/local/runtime-manifest.json`.

## Repository states

`mos status` resolves the repository into exactly one `repo_state`:

| State | Meaning | Suggested action |
|-------|---------|------------------|
| `absent` | No `.mos/config.yaml`; this is not a marketing-os repository. | Run `mos onboard`. |
| `invalid` | Structural `error` findings (missing config, directories, files, or malformed dated folders). | Repair structure, then re-check. |
| `needs-runtime-sync` | Structure is sound but Claude Code or Codex skill copies are missing or stale. | Run `mos skills sync`. |
| `needs-context` | Structure and wiring are sound but required context (brand, voice, audience, offer) is incomplete. | Complete the first missing context file. |
| `ready` | Structure, wiring, and required context are all in place. | Follow `CONTEXT.md` for the current priority. |

Only `absent` and `invalid` make `mos status` return a non-zero exit; the other
states are `ok` because the structure itself is valid.

## Examples

```bash
# One-time global install of the bootstrap skills
mos install --runtime all --plan
mos install --runtime all --yes

# Create a new brain (or complete an existing one), review then apply
mos onboard ./acme --name "Acme Co" --mode in-house --plan
mos onboard ./acme --name "Acme Co" --mode in-house --yes

# Onboard an agency client and register it in the agency HQ
mos onboard ./acme-widgets --name "Widgets Inc" --mode client \
    --agency "Acme Co" --hq ../acme-co-hq --plan
mos onboard ./acme-widgets --name "Widgets Inc" --mode client \
    --agency "Acme Co" --hq ../acme-co-hq --yes

# Daily orientation and machine-readable facts
mos status .
mos status . --json

# Repair loop
mos validate . --json
mos skills sync . --runtime all --plan
mos skills sync . --runtime all --yes
mos doctor . --json
```
