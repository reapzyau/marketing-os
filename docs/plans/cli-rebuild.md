# Plan: rebuild six CLI commands (agent-first)

Status file: this document is the contract. Executors implement FROM THIS FILE and the
existing code conventions — never from the predecessor repo (see AGENTS.md).

## Product framing

`mos` is an agent-first CLI: the primary operator is an LLM agent (Claude Code, Codex,
ChatGPT). Consequences, non-negotiable:

1. The CLI is deterministic and model-free. It never calls an LLM. Where judgment is
   needed, the command returns a **grounded prompt / handoff instructions inside the
   result envelope** for the calling agent to execute.
2. Every command supports `--json` and returns the standard envelope from
   `core/results.py` (`envelope()`): `schema, command, ok, repo, changes, findings,
   next_action, **facts`. `next_action` is how the CLI drives the agent loop.
3. Mutating commands require exactly one of `--plan | --yes` (see `_add_mutation` in
   `cli/main.py`). Read-only commands take neither.
4. Exit code: `0` when `ok` true, `1` otherwise — except `statusline` (always 0).
5. stdlib only (`dependencies = []`). Windows + macOS + Linux safe: use `pathlib`,
   `encoding="utf-8"` on every read/write, no ANSI unless TTY and `NO_COLOR` unset.

## Existing conventions to match

- `core/<name>.py` exposes one or two pure-ish functions returning the envelope dict;
  `cli/main.py` only parses args and dispatches. Match the style of `core/status.py`
  and `core/setup.py`.
- `core/schema.py` helpers: `read_config`, `find_root`, `slugify`, `template_root`.
  Config file is `.mos/config.yaml` containing JSON (`mos.business-repo.v1`,
  key `business_name`).
- Business-repo layout (from `assets/business-template/`): `BRAIN.md`, `CONTEXT.md`,
  `business/{audience,brand,decisions,offers,operations,proof,strategy}/`,
  `campaigns/`, `content/`, `knowledge/sources/`, `knowledge/wiki/` (with `_index.md`,
  `_log.md`), `outputs/`, `reporting/`, `archive/`.
- Tests: pytest with `tmp_path`, mirroring `tests/unit/test_setup.py` style.
  Coverage gate is 80% (`fail_under=80` in pyproject) — cover error paths too.
- Gates before done: `ruff check .`, `pytest`, `python scripts/check_clean_language.py`.

## Command contracts

### 1. ingest — capture raw material (mutating)

CLI: `mos ingest SOURCE [path] [--topic T] [--slug S] [--date YYYY-MM-DD] (--plan|--yes) [--json]`
     `mos ingest --pending [path] [--json]` (read-only; SOURCE omitted)

Core: `core/ingest.py`
- `ingest_repo(root: Path, source: str, *, topic: str | None, slug: str | None, date: str | None, apply: bool) -> dict`
- `pending_sources(root: Path) -> dict`

Behavior:
- Destination: `knowledge/sources/[<topic>/]<YYYY-MM-DD>-<slug>/`. Date defaults to
  `datetime.date.today().isoformat()`; `--date` overrides (validate format).
- Source resolution, in order: existing file → copy its text into `source.md`;
  existing directory → copy every `*.md`/`*.txt` under it into the dated folder and
  write a `source.md` manifest listing them; `http(s)://…` string → store the URL in
  `source.md` verbatim (the CLI never fetches; `next_action` tells the agent to fetch
  and re-ingest content if needed); anything else → treat as literal text.
- `source.md` starts with a metadata header (markdown, not YAML deps): ingested date,
  origin (path/url/literal), topic, slug.
- Immutability: if the dated folder already exists → `ok=false`, finding
  `source-exists`, no writes.
- `--plan` reports the would-be writes in `changes` without touching disk.
- Slug: `--slug` or `slugify()` of the file stem / first words of text.
- `next_action` on success: id `compile-source`, reason instructs the agent to read
  the new source, create/update pages under `knowledge/wiki/`, link them from
  `_index.md`, and append a line naming the source folder to `knowledge/wiki/_log.md`.
- `pending_sources`: a source folder is *pending* when its folder name does not appear
  anywhere in `knowledge/wiki/_log.md`. Return sorted relative paths in facts
  (`pending: [...]`), `next_action` `compile-source` if any, else `none`.

### 2. query — deterministic retrieval planner (read-only)

CLI: `mos query QUESTION [path] [--limit N] [--json]` (limit default 5)

Core: `core/query.py` — `query_repo(root: Path, question: str, *, limit: int = 5) -> dict`

Behavior:
- Corpus: `BRAIN.md`, `CONTEXT.md`, all `*.md` under `business/` and `knowledge/wiki/`
  excluding filenames starting with `_`.
- Tokenize question: lowercase alphanumeric terms, length > 2. Score each doc by
  summed term frequency over `filename stem + body` (case-insensitive). Ties broken
  by path for determinism.
- Facts: `question`, `candidates: [{path, score, matched_terms}]` (top N, score > 0),
  `indexes: [knowledge/wiki/_index.md if present]`.
