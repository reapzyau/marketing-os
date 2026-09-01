# Documentation

marketing-os creates a file-based marketing brain. Three surfaces reach it, all through the
same deterministic `mos` CLI: a terminal, an agent runtime (Claude Code or Codex) running the
bundled skills, and a local browser app started with `mos ui`. These docs explain the why, the
how, and the contracts that keep the sides honest.

Two ideas run through everything here. First, the CLI owns filesystem facts, validation,
and runtime wiring, and calls no model, with one documented exception — `mos assist`, which
may run an agent runtime the operator already installed; the agent owns interviews, judgment,
synthesis, and writing. Second, the brain is plain markdown on disk, so business truth
is versioned, reviewable, and portable across runtimes. Pick a route below, or jump
straight to the document you need.

## Reading routes

- **New here** - start with [philosophy.md](philosophy.md) for the why, then follow
  [setup-guide.md](setup-guide.md) from install to a healthy repository.
- **Operating a brain** - keep [cli-reference.md](cli-reference.md) and
  [business-repo.md](business-repo.md) close; reach for
  [troubleshooting.md](troubleshooting.md) when a command reports a problem. The navigation
  layer that makes retrieval cheap is described in business-repo.md, and the graph layer that
  deliberately stays outside the CLI in [knowledge-graph.md](knowledge-graph.md).
- **Prefer a window to a terminal** - run `mos ui`, then read
  [architecture.md](architecture.md) for what the local app is, what it can run, and what
  guards it.
- **Contracts and internals** - read [architecture.md](architecture.md),
  [json-output-contract.md](json-output-contract.md), and
  [agent-runtime-contract.md](agent-runtime-contract.md) to understand how the CLI and
  agents interoperate; see [../decisions/README.md](../decisions/README.md) for how
  directional choices are recorded.
- **Shipping the engine** - [releasing.md](releasing.md) is the runbook for publishing to
  PyPI: the one-time trusted-publishing setup only the account owner can do, the commands
  that cut a release, and how to prove the published wheel can still scaffold a brain.

## Reference documents

| Document | Summary |
| --- | --- |
| [philosophy.md](philosophy.md) | Why the system is split: the CLI owns facts, the agent owns judgment, grounding beats prompting. |
| [setup-guide.md](setup-guide.md) | First-run walkthrough from a source checkout to a `ready` business brain. |
| [cli-reference.md](cli-reference.md) | The `mos` commands, their flags, plan/apply gating, and repository states. |
| [json-output-contract.md](json-output-contract.md) | The envelope, finding, and next-action shapes every `--json` response follows. |
| [agent-runtime-contract.md](agent-runtime-contract.md) | How packaged skills reach Claude Code and Codex through content-hashed generated copies. |
| [architecture.md](architecture.md) | Engine-repo versus business-repo split, module map, the local app, and generated runtime state. |
| [business-repo.md](business-repo.md) | The generated brain's structure, memory layers, and file lifecycle rules. |
| [knowledge-graph.md](knowledge-graph.md) | Why the navigation layer ships in the CLI and the model-backed graph does not, with the measurements behind that split. |
| [troubleshooting.md](troubleshooting.md) | Per-state remedies keyed to `mos status` and `mos doctor` output. |
| [releasing.md](releasing.md) | How a version tag becomes a PyPI release: the trusted-publishing setup, the tag commands, and the post-publish verification. |
| [../decisions/README.md](../decisions/README.md) | Convention for recording directional and architectural decisions. |

Design plans live in [`plans/`](plans/). They record what a piece of work set out to do at
the time it was written, and are kept as history rather than maintained as contracts, so read
them for intent and the documents above for what is true now.

## Working from source

These docs describe the system as the code implements it. They are not the command surface:
`mos --help` and `mos <command> --help` list every command and flag the installed engine
actually has, and are the live source of truth when exact syntax matters. When a repository's
state matters, `mos status . --json` and `mos doctor . --json` report the deterministic facts.
The docs explain the model behind those outputs.
