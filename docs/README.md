# Documentation

marketing-os creates a file-based marketing brain that Claude Code and Codex operate
through the same deterministic `mos` CLI and the same bundled skills. These docs
explain the why, the how, and the contracts that keep the two sides honest.

Two ideas run through everything here. First, the CLI owns filesystem facts, validation,
and runtime wiring, and never calls a model; the agent owns interviews, judgment,
synthesis, and writing. Second, the brain is plain markdown on disk, so business truth
is versioned, reviewable, and portable across runtimes. Pick a route below, or jump
straight to the document you need.

## Reading routes

- **New here** - start with [philosophy.md](philosophy.md) for the why, then follow
  [setup-guide.md](setup-guide.md) from install to a healthy repository.
- **Operating a brain** - keep [cli-reference.md](cli-reference.md) and
  [business-repo.md](business-repo.md) close; reach for
  [troubleshooting.md](troubleshooting.md) when a command reports a problem.
- **Contracts and internals** - read [architecture.md](architecture.md),
  [json-output-contract.md](json-output-contract.md), and
  [agent-runtime-contract.md](agent-runtime-contract.md) to understand how the CLI and
  agents interoperate; see [../decisions/README.md](../decisions/README.md) for how
  directional choices are recorded.

## All documents

| Document | Summary |
| --- | --- |
| [philosophy.md](philosophy.md) | Why the system is split: the CLI owns facts, the agent owns judgment, grounding beats prompting. |
| [setup-guide.md](setup-guide.md) | First-run walkthrough from `pipx install` to a `ready` business brain. |
| [cli-reference.md](cli-reference.md) | Complete `mos` command surface, flags, plan/apply gating, and repository states. |
| [json-output-contract.md](json-output-contract.md) | The envelope, finding, and next-action shapes every `--json` response follows. |
| [agent-runtime-contract.md](agent-runtime-contract.md) | How packaged skills reach Claude Code and Codex through content-hashed generated copies. |
| [architecture.md](architecture.md) | Engine-repo versus business-repo split, module map, and generated runtime state. |
| [business-repo.md](business-repo.md) | The generated brain's structure, memory layers, and file lifecycle rules. |
| [troubleshooting.md](troubleshooting.md) | Per-state remedies keyed to `mos status` and `mos doctor` output. |
| [../decisions/README.md](../decisions/README.md) | Convention for recording directional and architectural decisions. |

## Working from source

These docs describe the system as the code implements it. When a command's exact syntax
matters, `mos --help` and `mos <command> --help` are the live source of truth; when a
repository's state matters, `mos status . --json` and `mos doctor . --json` report the
deterministic facts. The docs explain the model behind those outputs.
