# Review fixes before PR (2026-08-28)

Merged findings from the security and correctness reviewers. One executor applies all of them. Do not commit.

## Must fix

1. **Windows-style path relocates the brain into the cwd (HIGH).** `app.js` `normPath` turns `C:\Users\richa\Desktop` into `C:/Users/richa/Desktop`; `cli/main.py:_path()` resolves it relative to cwd; `onboard --plan` then reports `ok` for `<repo>/C:/Users/richa/Desktop/foo`. Fix in three places: (a) `ui/commands.py` `_positional` (or the POST dispatcher) refuses a `path` that is not absolute after `expanduser` — envelope error `bad-path`; (b) under WSL, a value matching `^[A-Za-z]:[\\/]` is converted with `wslpath -u` before dispatch (server side, reuse `places.py` WSL detection; failure → `bad-path`); (c) `probePath` in `app.js` shows "That is not a full path" for non-absolute text instead of probing. Tests: unit for (a)/(b), harness for (c).
2. **`/api/state?path=` skips the never-descend guard.** `server.py:_state_root` must apply `places._is_forbidden(resolved)` like `/api/browse`, and only expand a bare `~`/`~/…` (never `~otheruser`). Test both.
3. **WSL Desktop fallback picks the alphabetically-first Windows profile.** `places._wsl_desktop_from_profiles`: prefer the profile whose name casefold-matches `$USER`/`os.getlogin()`; when several profiles exist and none match, return `None` (home fallback) rather than guessing. Test: two profiles, match wins; two profiles, no match → None; one profile → that one.
4. **Registry entry that is no longer a brain renders as healthy.** `registry.py` `_describe` adds `is_brain: summary is not None`; `renderSidebar` treats `!is_brain && !attachable` like `missing` (grey, "not a brain" tag, Forget). Harness scenario.
5. **`switchBrain` commits `App.path`/`remember()` before the server answers.** Move both below the `!data` / schema check; on 400 show the existing toast and refresh the sidebar so the row flips to "not found". Fix the harness inconsistency: `stateFor` and the `status` stub must agree for non-fixture paths so the `!is_brain` and 400 branches are exercised — add a scenario for each.
6. **`attachFolder` re-entrancy.** Share `pickFolder`'s `picking` flag; when the picker returns `error` with `available: true` (dialog already open), say "A folder window is already open." and do nothing else — never fall through to the fallback browser.
7. **`mos attach --yes` second run can overwrite `.mos/config.yaml` with no backup.** When `existing != text and backup.exists()`, write a numbered backup (`config.legacy.1.yaml`, …) before overwriting. Test.

## Should fix (small)

8. Drop the dead `existing_brains` key from `/api/state` (nothing in app.js reads it) and its pinning test, so state requests do one Desktop scan, not two. Keep `known_brains`.
9. Picker timeout: return `cancelled: True` with the reason in `error`, and shorten `DEFAULT_TIMEOUT` to 120 s. Update tests.
10. `attach.py`: include `create <dir>/.gitkeep` in the plan's `changes` for every `mkdir`, so plan and apply match; add a `legacy-agency-missing` warning finding when `mode == "client"` and no agency is known.
11. `server.py`: hold `server.lock` only for mutating commands (`--yes`) — `status`/`doctor`/`validate`/`--plan` run unlocked. Keep a test that two concurrent read-only requests do not serialise (or at least that a read does not need the lock).

## Acceptance

- `.venv/bin/pytest -q` green; `.venv/bin/ruff check src tests scripts` clean; `node --check app.js`.
- Probe: `onboard --plan -- C:/Users/richa/Desktop/foo` via `/api/run` → `bad-path` or the wslpath-converted absolute path, never a cwd-relative repo.
- `GET /api/state?path=/proc` → 400.
- Restart `mos ui` at the end so the live server carries the fixes.
- CHANGELOG [Unreleased]: one "Fixed" bullet per user-visible item (1, 4, 5, 7).
