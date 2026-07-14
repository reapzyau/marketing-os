# Architecture

The generated repository has five memory layers:

1. `BRAIN.md` defines how every agent operates.
2. `CONTEXT.md` records the current focus and constraints.
3. `business/` is the sole source of business truth.
4. `knowledge/` holds immutable sources and maintainable synthesized pages.
5. `content/`, `campaigns/`, `reporting/`, and `outputs/` hold execution artifacts.

`AGENTS.md` and `CLAUDE.md` are intentionally thin runtime loaders. Both point to
`BRAIN.md`, preventing two instruction systems from drifting apart.

Runtime skill copies are generated from one packaged source, ignored by git, and checked
by content hash. Local runtime state lives below `.mos/local/` and is never committed.
