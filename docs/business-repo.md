# Business-Repo Architecture

`mos onboard` creates one canonical marketing brain:

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

The required directories, required files, allowed top-level paths, and grounding
exclusions above are enforced from `src/marketing_os/assets/schema.json`; `mos validate`
reports any deviation.

## Memory layers

- `BRAIN.md` is the shared operating contract.
- `CONTEXT.md` records the current focus and constraints.
- `business/` is the sole source of business truth.
- `knowledge/` contains immutable sources and maintainable synthesized knowledge.
- Execution work goes to the matching dated content, campaign, report, or output folder.
- `archive/` is excluded from ordinary grounding.

## business/operations/

`business/operations/` is a living reference for how the marketing function runs day to
day: standard operating procedures, channel checklists, publishing and approval workflows,
posting cadences, and the inventory of tools and accounts the business depends on. It ships
as a bare directory with no required files, so add plain-language pages as the practices
become real. These are living files on stable paths, edited in place rather than dated;
keep credentials and secrets out and record only the process itself.

## business/decisions/

`business/decisions/` is the per-event record of marketing decisions: each entry captures
what was decided, the reasoning, the alternatives considered, and the expected outcome, so
later work can trace why the current strategy exists. Unlike `operations/`, this tree is
dated. Each decision lives at `business/decisions/YYYY/MM/YYYY-MM-DD-slug/decision.md`, and
`mos validate` checks the folder names against the dated grammar below. Keep this business
record distinct from the engine repository's own `docs/` and `decisions/`, which document
the tooling rather than a business.

## .mos/config.yaml

Setup writes the repository marker to `.mos/config.yaml`. Despite the `.yaml` extension the
file currently holds JSON, and the tooling reads it back with a JSON parser
(`json.loads` in `read_config`); YAML is a superset of JSON, so a strict JSON document
still parses. `mos onboard` emits sorted keys, for example an agency HQ:

```json
{
  "business_name": "My Business",
  "mode": "agency",
  "schema": "mos.business-repo.v1",
  "schema_version": 1
}
```

Client repos additionally carry an `agency` key. Repos created before modes existed omit
`mode` entirely and read as in-house (see Modes below).

`mos status`, `mos validate`, and `mos doctor` locate the repository root by walking up
until they find `.mos/config.yaml`, then confirm `schema` and `schema_version` match the
packaged schema. A missing, unparseable, or schema-mismatched file makes the repository
read as absent or invalid.

## Modes

`mos onboard --mode` records how the brain is shaped in an additive `mode` field (the schema
version stays 1):

- **in-house** — one brand you run yourself; knowledge is global to the brand.
- **agency** — you serve clients. The agency HQ repo carries a client registry at
  `business/clients/clients.md` (pointers only, never client work), scaffolded from the
  agency mode overlay. Each client gets its own repo via
  `mos onboard --mode client --agency "<name>" --hq "<agency-hq-path>"`, which appends a row
  to that registry. Separate repos because the repo is the access boundary.
- **client** — the brain for one agency client; the config also records `agency`.

Read semantics are centralized in `repo_mode()` (`core/schema.py`): a missing `mode` is
treated as in-house with a `missing-mode` warning (legacy repos), while an unrecognized
value raises `invalid-mode` and fails closed. `mos validate` requires the registry in agency
mode (`missing-client-registry`) and warns if in-house/client repos hold a `business/clients/`
folder (`unexpected-clients-folder`). `mos onboard` without `--mode` returns a
self-contained `choose-mode` handoff instead of guessing.

## Dated-folder grammar

Execution trees use dated folders so artifacts sort chronologically and validate
deterministically. `mos validate` enforces the exact names:

- Execution dirs (`content/`, `campaigns/`, `outputs/`, `business/decisions/`, and
  `knowledge/sources/`) nest as `YYYY/MM/YYYY-MM-DD-slug/`. The year is four digits, the
  month is `01`-`12`, and the leaf is a full ISO date followed by a lowercase
  hyphenated slug (`a-z`, `0-9`, and single hyphens between segments), for example
  `content/2026/07/2026-07-18-launch-recap/`.
- Reporting uses `reporting/YYYY/QN/YYYY-MM/` instead: a four-digit year, a quarter
  `Q1`-`Q4`, then a `YYYY-MM` month, for example `reporting/2026/Q3/2026-07/`.

A `.gitkeep` file is ignored by the checker, so empty scaffolded trees pass. Any folder
that breaks the grammar surfaces as an `invalid-year`, `invalid-month`,
`invalid-dated-artifact`, `invalid-quarter`, or `invalid-report-month` finding.

## File lifecycle

Living business files retain stable paths and are edited in place. Execution artifacts use
dated folders. Setup and repair create missing generated files but never replace an existing
business file.
