# Business-Repo Architecture

`mos setup` creates one canonical marketing brain:

```text
my-business/
|-- BRAIN.md
|-- CONTEXT.md
|-- AGENTS.md
|-- CLAUDE.md
|-- README.md
|-- .mos/
|   |-- config.yaml
|   `-- local/                         generated and ignored
|-- .claude/skills/                    generated and ignored
|-- .agents/skills/                    generated and ignored
|-- business/
|   |-- brand/{brand.md,voice.md,assets/}
|   |-- audience/primary.md
|   |-- offers/<offer-slug>/offer.md
|   |-- strategy/{strategy.md,goals.md,roadmap.md}
|   |-- proof/testimonials.md
|   |-- operations/
|   `-- decisions/YYYY/MM/YYYY-MM-DD-slug/decision.md
|-- knowledge/
|   |-- sources/YYYY/MM/YYYY-MM-DD-source/
|   `-- wiki/{_index.md,_log.md}
|-- content/YYYY/MM/YYYY-MM-DD-topic/<channel>/
|-- campaigns/YYYY/MM/YYYY-MM-DD-campaign/<platform>/
|-- reporting/YYYY/QN/YYYY-MM/
|-- outputs/YYYY/MM/YYYY-MM-DD-slug/
`-- archive/
```

## Memory layers

- `BRAIN.md` is the shared operating contract.
- `CONTEXT.md` records the current focus and constraints.
- `business/` is the sole source of business truth.
- `knowledge/` contains immutable sources and maintainable synthesized knowledge.
- Execution work goes to the matching dated content, campaign, report, or output folder.
- `archive/` is excluded from ordinary grounding.

## File lifecycle

Living business files retain stable paths and are edited in place. Execution artifacts use
dated folders. Setup and repair create missing generated files but never replace an existing
business file.
