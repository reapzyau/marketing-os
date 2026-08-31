# Plan: in-house / agency / client mode split

> **Historical plan — not a live instruction.** This records what the mode split set out to
> do at the time it was written. It was written while the scaffold command was still called
> `mos setup` and the scaffold skill was still `mos-setup`; both were later merged into
> `mos onboard` and `mos-onboard`. Every `mos setup` and `mos-setup` below is the name as of
> then. Do not run them — there is no `setup` subcommand and no `mos-setup` skill. The
> function `setup_repo` in `core/setup.py` does still exist and keeps its name.
> For what is true now, read [../cli-reference.md](../cli-reference.md).

Contract for rebuilding the mode system from scratch (never copy from the predecessor
repo — see AGENTS.md). Builds on the conventions in docs/plans/cli-rebuild.md
(envelope, --plan|--yes, agent-first grounded handoffs, stdlib only).

## Operator story

One question at first initialisation decides how the brain is shaped:
- **in-house** — one brand you run yourself. One repo (`{slug}-hq` suggested name).
  Knowledge is global to the brand.
- **agency** — you serve clients. One agency HQ repo (`{slug}-hq`) holding a client
  REGISTRY (pointers, never client work), plus a separate repo per client. Separate
  repos because the repo is the access boundary — git has no per-folder permissions.
- **client** — the brain for one agency client (`{agency-slug}-{slug}` suggested
  name). Knowledge is client-specific; the repo records which agency runs it.

## Config (`.mos/config.yaml`)

- Add `"mode": "in-house" | "agency" | "client"` to the JSON payload.
- Client mode additionally records `"agency": "<agency business name>"`.
- `schema` stays `mos.business-repo.v1`; `schema_version` stays 1 (additive field).
- Read semantics everywhere (helper in core/schema.py, e.g.
  `repo_mode(config) -> tuple[str, list[finding]]`):
  - missing `mode` → implied `"in-house"` + WARNING finding `missing-mode`
    (legacy repo created before modes; suggest adding the field).
  - present but not one of the three → ERROR finding `invalid-mode`, fail closed
    (commands that depend on mode return ok=false; never guess).
- Do NOT add a `clients: []` config list (dead/write-only in the predecessor —
  the markdown registry is the single source of truth). Do NOT add `segment`.

## Template overlay

