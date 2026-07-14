# marketing-os

marketing-os creates a file-based marketing brain that Claude Code and Codex can use
through the same deterministic CLI and the same three starter skills.

## Install

```bash
pipx install marketing-os
mos install --runtime all --plan
mos install --runtime all --yes
```

Then open the destination folder in your agent:

- Claude Code: `/mos-setup`
- Codex: `$mos-setup`

Both commands load the same packaged workflow. See [the business-repo architecture](docs/business-repo.md)
for the exact generated structure and routing rules.

## CLI

```bash
mos setup ./my-business --name "My Business" --runtime all --plan --json
mos setup ./my-business --name "My Business" --runtime all --yes --json
mos status ./my-business --json
mos validate ./my-business --json
mos doctor ./my-business --json
mos skills sync ./my-business --runtime all --plan --json
```

Mutation commands always support a read-only plan and require `--yes` to apply it.
The CLI owns filesystem facts, validation, and runtime wiring. Agents own interviews,
judgment, synthesis, and writing.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
```
