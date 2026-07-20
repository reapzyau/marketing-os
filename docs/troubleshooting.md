# Troubleshooting

Start with deterministic facts:

```bash
mos status . --json
mos doctor . --json
```

`mos status` reports a `repo_state` and a `next_action`; work through the state you are in.

## By repo state

### absent

`config` could not be read, so the folder is not a marketing-os business repository. This is
also what you see outside a repository or when `.mos/config.yaml` is missing or unparseable.
Run the onboard skill (or `mos onboard`) to scaffold a new brain, or move into the correct
folder. `mos status` walks up from the given path to find `.mos/config.yaml`, so run it from
inside the repository.

### invalid

Structure has one or more error-severity findings and must be repaired before business work.
Read the findings and fix each path (see common findings below), then re-run `mos validate`.
Setup and repair never overwrite an existing business file, so it is safe to re-run them to
recreate anything genuinely missing.

### needs-runtime-sync

Structure is sound but the Claude Code and Codex skill copies are missing or out of date.
Preview and apply a sync:

```bash
mos skills sync . --runtime all --plan --json
mos skills sync . --runtime all --yes --json
```

### needs-context

The repository is wired but the required context is incomplete. `mos status` lists the
missing fields under `context.missing` and points `next_action` at the first one. The
required fields are brand, voice, audience, and offer; a field counts as complete once its
file carries real content (roughly thirty characters once headings, comments, and `TODO:`
lines are ignored). Fill in the named file, then re-run `mos status`.

### ready

Structure, runtime wiring, and context all pass. Follow `CONTEXT.md` to continue the current
priority.

## Skills sync scenarios

- **Missing** — a runtime skill has never been generated. It appears under a runtime's
  `missing` list; a plan shows a `create` action. Apply with `--yes`.
- **Stale** — a generated copy no longer matches the packaged source hash. It appears under
  `mismatched`; the plan shows a `replace` action, valid only when the previous install was
  recorded in the manifest.
- **Unrecognized** — a skill directory the tooling did not generate. Sync never overwrites
  it; the plan returns a `skill-conflict` finding instead. Review the directory, then remove
  or relocate it yourself and run the sync again.

## Common validation findings

- `missing-or-invalid-config` — `.mos/config.yaml` is absent or does not parse as JSON.
  Re-run onboard to rewrite the marker.
- `unsupported-schema` — the config's `schema` or `schema_version` does not match the
  packaged schema. Confirm you are on a compatible marketing-os version.
- `missing-directory` / `missing-file` — a required path from `schema.json` is absent. Re-run
  onboard to recreate scaffolded files without touching existing ones.
- `unknown-top-level` — a warning, not an error: a top-level path sits outside the canonical
  architecture. Move the work under an allowed tree (`business/`, `knowledge/`, `content/`,
  `campaigns/`, `reporting/`, `outputs/`, or `archive/`) or remove it.
- `invalid-year` / `invalid-month` / `invalid-dated-artifact` — a folder under an execution
  tree breaks the `YYYY/MM/YYYY-MM-DD-slug` grammar. Rename it to match.
- `invalid-quarter` / `invalid-report-month` — a folder under `reporting/` breaks the
  `YYYY/QN/YYYY-MM` grammar. Rename it to match.

Only error-severity findings block a repository; warnings are reported but leave `ok` true.
