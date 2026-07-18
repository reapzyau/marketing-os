# Decisions

This folder records directional and architectural decisions as they are made. It starts
empty by design and grows one file at a time.

## When to write one

Write a decision record when a choice sets direction and would otherwise be hard to
reconstruct later: a change to the CLI contract, the repository schema, the runtime wiring
model, or any tradeoff a future contributor would question. Skip it for routine fixes and
mechanical edits.

## File naming

Name each record `YYYY-MM-DD-slug.md`, using the decision date and a short lowercase
hyphenated slug, for example `2026-07-18-model-free-cli.md`. One decision per file.

## What goes in a record

Keep records short. Cover three things:

- **Context** - the situation and constraints that forced a choice.
- **Decision** - what was chosen, stated plainly.
- **Consequences** - what this enables, what it costs, and what it rules out.

## Decisions versus docs

Decisions are per-event narratives: they capture a moment and the reasoning behind it, and
they are not rewritten as the system evolves. The [docs/](../docs/README.md) folder holds
durable reference that is kept current. When a decision changes how the system works, update
the relevant doc and leave the decision record as the historical account of why.
