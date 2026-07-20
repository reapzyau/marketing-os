# Changelog

## [Unreleased]

### Changed

- Merged the former `setup` subcommand into `mos onboard`. Onboard is now the single command to create or complete a brain (new or existing) — scaffold, git, the context interview (now including strategy), and agency client registration. The `setup` subcommand and its bundled skill are retired; use `mos onboard` and `/mos-onboard` going forward.

### Added

- Clean deterministic marketing-os CLI.
- Canonical single-business brain scaffold.
- Shared `mos-onboard`, `mos-start`, and `mos-help` skills for Claude Code and Codex.
- Built out the `docs/` set: architecture, business-repo, and troubleshooting references, plus the documentation index and code-derived contract docs.
- `mos migrate` — model-free routing of off-schema files into the canonical structure: `--plan` diagnoses stray top-level entries, and a `mos.migrate-plan.v1` `--plan-file` is applied atomically (no overwrite, no escaping the repo), plus the `mos-migrate` skill that owns the routing judgement.
