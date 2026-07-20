# Agent Runtime Contract

`mos` ships a set of bundled skills — listed in the packaged `manifest.json` — and
delivers them to two agent runtimes: Claude Code and Codex. This document
describes how one packaged source reaches each runtime, how staleness is detected,
and the rules that keep synchronization safe.

## Single source

The only authored copy of every skill lives at
`src/marketing_os/assets/skills/`. Its `manifest.json` lists the bundled skills:

```json
{ "schema": "mos.skills.v1", "skills": ["mos-onboard", "mos-start", "..."] }
```

The manifest is the authoritative list of bundled skills; the sync machinery
(`bundled_skills()` in `core/skills.py`) reads it directly, so the set can grow
without changing this contract.

Everything under a runtime skill directory is a **generated copy**. Generated
copies are ignored by git and must never be tracked; the clean-language gate fails
the build if any appear under `.claude/skills/` or `.agents/skills/`.

## Runtime directories

Each runtime discovers skills in its own directory:

| Runtime | Skill directory |
|---------|-----------------|
| Claude Code | `.claude/skills` |
| Codex | `.agents/skills` |

`--runtime all` (the default) targets both; `--runtime claude` or
`--runtime codex` targets one. These paths are relative to the sync target: the
project root for `mos skills sync`, and the home directory for `mos install`.

## Content-hash staleness

Staleness is decided by content, not timestamps. `tree_hash` computes a single
SHA-256 over a directory: it walks every file in sorted order, and for each mixes
in the file's repository-relative POSIX path and its bytes. Files under any
`__pycache__` segment are skipped. A path that is not a directory hashes to the
empty string, which marks it missing.

For each skill and runtime, sync compares three hashes:

- `expected` — the hash of the packaged source.
- `current` — the hash of the installed copy (empty if absent).
- `previous` — the hash recorded in the runtime manifest.

The comparison yields one action per skill:

- `current == expected` — already current; nothing to do.
- destination absent — **create**.
- destination present and `current == previous` (a recognized, unmodified
  generated copy) — **replace**.
- destination present but unrecognized (`current` matches neither `expected` nor
  the recorded `previous`) — a `skill-conflict` finding; no action.

## Never overwrite unrecognized directories

The conflict rule is the core safety guarantee: sync only replaces a directory it
previously wrote and can still recognize by its recorded hash. Any directory it
does not recognize is left untouched and surfaced as a `skill-conflict` finding.
Resolve it by hand — remove or relocate the conflicting directory after reviewing
it — then run sync again. Applying a plan that contains findings writes nothing.

## Manifest tracking

Applied copies are recorded in a runtime manifest so later runs can tell a
recognized copy from a foreign one. Two manifests exist, chosen by command:

| Scope | Command | Manifest path |
|-------|---------|---------------|
| Global | `mos install` | `~/.marketing-os/runtime-manifest.json` |
| Project | `mos skills sync` | `.mos/local/runtime-manifest.json` |

Both use the `mos.runtime-manifest.v1` schema and store, per runtime and skill, the
hash that was written. `mos onboard` performs a project sync as part of scaffolding,
so a freshly created brain is already wired.

## Plan and apply

Synchronization follows the same plan/apply gate as every mutating command:

```bash
mos skills sync . --runtime all --plan   # preview create/replace actions
mos skills sync . --runtime all --yes    # apply the reviewed plan
```

`--plan` reports the actions without writing. `--yes` applies them: a `replace`
removes the existing directory and copies the source in its place, then records
the new hash in the manifest. See [cli-reference.md](cli-reference.md) for the full
command surface.

## Readiness in status and doctor

`mos status` and `mos doctor` inspect both runtime directories and report, per
runtime, whether it is `ready` along with any `missing` or `mismatched` skills. A
repository whose structure is sound but whose runtime copies are missing or stale
resolves to the `needs-runtime-sync` state; `mos doctor` is `ok` only when both
runtimes are ready.

## Invoking a skill

Once installed, each runtime invokes a skill with its own prefix:

- Claude Code: `/mos-onboard`
- Codex: `$mos-onboard`

The skill body is identical across runtimes — only the invocation syntax differs.
The same pattern applies to `mos-start` and `mos-help`.
