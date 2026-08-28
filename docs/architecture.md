# Architecture

marketing-os is two repositories with different jobs. This one, the **engine repository**,
holds the `mos` CLI, the packaged skills, and the templates. It never contains a business.
Running `mos onboard` (or the bundled onboard skill) produces a **business repository**: a
generated, self-contained marketing brain that holds one business's truth and its execution
artifacts. Judgment, interviews, synthesis, and writing happen in the business repository,
driven by agents. See [the business-repo architecture](business-repo.md) for the generated
structure.

## The engine is model-free, with exactly one documented exception

Every command in this engine is deterministic and calls no model, with one exception that is
named here rather than left to be discovered:

- `core/assist.py`, reached only through `mos assist status` and `mos assist ask`, may invoke
  an agent runtime the operator already has installed — `claude` or `codex` — as a child
  process. It runs on the operator's own subscription, on their machine, and only when they
  explicitly ask for it. It exists because the in-app interview otherwise hands a business
  owner an empty box and asks them to write about their own business cold.
- Nothing else in the engine calls a model. Every other command behaves exactly as it did
  before: same inputs, same outputs, no network, no runtime.
- `dependencies = []` still holds. There is no SDK and no HTTP client here. The engine runs a
  binary the operator already installed, as a child process with a fixed argument list and no
  shell, and never makes a network call of its own — the child does its own networking, on its
  own credentials.
- Nothing that seam produces is written by it. `mos assist ask` returns a draft as data; only
  `mos context set`, under the existing `--plan`/`--yes` gating, writes anything to disk.
- A runtime's output is untrusted input. It is parsed defensively, stripped of escape
  sequences and control characters, length-checked, and returned as a string. It never becomes
  markup, a path, a command, or an argument to anything.

## Engine module map

The engine lives under `src/marketing_os/`:

- `cli/` — the `mos` argument parser and command dispatch. It renders every result as text
  or `--json` and owns the `--plan`/`--yes` gating on mutating commands.
- `core/schema.py` — locates packaged assets (including the `mode-overlays/` tree), reads and
  writes `.mos/config.yaml`, finds the repository root, emits the config marker (`config_text`,
  which records `mode`/`agency`), and resolves the repository mode (`repo_mode`).
- `core/setup.py` — plans and applies the scaffold: copies the business template, then the
  chosen mode's overlay tree (only agency has one), renders `{{BUSINESS_NAME}}`, writes the
  config, and wires runtime skills. It gates on `--mode` (returning a `choose-mode` handoff
  when omitted) and never overwrites an existing business file.
- `core/skills.py` — the runtime sync engine: the packaged skill source, `RUNTIME_DIRS`,
  content hashing (`tree_hash`), the plan/apply cycle, and the manifests that track what was
  installed.
- `core/status.py` — `mos status` and `mos doctor`; derives the repository state and the
  context-readiness view.
- `core/validation.py` — `mos validate`; checks required directories and files, unknown
  top-level paths, the dated-folder grammar, mode-aware structure (the agency client
  registry, stray client folders, and fail-closed `invalid-mode`), and the frontmatter
  contract, with `--strict` promoting contract warnings to errors.
- `core/catalog.py` — `mos index build`; parses frontmatter and links across every document
  and writes `.mos/local/catalog.json`. The frontmatter parser and `coverage` are shared by
  the sensors, the hierarchy generator, and `query`.
- `core/index.py` — `mos index sync` and `mos index status`; generates the three-level
  `_index.md` hierarchy from the catalogue, with a size-bounded explode threshold and a
  do-not-overwrite rule for hand-written indexes.
- `core/related.py` — `mos related`; term-frequency scoring over titles and descriptions with
  a cross-folder weighting and a confidence floor, writing `## Related` blocks without
  disturbing line endings.
- `core/graphlint.py` — the frontmatter-contract sensors, surfaced through `mos validate`
  rather than a command of their own, because the repository already has one place for
  structural truth.
- `core/ingest.py` — `mos ingest`; captures a file, directory, URL, or literal text into a
  validator-conformant `knowledge/sources/YYYY/MM/YYYY-MM-DD-slug/` folder (atomically) and
  lists sources not yet compiled (`--pending`).
