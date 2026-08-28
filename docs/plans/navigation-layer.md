# Plan — Port TVML's Navigation Layer into marketing-os

**Status:** implemented in 0.2.0 (2026-08-20). Kept as the design record and the rationale
behind the split; see `CHANGELOG.md` for what actually shipped and
`docs/knowledge-graph.md` for why the graph layer stayed out.
**Date:** 2026-08-19
**Source:** `the-vibe-marketing-lab@72f0f42` "feat(graph): navigation layer + connected knowledge graph"

---

## 1. What TVML actually did, and what it moved

TVML is a 1,177-document markdown corpus. Before the change an agent working in it had
`Grep`, `Glob` and `Read` and no map — so every question started with speculative reads.

Measured before / after:

| metric | before | after |
|---|---|---|
| graph nodes / edges | 1,342 / 1,303 | 3,573 / 6,192 |
| average degree | 1.94 | 3.47 |
| edges crossing a top-level folder | 19% | 31% |
| orphan nodes | 14% | 9% |
| **docs with an outgoing link** | **2%** | **64%** |

The root cause finding is the important one, because it decides what we port: a full deep
re-extract found 2.5× more entities and moved connectivity by **zero**. Extraction can only
record a relationship a document *states*. 27 of 1,177 docs carried a wikilink; 1% carried a
connective frontmatter key. The fix was never a better model — it was making the corpus
declare its own structure.

Two 2026 papers drove the design and are worth keeping in the doc:

- **Corpus2Skill (arXiv 2604.14572)** — "Don't Retrieve, Navigate." Compile a corpus into a tree
  of small navigation files; the hierarchy, not an embedding index, is the interface. On WixQA
  (6,221 docs) it beat dense retrieval on Token F1 0.460 vs 0.363 and RAPTOR's 0.389, with better
  context recall (0.652 vs 0.616). Navigation files stay under 2 KB; a typical answer takes 2–3
  navigation turns.
- **"Is Grep All You Need?" (arXiv 2605.15184)** — with a decent harness, filesystem navigation
  plus grep closes most of the gap to embedding retrieval. Structure, meaningful names and index
  files matter more than better embeddings.

That is exactly the harness `mos` gives an agent. The papers say: give it a map.

### The five mechanisms TVML shipped

1. **A frontmatter contract** (`GRAPH_CONTRACT.md`) — five base keys plus at least one
   *connective* key. Enforced by a sensor, not by prose.
2. **A three-level `_index.md` hierarchy** — 159 generated files. Root names the folders;
   each hub is a routing table with distinctive terms per group; each group lists its docs with
   one-line descriptions. Size-bounded: a folder ≤40 docs lists inline, above that it explodes
   into child indexes. Root index is 1.4 KB. The naive flat `business/_index.md` came out at
   **59 KB** — ~15k tokens to read and nothing actionable.
3. **`## Related` blocks** on 636 docs — TF-IDF over title + description, weighted **1.4×
   toward cross-folder targets**, with a score floor so a weak match emits nothing rather than
   noise. Never links into archived / superseded / raw material.
4. **Community hub notes** — 106 notes projecting graphify's semantic clusters into the vault,
   linking docs that belong together by extracted content where no author linked them.
5. **Sensors** — `graph-lint.py` (contract compliance, `--strict`, `--orphans`) and
   `rdg_index.py lint` (docs with zero outgoing links, exit 1).

---

## 2. Where marketing-os-next stands today

| capability | TVML | marketing-os-next |
|---|---|---|
| frontmatter contract | 5 keys + connective key, linted | **none** — template docs carry zero frontmatter |
| navigation hierarchy | 159 generated `_index.md`, 3 levels | `knowledge/wiki/_index.md` is a hand-maintained stub ("Add links to synthesized knowledge pages here.") |
| cross-doc links | `## Related` on 636 docs, TF-IDF + cross-folder bias | none |
| retrieval | catalog + hierarchy navigation | `mos query` — raw term-frequency over `BRAIN.md`, `CONTEXT.md`, `business/**`, `knowledge/wiki/**` |
| sensors | `graph-lint.py`, `index lint` | `mos validate` checks structure and dated-folder grammar only |
| graph | graphify + Gemini, communities | none |

