# Plan — `mos ui`: the local app for non-technical operators

**Date:** 2026-08-26
**Status:** in-progress
**Bar:** Supabase Studio via `supabase start` (primary), n8n first-run wizard on `:5678`
(onboarding lens), Prisma Studio on `:5555` (CLI-opens-localhost-UI lens). Bar screenshots are
captured to `$BAR/shots/` and every critic compares against those real images, never a description.

## The outcome

A person who has never opened a terminal installs marketing-os, a browser tab opens by itself,
and they end up with a validated brain on disk — in-house or agency — without typing a command.
The same app opens and closes from the terminal for people who do live there.

## Hard constraints

1. **Vanilla only.** HTML, CSS and JavaScript with no framework, no bundler, no build step, no
   Node. Served by the Python standard library from inside the wheel. `dependencies = []` in
   `pyproject.toml` stays empty. If a dependency feels necessary, the design is wrong.
2. **The UI is a client of the CLI, never a second implementation.** Every action builds a real
   `mos` argv and dispatches it through `marketing_os.cli.main` in-process. The UI renders the
   returned envelope and always shows the exact equivalent command line, so the app teaches the
   CLI instead of hiding it.
3. **Localhost only.** Bind `127.0.0.1`. Never `0.0.0.0`.
4. **No shell.** No `subprocess`, no `shell=True`, no string interpolation into a command.
5. **Mutation gating survives.** Commands that write still require `--plan` or `--yes`. The UI
   always previews the plan and requires an explicit confirm before applying.
6. Python 3.10+, `ruff` clean at line-length 100, and the full `pytest` suite green.

## Security (non-negotiable — a localhost server that scaffolds folders is a real surface)

- Bind `127.0.0.1` only.
- Mint a random session token at start (`secrets.token_urlsafe(32)`). Inject it into `index.html`
  at serve time. Every `/api/*` request must present it in an `X-MOS-Token` header; reject
  otherwise with 403. This is what stops any other page in the browser driving the app.
- Reject requests whose `Origin` or `Referer` is present and is not the server's own origin.
- The command allowlist is explicit. An unknown command is a 400, never a passthrough.
- The token is never written to disk in world-readable state; the state file stores pid/port/url
  only.

## Surface

`mos ui [path] [--port N] [--no-open] [--json]` — start, print the URL, open the browser.
`mos ui stop [--json]` — stop a running server via the state file.
`mos ui status [--json]` — report running/not, pid, port, url.

Envelope: `schema: "mos.ui.v1"`, plus `running`, `url`, `port`, `pid`. Same
`ok`/`changes`/`findings`/`next_action` shape as every other command.

State file: `~/.marketing-os/ui.json` — must work before any brain exists, so it cannot live in
a repo. Stale-pid detection: if the recorded pid is dead, treat as not running and clean up.

**First-install auto-open.** `mos install --yes` opens the app when it has not opened before
(marker in `~/.marketing-os/`). `--no-ui` opts out. Opening the browser must never be able to
crash the command: `webbrowser.open`, then WSL fallbacks (`wslview`, `cmd.exe /c start`), then
silently degrade to printing the URL.

## API

- `GET /` → `index.html` with the token injected
- `GET /static/*` → css/js, correct content types, no directory traversal
- `GET /api/state` → cwd, whether it is a brain, and the current `status`/`doctor` envelopes,
  plus `brains`: every brain the operator has (the registry in `~/.marketing-os/brains.json`
  ∪ a one-level scan of the first place), each `{path, name, mode, legacy, attachable, exists,
  last_opened}`. `GET /api/state?path=<abs>` answers the same envelope for another root (an
  absolute path to an existing folder, else 400 `bad-path`); that is how the sidebar switches
  brains in one request. The folder the server was started in is registered on the first
  state request when it is a brain.
- `POST /api/brains` → `{"op": "remember"|"forget", "path"}` → `{brains}`. Same guards as
  `/api/browse`; `remember` also insists the folder exists. The page posts `remember` when a
  brain is opened, switched to, attached or created by the wizard; `forget` drops a listed
  brain whose folder is gone.
- `POST /api/run` → `{"command": "...", "args": {...}}` → `{envelope, command_line}`
- `POST /api/browse` → `{"path"}` → one folder: parent, subfolders, brain if any (the in-page list)
- `POST /api/pick-folder` → `{"start"}` → the operating system's own "choose a folder" window
  (Explorer under Windows and WSL via PowerShell, Finder via `osascript`, zenity/kdialog/Tk on
  Linux), answered as `{path, cancelled, available, error, backend}`. `/api/state` carries
  `picker: true|false` so the page knows whether to ask for it; when it is false, or the window
  fails to open, step 1's "Choose a folder…" falls back to the in-page list from `/api/browse`.

Allowlisted commands: `status`, `validate`, `doctor`, `onboard`, `install`, `skills sync`,
`index build`, `index sync`, `index status`, `related`, `query`, `think`, `ingest`, `migrate`,
`update`, `statusline`, `context show`, `context set`.

`context show` (read-only) and `context set` (mutating, so the Preview/Apply gate applies) are
what let the app ask the brand questions in place and record the answers. Without them the
dashboard can only tell a non-technical operator to open a terminal, which is the moment the
product abandons them.

## Onboarding workflow (the part that is actually being judged)

Five steps, one decision per screen, plain language, no jargon:

1. **Where** — pick or create the folder. Show the resolved absolute path back to them.
2. **Who** — in-house (one brand you own), agency (you serve clients — adds the client registry
   at `business/clients/clients.md`), or client (one brain for one agency client; requires the
   agency name). Explain each in a sentence a non-technical person understands. This choice maps
   to `--mode` and drives which overlay is applied.
3. **Name** — the business name. Show the folder name it will generate.
4. **Preview** — run `--plan`, render every file that will be created as a readable tree, and
   require an explicit confirm. Nothing is written before this click.
5. **Apply and verify** — run `--yes`, then `validate` and `status`, and show what is still
   missing in the operator's own words, with the next action as a button.

## Judging pieces

Each is judged on its own, builder and critic in separate fresh contexts:

1. First launch — from install to a rendered app, measured in clicks and seconds
2. Onboarding flow — can a non-technical person finish it without help
3. Dashboard — does it tell the truth about the brain's state at a glance
4. Command surface — every allowlisted command reachable, with results a human can read
5. Lifecycle — start, stop, status, restart, port in use, second instance
6. Error states — no brain, bad path, failed validate, killed server, stale pid

## Verification (binary, checked on disk — not claimed in prose)

- `uv run pytest -q` green, including new tests for the server, the token gate, the allowlist,
  the state file, stale-pid recovery, and mode-driven scaffolding.
- `uv run ruff check .` clean.
- `mos ui --no-open --json` returns a valid envelope and the port actually listens.
- `mos ui stop --json` stops it and the port is free afterwards.
- Onboarding through the UI creates the in-house tree; the same flow with agency also creates
  `business/clients/clients.md`.
- Playwright screenshots of every screen at 1440x900 and 390x844 exist for the critics.
