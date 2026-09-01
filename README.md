# marketing-os

marketing-os creates a file-based marketing brain that Claude Code and Codex can use
through the same deterministic CLI and the same bundled skills. The CLI owns filesystem
facts, validation, and runtime wiring. Agents own interviews, judgment, synthesis, and
writing.

## Install

marketing-os has never been published. There is no release on PyPI and no version tag in
this repository, so `pipx install marketing-os` has nothing to resolve and fails. A source
checkout is the install:

```bash
git clone https://github.com/reapzyau/marketing-os
cd marketing-os
python -m pip install -e .
mos install --runtime all --plan
mos install --runtime all --yes
```

That route stays supported after the first release, so nothing above is throwaway.

Once a release lands, `pipx install marketing-os` becomes the one-line front door and
nothing else in this section changes. Getting there takes one push of a `v0.2.0` tag plus a
one-time trusted-publishing setup on PyPI that only the account owner can do; both are
written down in [docs/releasing.md](docs/releasing.md). Ask PyPI whether it has happened
rather than trusting this file to have been updated:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://pypi.org/pypi/marketing-os/json
```

`404` is still unpublished, and the checkout above is the only way in. `200` means the
release landed and `pipx install marketing-os` works.

`mos install` copies the bundled skills into `~/.claude/skills` and `~/.agents/skills`
and records what it wrote in `~/.marketing-os/runtime-manifest.json`. It wires your home
directory and nothing else — no brain exists yet. On macOS and Linux the first successful
`--yes` install also opens the local app in a browser; on Windows, which has no `os.fork`,
it records the marker and leaves the app to `mos ui`. Either way the `ui-opened` marker in
`~/.marketing-os` is written before the attempt, so the open is tried once and never
retried, and `--no-ui` skips it.

`mos --version` prints `mos 0.2.0`. That is the version in `pyproject.toml`; until a tag is
pushed it is not a released one, and a tag that disagrees with it fails the release build
rather than publishing the wrong number. The local app and the merge of `setup` into
`mos onboard` are listed under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md).

## Create a brain

```bash
mos onboard ./my-business --name "My Business" --mode in-house --runtime all --plan --json
mos onboard ./my-business --name "My Business" --mode in-house --runtime all --yes --json
```

The same job has two other doors. In your agent, `/mos-onboard` (Claude Code) or
`$mos-onboard` (Codex) runs the interview and calls this command for you. In a browser,
`mos ui` walks you through the five-step wizard.

`--mode` decides how the brain is shaped, and `mos onboard` writes nothing without it:
omit it and you get a `choose-mode` handoff instead of a repository. `in-house` is one
brand you run yourself; `agency` creates an agency HQ with a client registry; `client` is
a brain for a single agency client, so pass `--agency "<agency name>"` as well, plus
`--hq <path>` to append a row to that agency's registry. `onboard` and `attach` are the
only commands that take `--mode`.

What you get is a git repository holding `business/`, `knowledge/`, `content/`,
`campaigns/`, `reporting/`, `outputs/`, and `archive/`, a `BRAIN.md` that tells both
runtimes how to ground their work, and the nine skills copied into the repository's own
`.claude/skills` and `.agents/skills`. From there:

```bash
mos status ./my-business --json
mos validate ./my-business --json
mos doctor ./my-business --json
mos skills sync ./my-business --runtime all --plan --json
mos update --plan
```

That is a taster, not the surface: `mos --help` lists every command and each one has its
own `--help`. Anything that writes to the brain takes `--plan` to preview and requires
`--yes` to apply. Machine-local state is the exception — `mos index build` writes a
catalogue under `.mos/local/`, and `mos ui` writes its pid file and log under
`~/.marketing-os` (the running app adds a brain registry there itself), neither gated,
neither touching a business file.

## The local app

```bash
mos ui                  # open the current folder
mos ui ./my-business    # open a specific brain
mos ui status           # whether it is running, with pid, port, and URL
mos ui stop             # stop it
```

`mos ui` starts a small server and opens a browser tab. It binds `127.0.0.1` only — the
address is a module constant, so there is no host flag and no LAN mode — and takes the
first free port from 4321 to 4370 unless you name one with `--port`. `--no-open` starts
the server without opening a browser. Where `os.fork` exists the server detaches and
gives the terminal back; where it does not, it runs in the foreground and says so in the
envelope rather than pretending otherwise.

Four things live in it:

- a five-step onboarding wizard — folder, who it's for, name, preview, create — whose
  preview step runs the real `mos onboard --plan` and shows you that plan before anything
  is written;
- a brain switcher listing every brain you have, from a registry at
  `~/.marketing-os/brains.json` plus a one-level scan of your desktop, with rows tagged
  "not found", "not a brain", or "needs attach" instead of quietly disappearing;
- a dashboard: mode, a health verdict, the required and optional context checklist,
  runtime wiring, and findings, all read from a real `mos status` and `mos doctor` run;
- a commands tab with a generated form for every allowlisted command, a "Read only" or
  "Writes files" pill, and the exact `mos …` line it ran.

Two decisions are worth stating. It ships zero dependencies — the standard library's
`http.server`, one vanilla JavaScript file, no framework, no bundler, no CDN, no web
fonts — so it travels inside the wheel and cannot rot on its own schedule. And it is a
client of the CLI, never a second implementation: every action builds a real argv and
goes through the same parser and handlers your terminal runs, then shows you the command
line, so the app teaches the CLI instead of hiding it.

## Bundled skills

`mos install` copies these nine into `~/.claude/skills` and `~/.agents/skills`;
`mos onboard` and `mos skills sync` put the same copies inside a brain.

| Skill | Claude Code | Codex | What it does |
| --- | --- | --- | --- |
| mos-onboard | `/mos-onboard` | `$mos-onboard` | Create a new brain or complete an existing one: scaffold, git, the context interview, and client registration for agencies. |
| mos-migrate | `/mos-migrate` | `$mos-migrate` | Move a messy folder into the canonical structure. The skill produces the routing plan; `mos migrate` applies it. |
| mos-start | `/mos-start` | `$mos-start` | Start or resume work from deterministic repository facts and recommend one useful next action. |
| mos-status | `/mos-status` | `$mos-status` | Brief you on what is healthy, what context is missing, and the single next action. |
| mos-think | `/mos-think` | `$mos-think` | Research a marketing question from repository truth, decide with you, and codify the decision as durable memory. |
| mos-bet | `/mos-bet` | `$mos-bet` | Open, update, close, list, or narrate a falsifiable business bet stored as a dated decision artifact. |
| mos-end | `/mos-end` | `$mos-end` | Close a session by recording the current focus, logging what changed, and proposing a safe commit. |
| mos-help | `/mos-help` | `$mos-help` | Explain setup, architecture, routing, status, validation, and Claude Code or Codex wiring. |
| mos-update | `/mos-update` | `$mos-update` | Update the engine, then refresh the bundled skills and verify runtime wiring. |

`assets/skills/manifest.json` is the registry that decides what gets installed. The
installer reads that file rather than listing the directory, so a skill folder missing
from it is never copied and never counted. What ships in the wheel is a separate
question, settled by a package-data glob over the whole `assets/` tree.

## Documentation

[The documentation index](docs/README.md) is the way in: [philosophy.md](docs/philosophy.md)
for why the split exists, [setup-guide.md](docs/setup-guide.md) for the first run,
[cli-reference.md](docs/cli-reference.md) for the commands, and
[business-repo.md](docs/business-repo.md) for the generated structure and routing rules.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest --cov=marketing_os --cov-report=term-missing
python scripts/check_clean_language.py
python -m build
python scripts/smoke_wheel.py
```

CI runs exactly those, on Linux, macOS, and Windows across Python 3.10 and 3.13. Run
`pytest` under coverage as shown: `fail_under = 80` in `pyproject.toml` is only enforced
when `--cov` is passed, so a bare `pytest` cannot fail the way CI does. The wheel smoke
reads the wheel `python -m build` just produced, so the build step is not optional
either, and the clean-language gate is a gate. Skipping any of them locally only moves
the failure to the push.

Pushing a `v*` tag runs the same gates again and then publishes to PyPI —
[docs/releasing.md](docs/releasing.md) covers the setup that has to happen first.
