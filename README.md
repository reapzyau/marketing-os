# marketing-os

marketing-os creates a file-based marketing brain that Claude Code and Codex can use
through the same deterministic CLI and the same bundled skills.

## Install

```bash
pipx install marketing-os
mos install --runtime all --plan
mos install --runtime all --yes
```

Then open the destination folder in your agent:

- Claude Code: `/mos-setup`
- Codex: `$mos-setup`

Both commands load the same packaged workflow. `mos install` wires the bundled
skills globally into your home directory and records the install in
`~/.marketing-os/runtime-manifest.json`. See [the documentation index](docs/README.md) to
get oriented, or [the business-repo architecture](docs/business-repo.md) for the exact
generated structure and routing rules.

## CLI

```bash
mos setup ./my-business --name "My Business" --mode in-house --runtime all --plan --json
mos setup ./my-business --name "My Business" --mode in-house --runtime all --yes --json
mos status ./my-business --json
mos validate ./my-business --json
mos doctor ./my-business --json
mos skills sync ./my-business --runtime all --plan --json
```

`--mode` is required and picks how the brain is shaped: `in-house` (one brand you
run yourself), `agency` (you serve clients; adds a client registry), or `client`
(a brain for one agency client — pass `--agency "<agency name>"` too). Omitting
`--mode` writes nothing and returns a `choose-mode` handoff.

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
