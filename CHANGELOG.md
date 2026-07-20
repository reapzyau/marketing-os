# Changelog

## [Unreleased]

### Added

- Clean deterministic marketing-os CLI.
- Canonical single-business brain scaffold.
- Shared `mos-setup`, `mos-start`, and `mos-help` skills for Claude Code and Codex.
- Built out the `docs/` set: architecture, business-repo, and troubleshooting references, plus the documentation index and code-derived contract docs.
- `mos migrate` — model-free routing of off-schema files into the canonical structure: `--plan` diagnoses stray top-level entries, and a `mos.migrate-plan.v1` `--plan-file` is applied atomically (no overwrite, no escaping the repo), plus the `mos-migrate` skill that owns the routing judgement.
