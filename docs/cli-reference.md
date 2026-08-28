# CLI Reference

`mos` is a deterministic command line tool that manages a file-based marketing
brain. It scaffolds structure, reports facts, validates the canonical schema, and
wires the shared skills into each runtime. It never writes business prose; that is
the agent's job.

Every command here is model-free except `mos assist`, which may run an agent runtime
the operator already installed, only when they ask for it, and which writes nothing.
That exception is stated in full in [architecture.md](architecture.md).

```text
mos [--version] <command> [path] [options]
```

- `--version` prints `mos <version>` and exits.
- Every command accepts `--json` to emit the machine envelope only.
- Exit code is `0` when the result is `ok`, otherwise `1`.

See [json-output-contract.md](json-output-contract.md) for the envelope shape and
[agent-runtime-contract.md](agent-runtime-contract.md) for the skill sync model.

## Mutation gating

The mutating commands (`install`, `onboard`, `attach`, `skills sync`, `index sync`, `related`) require **exactly one** of:

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

### `mos attach`

```text
mos attach [path] [--name "<business name>"] [--mode in-house|agency|client] \
    [--runtime claude|codex|all] (--plan | --yes) [--json]
```

Adopts a folder that already holds a brain in an older layout — a `.mos/config.yaml`
written as plain YAML (`mode: in-house`, `name: ...`), or a `BRAIN.md` beside a
`business/` tree — as a first-class marketing-os brain **without rewriting its
content**. Exactly two kinds of write happen: `.mos/config.yaml` is rewritten in the
canonical JSON form (the previous text is kept as `.mos/config.legacy.yaml` when it
differs), and scaffold files the folder lacks are added — the top-level contract
documents (`BRAIN.md`, `CONTRACT.md`, `AGENTS.md`, `.gitattributes`, ...), the required
empty directories, and the generated runtime skill copies. Nothing that exists is
overwritten, and no `business/` or `knowledge/` content file is ever created; a missing
required document is reported as a `missing-content-file` warning and every stray
top-level entry as `off-schema-entry`, both pointing at `mos migrate --plan`.

The name comes from `--name`, then the legacy config's `business_name` or `name`, then
the folder name; the mode from `--mode`, then a valid legacy `mode`, then `in-house`.
A canonical brain is an `ok` no-op with an `already-attached` finding; a folder with no
brain signals is refused with `not-a-brain` and a `run-onboard` next action. The
envelope adds `name`, `mode`, `legacy` (the parsed YAML, or null) and `unrouted`; after
`--yes` the next action is `run-status`.

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
mos validate [path] [--strict] [--json]
```

Validates the canonical schema, the dated-folder grammar (config identity,
required directories and files, allowed top-level paths, and the
`YYYY/MM/YYYY-MM-DD-slug` layout for dated artifacts), and the frontmatter
contract. Structural problems are `error` findings; unknown top-level paths and
contract gaps are `warning` findings. Exit is `1` only when there is at least one
error.

`--strict` promotes every contract finding to an error, which is what continuous
integration should run. Warnings are the default so an early-stage brain, where
most documents are still stubs, is never blocked from doing work.

Contract findings:

| Code | Meaning |
|------|---------|
| `missing-frontmatter` | No contract block, or one of the five required keys is absent. |
| `missing-connective-key` | No `sources`, `related`, or `produced_by`, so nothing reaches this document. |
| `output-without-sources` | A file under `content/`, `campaigns/`, `reporting/`, or `outputs/` with no `sources:`. An output with no sources is not finished. |
| `unlinked-document` | A substantial document that links to nothing. Fix with `mos related`. |
| `invalid-type` | `type` is outside the vocabulary, or contradicts the folder it sits in. |
| `invalid-status` | `status` is not one of draft, active, archived, superseded. |

The `summary` block reports `errors`, `warnings`, and `contract_gaps`.

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

### `mos index build`

```text
mos index build [path] [--json]
```

Reads every document once and writes the catalogue to `.mos/local/catalog.json`
(machine-local, gitignored). The catalogue records each document's title,
description, type, status, word count, outgoing links, and which contract keys it
carries. It is what lets `mos query` answer without opening a single document
body.

### `mos index sync`

```text
mos index sync [path] (--plan | --yes) [--json]
```

Regenerates the `_index.md` navigation hierarchy from the live corpus. Three
levels: the root index names every folder holding documents; a folder index lists
its groups or its documents; a group index lists documents. A folder at or below
40 documents lists them inline, above that it explodes into child indexes, which
is what keeps any single navigation file small enough to be worth reading.

Below 25 documents in total, only the root index is generated — a hierarchy over a
near-empty brain is noise, and the command says so with a `small-corpus` finding.

Generated files carry a do-not-hand-edit marker. If a file of the same name exists
without that marker, the generator leaves it alone and raises
`hand-written-index`. Re-running when nothing has changed writes nothing.

### `mos index status`

```text
mos index status [path] [--json]
```

Reports catalogue freshness and navigation coverage: the share of documents
carrying frontmatter, a description, and an outgoing link, plus which folder
indexes exist. A `stale-catalog` or `no-catalog` finding means `mos query` is
falling back to reading every document.

### `mos related`

```text
mos related [path] (--plan | --yes) [--limit N] [--json]
```

Proposes a `## Related` block for every substantial document that links to
nothing. Candidates are scored by term overlap across `title` and `description`
only — not bodies, so a long document cannot dominate by length — and targets in a
different top-level folder are weighted higher, because those are the connections
nothing else in the repository supplies.

