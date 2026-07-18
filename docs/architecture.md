# Architecture

marketing-os is two repositories with different jobs. This one, the **engine repository**,
holds the `mos` CLI, the packaged skills, and the templates. It never contains a business.
Running `mos setup` (or the bundled setup skill) produces a **business repository**: a
generated, self-contained marketing brain that holds one business's truth and its execution
artifacts. The engine is model-free and deterministic; judgment, interviews, synthesis, and
writing happen in the business repository, driven by agents. See
[the business-repo architecture](business-repo.md) for the generated structure.

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
  top-level paths, the dated-folder grammar, and mode-aware structure (the agency client
  registry, stray client folders, and fail-closed `invalid-mode`).
- `core/ingest.py` — `mos ingest`; captures a file, directory, URL, or literal text into a
  validator-conformant `knowledge/sources/YYYY/MM/YYYY-MM-DD-slug/` folder (atomically) and
  lists sources not yet compiled (`--pending`).
- `core/query.py` — `mos query`; a deterministic retrieval planner that scores the corpus by
  term frequency and returns candidate documents (its `score_corpus` is reused by `think`).
- `core/think.py` — `mos think`; emits a grounded thinking handoff (objective, context paths,
  steps, output contract) that targets a `business/decisions/YYYY/MM/YYYY-MM-DD-slug/` file.
- `core/onboard.py` — `mos onboard`; reuses the setup scaffold, optionally `git init`s the
  repository, appends a client row to an agency HQ registry when `--mode client --hq` is given,
  and hands off the interview for unfilled business files.
- `core/update.py` — `mos update`; detects the install mode (source checkout, pipx, unknown)
  and plans or runs the matching self-update command under guards.
- `core/statusline.py` — `mos statusline`; renders the one-line ambient badge and the skill
  install counts.
- `core/results.py` — the shared JSON envelope (`envelope`, `finding`, `next_action`) every
  command returns.
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
