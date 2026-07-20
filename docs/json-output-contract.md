# JSON Output Contract

Every `mos` command returns the same envelope. Pass `--json` to any command to get
it verbatim, printed with `indent=2` and `sort_keys=True`. The envelope is
constructed in `src/marketing_os/core/results.py` and its shape is pinned by the
contract tests in `tests/contracts/`. Human output is a rendering of this
structure and carries no information the envelope lacks.

## Envelope

Every envelope carries these seven keys:

| Field | Type | Meaning |
|-------|------|---------|
| `schema` | string | `mos.<command>.v1` — the contract identity and version. |
| `command` | string | The command that produced the result. |
| `ok` | boolean | Whether the command succeeded. Drives the process exit code. |
| `repo` | string | The absolute, resolved repository path. |
| `changes` | array of string | Human-readable descriptions of planned or applied changes. Empty for read-only commands. |
| `findings` | array of finding | Problems detected (see below). Empty when nothing is wrong. |
| `next_action` | object | The single recommended next step (see below). |

The contract tests assert that these keys are always present:

```python
REQUIRED_KEYS = {"schema", "command", "ok", "repo", "changes", "findings", "next_action"}
```

Beyond the required seven, each command adds its own factual keys (for example
`repo_state`, `context`, `runtimes`, and `installed_skills` on `status`; `checks`
on `doctor`; `summary` on `validate`; `applied`, `planned`, and `runtime` on the
mutating commands). `onboard` adds two mode facts on success:

- `mode` — the chosen repository mode (`in-house`, `agency`, or `client`). It also
  appears on `status`, `doctor`, and `statusline`, where it is `null` for a legacy
  repo whose config predates modes.
- `suggested_repo_name` — the advisory folder name: `{slug}-hq` for in-house/agency,
  `{agency-slug}-{slug}` for client.

Consumers should read known keys and ignore the rest.

## `schema`

The `schema` value is `mos.<command>.v1`, where `<command>` is the command name.
Observed values include `mos.setup.v1`, `mos.status.v1`, `mos.validate.v1`,
`mos.doctor.v1`, `mos.install.v1`, and `mos.skills-sync.v1`. The `v1` suffix is the
stability promise: the seven required keys and their meanings will not change
within `v1`. New optional facts may be added; existing ones will not be removed or
repurposed under the same version.

## Finding

Each entry in `findings` describes one problem:

| Field | Type | Meaning |
|-------|------|---------|
| `code` | string | A stable machine identifier (e.g. `missing-directory`, `skill-conflict`, `not-marketing-os`). |
| `severity` | string | `error` (default) or `warning`. |
| `message` | string | A human-readable explanation. |
| `path` | string | The offending path, or `""` when not path-specific. |

`ok` and the exit code are governed by `error` findings only. A result can carry
`warning` findings (for example, `unknown-top-level`) and still be `ok`.

## Next action

`next_action` names exactly one recommended step:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | A stable action identifier (e.g. `run-setup`, `sync-skills`, `apply-skill-sync`). |
| `reason` | string | A short, human-readable justification. |

When nothing is required, it defaults to
`{"id": "none", "reason": "No further action is required."}`.

## Example

A planned `mos onboard . --name "Acme Co" --mode in-house` on a fresh path:

```json
{
  "schema": "mos.onboard.v1",
  "command": "onboard",
  "ok": true,
  "repo": "/home/user/acme",
  "changes": [
    "create BRAIN.md",
    "create .mos/config.yaml",
    "create .claude/skills/mos-onboard"
  ],
  "findings": [],
  "next_action": {
    "id": "apply-onboard",
    "reason": "Apply the reviewed onboard plan."
  },
  "applied": false,
  "planned": true,
  "mode": "in-house",
  "suggested_repo_name": "acme-co-hq"
}
```

## The `choose-mode` refusal

`--mode` is required. Running `mos onboard` without it is a documented contract
case: the command writes nothing, returns `ok: false` with a `mode-required`
finding, and points at the `choose-mode` next action whose `reason` is the
self-contained question to relay to the user.

```json
{
  "schema": "mos.onboard.v1",
  "command": "onboard",
  "ok": false,
  "repo": "/home/user/acme",
  "changes": [],
  "findings": [
    {
      "code": "mode-required",
      "severity": "error",
      "message": "Onboard requires --mode; choose in-house, agency, or client.",
      "path": ""
    }
  ],
  "next_action": {
    "id": "choose-mode",
    "reason": "Ask the user: are you marketing one brand you run in-house, or running an agency that serves clients? Choices: in-house (one brand you own), agency (you serve clients; creates the agency HQ with a client registry), client (a brain for one agency client). Then re-run onboard with --mode <choice> (client mode: add --agency <agency name>)."
  },
  "applied": false,
  "planned": false
}
```

A failing command returns the same envelope with `ok: false` and a populated
`findings` array — never a stack trace. Uncaught `OSError` and `ValueError` are
caught and reported as a single `command-error` finding.

## Stability expectations

- The seven required keys are guaranteed for every command, in every state.
- `ok` is authoritative: exit code is `0` when `ok` is true, `1` otherwise.
- `schema` identifies the contract version; treat unknown extra keys as additive.
- Finding `code` and next-action `id` values are stable identifiers meant for
  branching in downstream automation; parse them, not the human `message`/`reason`.