- `assets/business-template/` stays the shared canonical template for ALL modes.
- New `assets/mode-overlays/agency/business/clients/clients.md` — the registry:
  title `# Client Registry`, a note that this file holds pointers only (client work
  lives in each client's own repo), then the table with exact columns
  `| Client | Repo | Status | Access |` and one seed row
  `| _example-client_ | ` + backtick-quoted path-or-url + ` | active | you |`.
  Documented status values: active / paused / offboarded.
- Scaffold logic: setup applies the shared template, then the overlay tree for the
  chosen mode (only agency has one today). Client mode = shared template only.

## CLI surface changes

### setup (first-step tie-in)
`mos setup [path] --name NAME --mode {in-house,agency,client} [--agency NAME] [--runtime ...] (--plan|--yes) [--json]`
- `--mode` omitted → ok=false, finding `mode-required`, next_action `choose-mode`
  whose reason IS the detection prompt, self-contained for an agent to relay:
  "Ask the user: are you marketing one brand you run in-house, or running an agency
  that serves clients? Choices: in-house (one brand you own), agency (you serve
  clients; creates the agency HQ with a client registry), client (a brain for one
  agency client). Then re-run setup with --mode <choice> (client mode: add
  --agency <agency name>)."
- `--agency` required when mode=client (else finding `agency-required`, same
  choose-mode-style guidance); forbidden (warning `agency-ignored`) otherwise.
- Config written with mode (+agency for client). Agency mode also scaffolds the
  overlay. Envelope facts gain `mode` and `suggested_repo_name`
  ({slug}-hq for in-house/agency, {agency-slug}-{slug} for client — slugify both).

### onboard
Same new flags as setup (`--mode`, `--agency`) plus `--hq PATH` (client mode only):
- Delegates scaffolding to setup_repo as today (pass mode through).
- client + `--hq`: append `| <name> | ` + backtick-quoted repo path + ` | active |
  you |` to `<hq>/business/clients/clients.md`, inserted directly after the
  `_example-client_` row if present else appended to the table. Apply-gated.
  Missing registry file → WARNING `no-client-registry` ("is this an agency HQ?"),
  non-fatal. HQ path that is not a mos repo → same warning path.
- `--hq` with a non-client mode → warning `hq-ignored`.
- Interview handoff unchanged; facts gain `mode` + `suggested_repo_name`.

### validate (mode-aware structure)
- agency: `business/clients/clients.md` REQUIRED (error `missing-client-registry`).
- in-house/client: `business/clients/` present → WARNING `unexpected-clients-folder`
  (mode says this repo should not hold a registry).
- invalid-mode config → error (fail closed); missing mode → warning missing-mode.

### status / doctor / statusline
- status + doctor: include `mode` in facts; render it in the human output line.
- statusline: line becomes `mos | <name> | <mode> | skills n/m` (omit mode segment
  for legacy repos with missing mode). facts gain `mode`.

## Skill update

`assets/skills/mos-setup/SKILL.md`: the flow now LEADS with the mode question
(same wording as choose-mode), passes `--mode`/`--agency` to setup, and for agency
mode explains the registry + that each client gets its own repo via
`mos onboard --mode client --agency <name> --hq <agency-hq-path>`. Update the skills
manifest if it carries content hashes (inspect core/skills.py + manifest.json and
regenerate however the build expects). The other skills only need edits if they
contradict modes.

## Deliberate cuts from the predecessor (record, do not build)

- `segment` config field; `clients: []` config list (dead there).
- `product/`, `team/` folders and `--no-campaigns`/`--no-team` toggles.
- `--github`/`gh repo create` integration and `--org` (defer to a later unit).
- Interactive terminal prompts — replaced by the choose-mode envelope handoff.
- Forced repo-directory naming — advisory `suggested_repo_name` fact instead.

## Acceptance criteria

1. `mos setup . --name X --yes` (no mode) → ok=false with the self-contained
   choose-mode next_action; nothing written.
2. `mos setup . --name X --mode agency --yes` → scaffold includes
   business/clients/clients.md; validate → ok=true.
3. `mos setup . --name X --mode in-house --yes` → no clients folder; validate ok.
4. client without --agency → agency-required; with it → config carries agency,
   suggested_repo_name = {agency-slug}-{slug}.
5. onboard client + --hq pointing at an agency repo → registry row appended after
   the example row (verify content); --plan appends nothing.
6. Legacy repo (config without mode): validate/status/statusline still ok with the
   missing-mode warning; statusline omits the mode segment.
7. Invalid mode in config: validate ok=false invalid-mode.
8. Full gates green: ruff, pytest (coverage ≥80), clean-language,
   python -m build + smoke_wheel.py.

## Status

- [x] Implementation
- [x] Review (correctness + agent-contract) and fixes

### Shipped

All 8 acceptance criteria implemented and verified; full gate suite green
(`ruff` clean, `pytest --cov` 113 passed at 88% ≥ 80 floor, clean-language passed,
`python -m build` + `smoke_wheel.py` passed with the overlay proven in the wheel). E2E
walkthrough (a–f) confirmed in a temp dir.

- `mode` read semantics live in `repo_mode()` (`core/schema.py`); `config_text` gained
  keyword `mode`/`agency` args, keys stay sorted. Legacy `config_text(name)` still omits
  `mode` so pre-mode fixtures/repos read as in-house.
- Agency overlay at `assets/mode-overlays/agency/business/clients/clients.md`; setup applies
  the shared template then the mode overlay (create-only, listed in `--plan`).
- `setup_repo`/`onboard_repo` gained keyword-only `mode`/`agency` (+ `hq` on onboard). Mode
  is required — omitting it returns the verbatim `choose-mode` handoff and writes nothing.
- Envelope facts gained `mode` + `suggested_repo_name` (setup, onboard); status/doctor add
  `mode`; statusline adds a `mode` segment only when `mode` is present (legacy repos omit it),
  plus a `mode` fact. Human output renders a `Mode:` line when present.
- Registry append is apply-gated, inserts after the `_example-client_` row (else appends to
  the table tail), warns `no-client-registry` for a non-HQ path and `client-already-registered`
  on a duplicate name (skipping the write), and `hq-ignored` for non-client modes.

Deviations from the plan:

- The `mode-required` finding carries a short message; the verbatim detection prompt lives in
  the `choose-mode` `next_action.reason` (the plan says the reason IS the prompt), exposed as
  the module constant `CHOOSE_MODE_REASON`.
- The golden-tree contract test now scaffolds with `mode="in-house"` (no overlay), keeping the
  golden fixture the shared-template baseline; a separate test covers the agency overlay.
- The wheel smoke now scaffolds an agency repo (was mode-less) so it exercises and proves the
  overlay end to end, and asserts the overlay path is present in the wheel archive.
- No `pyproject` packaging change was needed: the existing `assets/**/*` package-data glob
  already carries `mode-overlays/` into the wheel (verified in the archive).

### Review fixes (post-review)

Two read-only reviews merged into one approved fix list; all applied.

- **A (docs):** README, setup-guide, cli-reference, and json-output-contract now lead with
  the required `--mode` (+`--agency` for client). cli-reference gained a full `mos onboard`
  section (mode/agency/hq, relative-path registry write-back, dup/malformed warnings,
  suggested_repo_name) and dropped the mode-less examples; json-output-contract documents the
  `mode`/`suggested_repo_name` facts and shows the `choose-mode`/`mode-required` refusal envelope.
- **B (validation.py):** a legacy repo (missing mode) that already carries
  `business/clients/clients.md` now warns `set-mode-agency` instead of the wrong
  `unexpected-clients-folder`; explicit in-house/client modes keep the original warning.
- **C (onboard.py):** registry rows record a relative posix path from the HQ root
  (absolute-posix fallback across Windows drives via `ValueError`); CRLF files keep CRLF
  byte-for-byte (`newline=""` read/write); duplicate detection casefolds names; a table-less
  registry warns `registry-malformed` and skips the write.
- **D (statusline.py):** mode resolved via `repo_mode`; the segment renders only for an
  explicit valid mode. Legacy/missing → fact `null`, omitted; invalid → verbatim string kept
  in facts but omitted from the line.
- **E (tests):** added coverage for B, C1–C4, D, plus the empty-slug `suggested_repo_name`
  fallback and the API-level `invalid-mode` setup branch.

Gates re-run green: `ruff` clean, `pytest --cov` 121 passed at 88% (≥80 floor), clean-language
passed, `python -m build` + `smoke_wheel.py` passed. E2E confirmed: agency setup → client
onboard --hq writes `| Widgets Inc | ` + backtick `../acme-widgets` + ` | active | you |`;
a mode-stripped agency repo validates `ok=true` with `set-mode-agency` (no
`unexpected-clients-folder`).