`mos query` (`core/query.py`) is the honest gap. It tokenises, counts term frequency across
filename stem plus full body, sorts, returns the top 5 paths. Three problems:

- **It reads every body on every query.** Cost grows linearly with the corpus, in-process.
- **It never sees `knowledge/sources/`, `content/`, `campaigns/`, `outputs/` or `reporting/`.**
  A question about last quarter's launch recap cannot be answered.
- **It has no notion of description or type**, so a 4,000-word doc that says a term twice
  outranks a doc whose one-line description *is* that term.

The scale difference is also real and must shape the design: TVML has 1,177 docs; a freshly
scaffolded brain has 15 files. A generated hierarchy over 15 files is pure overhead.

---

## 3. What ports, what does not

`AGENTS.md` in this repo is explicit: **"Keep the CLI deterministic and model-free."** That
line decides the split cleanly, and it costs us almost nothing.

**Ports (deterministic, no model):**
- the frontmatter contract
- catalogue build
- the `_index.md` hierarchy generator
- TF-IDF `## Related` backfill
- the lint sensors
- a catalogue-backed rewrite of `mos query`

**Does not port into the CLI:**
- graphify itself (LLM extraction via Gemini / claude-cli)
- community detection and community hub notes
- the ext4-mirror WSL workaround, the `--token-budget 8000` chunk fix, wikilink-edge injection

Those five mechanisms delivered the graph metrics, but mechanisms 1–3 and 5 are what took
**docs with an outgoing link from 2% to 64%** — the number an agent actually feels. The graph
layer is a nice-to-have that costs API keys, a WSL workaround and ~10 minutes a rebuild.

Recommendation: ship 1, 2, 3, 5 in core. Leave the graph as a documented optional add-on
(`docs/knowledge-graph.md`) that a user wires up themselves, not something `mos install` touches.

---

## 4. Proposed implementation, in five phases

### Phase 1 — The contract (highest leverage, smallest diff)

The TVML lesson stated plainly in `GRAPH_CONTRACT.md`: *"Skills that write files into this repo
must emit the frontmatter block themselves. Fixing the skill template is worth more than fixing
a hundred files by hand."* TVML had to backfill 636 docs. A `mos` brain starts at 15 files —
we can make every doc born compliant and never run a backfill at all.

**New file:** `src/marketing_os/assets/business-template/CONTRACT.md`

```yaml
---
title: Human-readable name
type: business | knowledge | content | campaign | report | output | reference
description: One sentence. Highest-leverage field — every index and every Related block is built from it.
date: YYYY-MM-DD
status: draft | active | archived | superseded
---
```

Plus at least one connective key:

- `sources:` — what this was built from. Backward edge. **Mandatory for anything under
  `outputs/`, `content/`, `campaigns/`, `reporting/`.** TVML's rule, worth keeping verbatim:
  *an output with no `sources` is not finished.*
- `related:` — lateral wikilinks, cross-folder preferred.
- `produced_by:` — the skill that generated it. Turns every skill into a hub node: "show me
  everything mos-think has produced" becomes one grep.

The `type` vocabulary maps 1:1 onto this repo's existing top-level folders, so it stays
mechanically checkable against `schema.json`.

**Edits:**
- every `.md` in `assets/business-template/` gains a compliant frontmatter block
- `BRAIN.md` gains a **Frontmatter contract** section between *Routing* and *Invariants*
- all nine `assets/skills/*/SKILL.md` gain a line: files you write carry the contract block
- `assets/schema.json` gains a `frontmatter_contract` object (required keys, connective keys,
  `type` vocabulary, folders where `sources` is mandatory) — one contract, machine-readable,
  same place as the rest of the schema

**Test impact:** `tests/fixtures/golden-tree.txt` gains `CONTRACT.md`; `schema.json`
`required_files` gains `CONTRACT.md`; `tests/contracts/test_assets_contract.py` gains a case
asserting every template `.md` parses a valid contract block.

