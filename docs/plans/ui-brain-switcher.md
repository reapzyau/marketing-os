# Plan: brain switcher + left sidebar navigation

Status: queued 2026-08-28. Owner: one executor (app.js / index.html / styles.css / server.py additive / tests).

## Objective

The local app knows every brain the operator has, lists them in a left-hand sidebar, and lets them switch between brains with one click. Navigation (Dashboard, Commands) moves from the top bar into the same left panel.

## Decisions already made

- **Registry, not scanning.** A brain becomes "known" when it is created by the wizard, opened via "Open this brain", attached via `mos attach`, or is the folder the server was started on. Known brains persist in `~/.marketing-os/brains.json` (`{"schema": "mos.brains.v1", "brains": [{"path", "name", "mode", "last_opened"}]}`), written atomically (see `core/atomic.py`). The default place (`places[0]`) is also scanned once at boot so brains sitting on the Desktop appear without having been opened. Nothing sweeps the home folder.
- **Missing folders** stay listed but greyed with a text tag "not found" and a "Forget" action; they are never auto-deleted from the registry.
- **Switching** = set the active brain; the dashboard, Commands default path, and every allowlisted command target that brain. The choice persists (existing `remember()` localStorage plus `last_opened` server-side).
- **Layout**: left sidebar, fixed width ~260px on ≥ 900px viewports. Sections top to bottom: app mark; **Brains** (list, active highlighted with a text marker not colour alone, "+ Set up another brain" → wizard, "Attach a folder…" → runs `mos attach <picked folder> --plan` via `/api/run` and shows the plan before `--yes`); **Navigation** (Dashboard, Commands) as a `tablist`; footer with Refresh. Under 900px the sidebar becomes a top drawer opened by a "Menu" button (`aria-expanded`), so the 390px requirement still holds. Keyboard operable end to end; focus lands in the drawer when opened and returns to the button when closed.
- The top bar shrinks to the mobile menu button + current brain name only.

## Server (additive only)

- `ui/registry.py`: `load()`, `remember(path, name, mode)`, `forget(path)`, `known_brains(places)` (registry ∪ one-level scan of `places[0]`, deduped by path, each entry re-described with `places.describe_folder`-style brain summary so name/mode/legacy/attachable are current; `exists: bool`).
- `/api/state` gains `"brains": known_brains(...)`. Active brain resolution: `/api/state?path=<abs>` (GET, token-guarded) returns the same envelope for that root (status/doctor run against it, `is_brain`, `business_name`, `mode`). Keep the no-arg form identical.
- `/api/brains` POST `{op: "remember"|"forget", path}` with the same guards as `/api/browse`.
- Hook `remember` into the wizard create path (after a successful onboard) and `openBrain`.

## Client

- `App.brains`, `renderSidebar()`, `switchBrain(path)` (loads `/api/state?path=`, updates `App.path/App.state/App.status/App.doctor`, `remember()`, re-renders dashboard, announces "Now showing <name>" in the existing live region), `forgetBrain(path)`.
- `openBrain(path)` becomes `switchBrain(path)` + registry remember.
- Nav tabs keep their `role="tablist"` semantics; move the markup, not the behaviour.

## Tests

- `tests/unit/test_ui_registry.py`: remember/forget/dedupe/missing-folder/atomic write/malformed file recovers to empty.
- `tests/unit/test_ui.py`: `/api/state?path=` for a second tmp brain; `/api/brains` ops + token; state carries `brains`.
- Harness (`tests/support/ui_harness.cjs`): sidebar lists two brains, switching updates the heading and dashboard root, missing brain shows "not found" and Forget; drawer toggles at narrow width (set `window.innerWidth` in the stub if supported, else assert the button/aria wiring).
- Static contract: sidebar has a `nav` landmark, tablist still present, no paths in visible copy, contrast pairs for the new active-state styles pass the existing audit.

## Acceptance

- `.venv/bin/pytest -q` green; `.venv/bin/ruff check src tests` clean; `node --check app.js`.
- Live: restart `mos ui`, `GET /api/state` has `brains` with Flowstate and the-vibe-marketing-lab; `GET /api/state?path=/mnt/c/Users/richa/Desktop/flowstate-hq` returns `business_name == "Flowstate"`.
- CHANGELOG [Unreleased]; `docs/plans/ui-app.md` API list updated.
- Not committed.
