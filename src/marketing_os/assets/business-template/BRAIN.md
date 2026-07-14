# {{BUSINESS_NAME}} Marketing Brain

This file is the canonical operating contract for Claude Code and Codex.

## Grounding order

Before producing work:

1. Read `CONTEXT.md` for the current focus, desired outcome, and constraints.
2. Read only the relevant truth under `business/`.
3. Read relevant synthesized knowledge under `knowledge/wiki/`.
4. Retrieve related prior work only when it materially improves the task.

## Routing

- Business identity, audience, offers, strategy, proof, and operations belong in `business/`.
- Immutable source material belongs in `knowledge/sources/YYYY/MM/YYYY-MM-DD-source/`.
- Reusable synthesized knowledge belongs in `knowledge/wiki/`.
- Organic deliverables belong in `content/YYYY/MM/YYYY-MM-DD-topic/<channel>/`.
- Coordinated or paid work belongs in `campaigns/YYYY/MM/YYYY-MM-DD-campaign/<platform>/`.
- Performance reports belong in `reporting/YYYY/QN/YYYY-MM/`.
- Work with no better destination belongs in `outputs/YYYY/MM/YYYY-MM-DD-slug/`.
- Retired material belongs in `archive/` and must not be used for ordinary grounding.

## Invariants

- `business/` is the sole source of business truth. Never create a parallel identity layer.
- Living business documents keep stable filenames and are edited in place.
- Execution artifacts use dated folders.
- Sources are immutable after capture; wiki pages may be improved.
- Never overwrite an existing business file during setup or repair.
- Never store secrets, credentials, raw customer exports, or runtime-local state in tracked files.

## Approval gates

Ask before publishing, spending, contacting customers, mutating external accounts, deleting
files, or performing any destructive operation.