### Phase 2 — Catalogue and the `_index.md` hierarchy

**New:** `src/marketing_os/core/catalog.py` and `src/marketing_os/core/index.py`

Port from `rdg_index.py` (595 lines; ~40% is TVML-specific and drops out):

- `parse_frontmatter`, `first_sentence`, `docs_iter`, `cmd_build` → `catalog.py`, writing
  `.mos/local/catalog.json` (already gitignored — machine-local state stays out of git, per
  `AGENTS.md`)
- `discover_hubs`, `sync_folder_index`, `sync_root_index`, `_group_terms`, `_doc_lines`,
  `_write_generated` → `index.py`

Constants to keep as-is; they are tuned and TVML paid for the tuning:
- `INLINE_MAX = 40` — the explode threshold
- `GROUP_TERMS = 6` — distinctive terms per group row
- `HUB_MIN_DOCS = 2` — below this a folder gets no index

Adaptation for scale: **below ~25 docs total, generate only the root `_index.md`.** A hierarchy
over an empty brain is noise. The generator already no-ops per-folder via `HUB_MIN_DOCS`; the
global floor is the one new rule.

Keep TVML's "do not hand-edit" marker and its skip-if-replaced-by-hand behaviour
(`_write_generated`). That is what stops the generator fighting the operator.

**New CLI surface**, following this repo's existing plan/apply and JSON-envelope contract:

```bash
mos index build   ./brain --json          # catalogue every doc
mos index sync    ./brain --plan --json   # regenerate the hierarchy (plan)
mos index sync    ./brain --yes  --json   # apply
mos index status  ./brain --json          # coverage
```

Note `knowledge/wiki/_index.md` is currently a hand-written required file. Under this plan it
becomes generated. Either drop it from `required_files` or seed it with the generated marker —
**recommend seeding**, so `mos validate` on a fresh brain stays green before the first sync.

### Phase 3 — `## Related` backfill

**New:** `src/marketing_os/core/related.py` — port `terms_of`, `build_tfidf`, `related_for`,
`unlinked`, `cmd_related` from `rdg_index.py:314-407`.

The algorithm, unchanged: TF-IDF over `title + description` only (not body — that is what keeps
it fast and what stops long docs dominating), top-12 terms per doc, score
`Σ idf(t) · min(count, 3)` over shared terms, **× 1.4 when the target is in a different
top-level folder**, cut at `RELATED_MIN_SCORE = 6.0`, take top 4.

Exclusions port directly onto this repo's schema: never link into `archive/` (already
`excluded_from_grounding`), `knowledge/sources/` (immutable raw), or any `_archive/`,
`_superseded/` path. Never add a block to `_index.md`, `_log.md`, `README.md`, `BRAIN.md`,
`CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRACT.md`.

```bash
mos related ./brain --plan --json
mos related ./brain --yes --json
```

**Known gotcha, already paid for once:** TVML's `related --apply` normalised CRLF → LF across
every file it touched, producing a phantom whole-file diff on the Windows drive. Fixed upstream
in `rdg-skills@274d878`. Port the fix, not the bug: read and write with `newline=""` so line
endings survive, and ship a `.gitattributes` in the business template (TVML added one in the
same commit).

### Phase 4 — Sensors

**New:** `src/marketing_os/core/graphlint.py`, wired into the existing `mos validate` rather
than a separate command — this repo already has one place for structural truth.

Three checks, as findings in the existing envelope:

| finding | meaning |
|---|---|
| `missing-frontmatter` | doc has no contract block |
| `missing-connective-key` | no `sources` / `related` / `produced_by` |
| `output-without-sources` | file under `outputs/`, `content/`, `campaigns/`, `reporting/` with no `sources:` — *"an output with no sources is not finished"* |
| `unlinked-doc` | no outgoing wikilinks and no `## Related` block |
| `invalid-type` | `type` outside the schema vocabulary |

Severity: warnings by default, so an early-stage brain is never blocked. `--strict` promotes
them to errors for CI. This matches how `missing-mode` already behaves in `repo_mode()`.

### Phase 5 — Rewire `mos query`