- `ok=true` even with zero hits (finding `no-matches`, severity `warning`).
- `next_action`: id `synthesize-answer`, reason: read the candidate files and answer
  the question with citations to those paths; if candidates are thin, browse
  `knowledge/wiki/_index.md`.

### 3. think — structured thinking handoff (read-only)

CLI: `mos think TOPIC [path] [--json]`

Core: `core/think.py` — `think_repo(root: Path, topic: str) -> dict`

Behavior:
- Gather context paths: always-if-present `BRAIN.md`, `business/strategy/strategy.md`,
  `business/strategy/goals.md`, plus top-5 topic-relevant docs reusing the scoring
  from `core/query.py` (import and reuse; do not duplicate the ranking logic).
- Facts: `topic`, `prompt` — a dict with `objective` (one sentence framing the topic),
  `context_paths`, `steps` (read context → reason through options and tradeoffs →
  make a recommendation → write it to `business/decisions/<YYYY-MM-DD>-<slug>.md`
  with rationale → append to `knowledge/wiki/_log.md`), and `output_contract`
  (decision file must state: decision, why, alternatives rejected, revisit-when).
- `next_action`: id `run-think`, reason: execute the grounded prompt now.
- Requires a valid repo (`.mos/config.yaml` via `find_root`); otherwise `ok=false`,
  finding `not-a-mos-repo`.

### 4. onboard — scaffold + interview handoff (mutating)

CLI: `mos onboard [path] --name NAME [--runtime claude|codex|all] (--plan|--yes) [--json]`

Core: `core/onboard.py` — `onboard_repo(root: Path, name: str, runtime: str, *, apply: bool) -> dict`

Behavior:
- If the repo is not set up, perform the same scaffold as `setup_repo`
  (import and call `core.setup.setup_repo`, or its internals if cleaner) — do not
  reimplement scaffolding.
- Then, if no `.git` directory exists: run `git init` (+ `git add -A` and an initial
  commit `mos: onboard <name>`) via `subprocess`, apply-gated. If `git` is missing,
  finding `git-unavailable` severity `warning`, still `ok=true`.
- Interview handoff: compare each business-template content file against the packaged
  template copy (`template_root()`); files whose content is byte-identical to the
  template are *unfilled*. Facts: `interview: {unfilled: [relpaths], guidance}` where
  guidance tells the agent to interview the user about brand, audience, offer,
  strategy and rewrite each unfilled file with real content.
- `next_action`: `run-interview` when anything is unfilled, else `run-start`.

### 5. update — engine self-update (mutating)

CLI: `mos update (--plan|--yes) [--json]`

Core: `core/update.py` — `update_engine(*, apply: bool) -> dict`

Behavior:
- Detect install mode from `Path(marketing_os.__file__)`:
  (a) *source checkout*: some ancestor contains `pyproject.toml` whose text contains
  `name = "marketing-os"` and a `.git` dir → update = `git -C <root> pull --ff-only`.
  Guards: current branch is `main` (else finding `not-on-main`), `git status
  --porcelain` clean (else `dirty-worktree`); on guard failure `ok=false`, no pull.
  (b) *pipx install*: `"pipx" in str(path).lower()` → update = `pipx upgrade
  marketing-os`.
  (c) otherwise → `ok=true`, no-op, finding `unknown-install` severity `warning`,
  `next_action` `manual-update` (tell the agent/user to upgrade via their installer).
- `--plan`: report detected mode + the exact command that would run, in `changes`.
- `--yes`: run it via subprocess, capture output; `ok` reflects returncode. On change,
  `next_action` `run-doctor`.
- Envelope `repo` = the checkout root (mode a) or `Path.cwd()`.

### 6. statusline — one-line ambient badge (read-only, special output)

CLI: `mos statusline [path] [--json]`

Core: `core/statusline.py` — `statusline_repo(start: Path) -> dict`

Behavior:
- `find_root(start)` (walk-up). Not a mos repo → facts `active=false, line=""`;
  `ok=true`. Always exit 0 (special-cased in `main()`).
- Active: line is plain ASCII: `mos · <business_name> · skills <installed>/<total>`.
  Skill counts via `core.skills.project_manifest` presence / counting skill dirs under
  the project runtime dirs — reuse existing helpers in `core/skills.py`; if counting
  is unreliable, drop the skills segment rather than guessing.
- Human (non-json) output prints the bare line only (no envelope rendering) — handled
  in `cli/main.py` dispatch, not in core.
- No color codes at all in v1 (agents and statusbars both prefer plain).

## CLI wiring (phase 2, single owner of cli/main.py)

- Add the six subparsers exactly as specced; `path` stays a positional `nargs="?"`
  default `"."` for repo-taking commands, payload (`SOURCE`, `QUESTION`, `TOPIC`) is
  the first positional.
- `dispatch()` gains six branches calling the core functions.
- `main()` special-cases: `statusline` non-json prints `result["line"]` and returns 0.
- Update `tests/contracts/test_cli_contract.py` for the new help surface and envelope
  schemas (`mos.ingest.v1`, `mos.query.v1`, `mos.think.v1`, `mos.onboard.v1`,
  `mos.update.v1`, `mos.statusline.v1`).

