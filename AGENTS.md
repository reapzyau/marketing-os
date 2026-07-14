# Agent Contract

This is the marketing-os engine repository, not a business repository.

- Keep the CLI deterministic and model-free.
- Treat `src/marketing_os/assets/skills/` as the only skill source.
- Never add tracked runtime copies under `.claude/skills/` or `.agents/skills/`.
- Do not copy files from predecessor implementations; implement from this repository's contracts.
- Run `ruff check .`, `pytest`, the clean-language gate, and a wheel smoke before handoff.
- Keep credentials, customer data, provider exports, and machine-local state out of git.