Replace the body-scan in `core/query.py` with catalogue-backed retrieval, and return a
navigation path rather than a flat file list:

1. Score against `title + description + type + tags` from the catalogue (fast, no body reads).
2. Fall back to a body scan only when the catalogue produces nothing above the floor.
3. Widen the corpus beyond `business/` and `knowledge/wiki/` to every non-archived doc.
4. Return **`route`** — the `_index.md` chain the agent should walk — alongside `candidates`.
   That is the Corpus2Skill move: give the model the branch, not just the leaf.
5. Keep the envelope shape and `next_action` contract exactly as-is.

Also worth adding, cheaply: `mos query --grep "<literal>"` for exact-string lookups (URLs,
names, error text). Half of pm-brain's real searches are literal, and TF-IDF is the wrong tool
for those.

---

## 5. Sequencing, effort, and risk

| phase | effort | risk | blocks |
|---|---|---|---|
| 1 — contract | ~2 h | low | everything |
| 2 — catalogue + hierarchy | ~4 h | medium — golden-tree churn | 3, 5 |
| 3 — Related | ~2 h | medium — CRLF, write safety | — |
| 4 — sensors | ~1.5 h | low | — |
| 5 — query rewrite | ~2.5 h | low | 2 |

About a day and a half end to end, assuming `ruff` and `pytest` stay green throughout.

**Do Phase 1 alone first and ship it.** It is the highest-leverage, lowest-risk piece, and it is
the one that stops the problem from ever accumulating. Phases 2–5 only earn their keep once a
brain has real volume; the contract has to be there from the first document or you are back to
backfilling 636 files.

### Risks worth naming

1. **Golden-tree brittleness.** `tests/fixtures/golden-tree.txt` is an exact-match fixture.
   Every template file added in Phase 1 and every generated index in Phase 2 churns it. Generated
   indexes must be excluded from the golden tree, or the fixture becomes unmaintainable — a
   freshly scaffolded brain should contain no generated indexes at all.
2. **Generated-vs-authored collision.** `knowledge/wiki/_index.md` is currently authored and
   required. Decide this explicitly in Phase 2 (recommendation: seed it generated).
3. **`## Related` on living business files.** TVML gates on `RELATED_MIN_WORDS = 120`. Template
   stubs like `business/audience/primary.md` are shorter than that and should never receive a
   block until the operator has actually filled them in. Keep the word floor.
4. **Small-corpus noise.** TF-IDF over 15 docs produces near-random links. The `RELATED_MIN_SCORE`
   floor handles it mathematically, but verify empirically on the golden brain before shipping —
   the honest expected result at that size is *no blocks written*, and that is correct behaviour.
5. **Scope creep into the graph.** graphify wants an API key, a WSL ext4 mirror, and ~10 minutes
   a rebuild. It stays out of the CLI. If it ships at all, it ships as documentation.

---

## 6. How we verify it worked

TVML's numbers are the model — measure, do not assert. On a seeded test brain of ~120 docs:

- **docs with an outgoing link** — target >60%, the number that moved most in TVML
- **`mos query` candidate precision** — hand-score 20 questions before and after Phase 5
- **root `_index.md` size** — must stay under 2 KB (Corpus2Skill's navigation-file bound)
- **no folder index over ~8 KB** — otherwise the explode threshold is mis-tuned
- **`mos validate --strict`** — clean on the golden brain
- **`ruff check .`, `pytest`, clean-language gate, wheel smoke** — all green, per `AGENTS.md`

---

## 7. Open questions for Richard

1. **Ship the graph layer at all?** Recommendation: no, not in the CLI. Document it as an
   optional add-on. It is the expensive 20% that bought the smallest share of the win.
2. **`mos index sync` on a hook, or manual?** TVML runs it from `pm-end` / a post-commit hook.
   The cheap equivalent here is a step in `mos-end`'s SKILL.md — no hook installation, no
   machine-local state. Recommendation: `mos-end`.
3. **Retrofit the existing `marketing-os` repo?** This plan targets the template. The current
   `marketing-os` brain would need the same backfill TVML ran. Worth doing, separate job.