A weak match emits nothing rather than a plausible-looking wrong link, so on a
small corpus the correct output is often an empty plan. Documents under 120 words,
archived or superseded material, `knowledge/sources/`, and structural files are
never touched and never linked to. Existing line endings are preserved.

### `mos query`

```text
mos query "<question>" [path] [--limit N] [--grep] [--json]
```

Plans deterministic retrieval. With a catalogue present it scores the question
against titles, descriptions, types, and paths, so cost does not grow with
document length; without one it falls back to reading bodies and says so in
`source`. The corpus covers every non-archived document, not just `business/` and
`knowledge/wiki/`.

Alongside `candidates`, the response carries `route`: the chain of `_index.md`
files leading to the best candidate. Walking that chain first is what turns
retrieval into navigation — the model gets the branch, not only the leaf.

`--grep` switches to literal substring lookup and returns `path`, `line`, and the
matching text. Use it for URLs, names, identifiers, and error strings, where term
scoring is the wrong tool.

### `mos context show`

```text
mos context show [path] [--json]
```

Turns every context gap `mos status` reports into a question a person can answer.
For each field it returns the `name`, a plain-language `question` and `hint`, the
backing file `path`, `writes_to` (where an answer would land), whether it is
`complete`, and `body` — the operator's own words, with the document's heading
stripped. Required fields come first.

Completeness is decided by the same function `mos status` uses, so untouched
template boilerplate reports as no answer and the two commands can never disagree.
Read-only.

### `mos context set`

```text
mos context set [path] --field <name> --text <answer> [--slug <offer-slug>] (--plan | --yes) [--json]
```

Writes one answer into the file that backs one context field, and nothing else.
`--text -` reads the answer from stdin, so a long answer is never mangled by the
shell. `--slug` chooses which offer to write; it is required once a brain has more
than one, and ignored on every other field.

Frontmatter that is already on the file is preserved line for line apart from
`date`, which is refreshed; a file with no contract block is given one per
`CONTRACT.md`. Only the body beneath the block is replaced, and the file's existing
line endings are kept, so a one-line answer produces a one-line diff rather than a
whole-file rewrite.

`--plan` returns a real unified diff in `diff` and writes nothing. `field_complete`
says whether the answer is substantial enough to count; a short one still writes but
returns an `answer-too-short` warning and leaves the field in `missing`.

### `mos assist status`

```text
mos assist status [--json]
```