## File ownership (parallel phase 1 — no overlaps)

- Executor A: `core/query.py`, `core/think.py`, `tests/unit/test_query.py`,
  `tests/unit/test_think.py` (think reuses query's scorer: expose
  `score_corpus(root, terms) -> list[tuple[Path, int, list[str]]]` from
  `core/query.py` and import it in `core/think.py`)
- Executor B: `core/ingest.py`, `core/statusline.py`, `tests/unit/test_ingest.py`,
  `tests/unit/test_statusline.py`
- Executor C: `core/onboard.py`, `core/update.py`, `tests/unit/test_onboard.py`,
  `tests/unit/test_update.py`
- Phase 2 executor: `cli/main.py`, `tests/contracts/test_cli_contract.py`, this file's
  status section, full gate run.

Nobody in phase 1 touches `cli/main.py`, `core/schema.py`, or another executor's
files. `find_root` already exists in `core/schema.py`.

## Status

- [x] Plan written; `find_root` added to `core/schema.py`
- [x] Phase 1: core modules + unit tests (A, B, C) — all landed, targeted tests green.
      Accepted deviations: statusline separator is `·`; skills counted via
      `inspect_runtimes()["claude"]`; update exposes fact `run_command` (not
      `command`, which collides with the envelope key); think non-repo envelope uses
      `next_action=run-setup`; ingest is not repo-gated (flag for review).
- [x] Phase 2: CLI wiring + contract tests + gates — all six commands wired into
      `cli/main.py`, contract tests extended, full gate-suite green.
      Gate results (`.venv/Scripts/python.exe`, repo root):
      `ruff check .` clean; `pytest --cov=marketing_os` 76 passed, total coverage
      87.92% (floor 80); `scripts/check_clean_language.py` passed; `python -m build`
      + `scripts/smoke_wheel.py` passed; `python -m marketing_os --help` lists all
      commands. No Phase-1 module changes were required.
      Phase-2 wiring notes: `ingest --pending` takes an optional `[path]` only — since
      argparse fills the `source` positional first, a lone positional under `--pending`
      is treated as the path (two positionals → ValueError). Ingest's mutation group is
      non-required at the parser level (pending is read-only); a missing `--plan/--yes`
      when ingesting surfaces via `_mutation_mode` as a `command-error` envelope (exit 1),
      whereas `onboard`/`update` keep the required group so argparse rejects with exit 2.
      The engine module is `marketing_os` (console script `mos`), so the help gate runs
      as `python -m marketing_os --help` (there is no importable `mos` module for `-m`).
- [x] Phase 3: read-only review (correctness + agent-contract lenses), fixes applied.

### Phase 3 fixes

Two read-only reviews produced a merged fix list, all applied:

- **ingest path grammar**: destination is now the validator-conformant
  `knowledge/sources/YYYY/MM/YYYY-MM-DD-<slug>/source.md`; `--topic` is metadata only
  (header + envelope fact), no longer a directory segment. `mos validate` now passes after
  an ingest.
- **think decision path**: the grounded prompt targets
  `business/decisions/YYYY/MM/YYYY-MM-DD-<slug>/decision.md` (validator-conformant).
- **ingest repo gate**: `ingest`/`--pending` require a repo (`find_root`); otherwise
  `ok=false`, finding `not-a-mos-repo`, `next_action` `run-setup`.
- **directory ingest**: members are copied under a `files/` subdirectory (relative subpaths
  preserved); the root `source.md` manifest lists `files/<relpath>` entries, so a member
  named `source.md` never clobbers the manifest.
- **pending matching**: source folders are enumerated with a depth-fixed
  `*/*/*/source.md` glob and matched against `_log.md` by whole token (split on whitespace
  and `/`), not substring — superstring folder names no longer collide.
- **atomic ingest writes**: apply-mode writes land in a temp sibling directory and are
  `os.replace`d into place only after all writes succeed; failures roll back with an
  `ingest-failed` finding.
- **subprocess timeouts**: `update` git/pipx runners use 120s (pull/upgrade) and 30s
  (introspection); `onboard`'s git runner uses 60s. Timeouts surface as `update-failed` /
  `git-failed`.
- **strict date**: `--date` must match `^\d{4}-\d{2}-\d{2}$` and parse via
  `date.fromisoformat`; the bad value is reported in the finding message, not the path.
- **statusline**: separator is plain ASCII ` | `; the installed count subtracts mismatched
  (stale) skills as well as missing ones; the `business` fact is `{"name": ...}`.
- **pending schema**: `pending_sources` returns command `ingest-pending`
  (schema `mos.ingest-pending.v1`).
- **update changes**: plan-mode `changes` entries are prefixed `run: <cmd>`; a guard trip
  yields empty `changes`; `run_command` is always populated when a command is known.
- **compile-source next_action**: the reason interpolates the actual source folder path and
  folder name.
- **CLI hygiene**: `--pending` help documents read-only usage; `SOURCE` help notes it needs
  `--plan`/`--yes`; combining `--pending` with `--plan`/`--yes` raises a clear `ValueError`.
- **docs**: the architecture module map lists the six new modules.