- `core/query.py` — `mos query`; a deterministic retrieval planner. It scores catalogued
  metadata when a catalogue exists and falls back to a body scan when it does not, returns
  candidate documents plus the `_index.md` route to them, and offers `--grep` for literal
  lookups (its `score_corpus` is reused by `think`).
- `core/think.py` — `mos think`; emits a grounded thinking handoff (objective, context paths,
  steps, output contract) that targets a `business/decisions/YYYY/MM/YYYY-MM-DD-slug/` file.
- `core/onboard.py` — `mos onboard`; reuses the setup scaffold, optionally `git init`s the
  repository, appends a client row to an agency HQ registry when `--mode client --hq` is given,
  and hands off the interview for unfilled business files.
- `core/update.py` — `mos update`; detects the install mode (source checkout, pipx, unknown)
  and plans or runs the matching self-update command under guards.
- `core/statusline.py` — `mos statusline`; renders the one-line ambient badge and the skill
  install counts.
- `core/assist.py` — `mos assist status` and `mos assist ask`; the one seam that may invoke an
  agent runtime. `status` probes each candidate by actually running it, so a binary that is on
  PATH but cannot answer is reported unavailable. `ask` runs one stateless interview turn: the
  caller holds the conversation and passes it back, the engine keeps no session and no state
  file. The whole prompt travels to the child on stdin, never in its argv; the child's stdout
  and stderr go to files so nothing it prints can contaminate a `--json` envelope; it runs in a
  scratch directory that is deleted afterwards; and it is bounded in wall clock, in bytes, and
  at four questions before a draft is compulsory. `claude` is the runtime this was built and
  verified against; the `codex` entry follows that tool's documented `codex exec` interface and
  has not been exercised against a real install.
- `core/results.py` — the shared JSON envelope (`envelope`, `finding`, `next_action`) every
  command returns.
- `core/atomic.py` — `atomic_write`, the single way every command rewrites a document in the
  operator's repository. `Path.write_text` truncates the target and encodes afterwards, so a
  failure between those two moments leaves an empty file where a document was. `atomic_write`
  encodes first, writes a temporary file in the target's own directory, `fsync`s it, and
  renames it over the target, so a failed write leaves the original exactly as it was.
  Generated machine-local state (`.mos/local/catalog.json`, the runtime manifest, the app's
  pid file) stays on `write_text` deliberately: those readers already treat an unreadable file
  as absent, and the next run writes a fresh one.
- `assets/` — the packaged data: `schema.json` (the canonical structure), the
  `business-template/` scaffold, and the `skills/` source of truth.

## Skill sync model

The bundled skills have a single source, `src/marketing_os/assets/skills/`. Runtime
copies are generated into `RUNTIME_DIRS` (`.claude/skills/` for Claude Code, `.agents/skills/`
for Codex), are ignored by git, and are compared by a content hash of the source tree
(`tree_hash`), not by timestamps. `mos skills sync` plans the difference and applies it only
under `--yes`. A directory the tooling did not generate is treated as unrecognized and is
never overwritten; the plan reports it as a conflict instead. Installs are recorded in a
manifest so a later run can tell a stale generated copy from a hand-authored one. See
[the agent runtime contract](agent-runtime-contract.md) for the full rules.

## Local state

Machine-local runtime state lives below `.mos/local/` and is never committed; the
project-level runtime manifest is written there. `mos install` wires the same skills into the
user's home directory and records that in `~/.marketing-os/runtime-manifest.json`.

## Two thin loaders

`AGENTS.md` and `CLAUDE.md` in a business repository are intentionally thin runtime loaders.
Both point to `BRAIN.md`, preventing two instruction systems from drifting apart.

## Memory layers

- `BRAIN.md` is the shared operating contract.
- `CONTEXT.md` records the current focus and constraints.
- `business/` is the sole source of business truth.
- `knowledge/` contains immutable sources and maintainable synthesized knowledge.
- Execution work goes to the matching dated content, campaign, report, or output folder.
- `archive/` is excluded from ordinary grounding.