Reports which agent runtimes on this machine can genuinely answer. Being on PATH is
not the test: each candidate (`claude`, then `codex`) is resolved with `shutil.which`
and then actually run with `--version` under a short timeout. One that resolves but
exits non-zero, prints nothing, or never returns is reported unavailable with the
reason it failed.

`runtimes` lists only the invocable ones, each with `name`, `path`, and `version`.
`checked` lists every candidate with `resolved`, `available`, `reason`, and `version`,
so a caller can explain the absence. `ready` is whether anything answered. This
command writes nothing and needs no repository.

`claude` is the runtime this was built and verified against. The `codex` entry follows
that tool's documented `codex exec` interface and has not been exercised against a
real install, so `available: true` for `codex` is a statement about its version probe,
not a promise that a turn will succeed.

### `mos assist ask`

```text
mos assist ask [path] --field <name> [--transcript-json <json>] [--json]
```

Runs one stateless interview turn for one context field, using the first runtime that
answered. It runs on the operator's own subscription and spends their tokens, only on
an explicit request.

The caller owns the conversation. `--transcript-json` is the whole memory of the
interview: a JSON array of `{"question": ..., "answer": ...}` objects, defaulting to
`[]` on the first turn. The engine keeps no session, no state file, and no history on
disk between turns.

Before it asks anything the assistant is given what the brain already knows — the
business name, the mode, and every field already answered with the operator's own
words — read from the same place `mos context show` reads it, so nobody is asked
twice about something they have already said.

Two shapes come back, both inside the standard envelope on schema `mos.assist.v1`:

```json
{ "schema": "mos.assist.v1", "ok": true, "operation": "ask", "field": "brand",
  "runtime": "claude", "done": false, "question": "...", "draft": "",
  "turn": 2, "turns_used": 1 }
```

```json
{ "schema": "mos.assist.v1", "ok": true, "operation": "ask", "field": "brand",
  "runtime": "claude", "done": true, "question": "", "draft": "...",
  "turn": 5, "turns_used": 4 }
```

The interview is bounded at four questions. The fifth turn must produce a draft, and
that is enforced by the engine rather than by the wording sent to the model: a reply
that asks a fifth question is discarded and reported as an error, never handed back as
a question. A transcript longer than four turns is refused outright.

**This command writes nothing.** The draft comes back as data for the operator to read
and edit; `mos context set`, under the existing `--plan`/`--yes` gating, is still the
only thing that writes it to a file.

The whole prompt — the field, the grounding, and the transcript — is written to a file
this command creates and handed to the child on stdin. Nothing operator-authored or
model-authored is ever placed in the child's argument list, so a field name, an answer,
or a draft that begins with `-` has no route to being parsed as a flag. `--field` is
additionally checked against the closed set of context fields. There is no shell. The
child's stdout and stderr go to files rather than to inherited descriptors, so nothing
it prints can contaminate the `--json` envelope, and it runs in a scratch directory
that is removed when the turn ends.

Failures are envelopes, never hangs and never stack traces: `no-runtime` when nothing
answered, `unknown-field`, `bad-transcript`, `assist-timeout`, `assist-reply-too-large`,
`assist-failed` when the runtime exited non-zero, and `assist-unusable-reply` when the
reply was not a usable question or draft. In every one of them `question` and `draft`
are empty.

## Repository states

`mos status` resolves the repository into exactly one `repo_state`:

| State | Meaning | Suggested action |
|-------|---------|------------------|
| `absent` | No canonical `.mos/config.yaml`; this is not a marketing-os repository. | Run `mos onboard`, or `mos attach` if the folder already holds an older brain. |
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

# Adopt a folder that already holds a brain in an older layout
mos attach ./the-lab --plan
mos attach ./the-lab --yes

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

# Refresh the navigation layer after writing documents
mos index build .
mos index sync . --plan
mos index sync . --yes
mos related . --plan
mos related . --yes
mos index status . --json

# Ask the brain a question, or find an exact string
mos query "how should we price the retention offer" . --json
mos query "https://example.com/pricing" . --grep --json

# Fail continuous integration on contract gaps
mos validate . --strict --json
```
